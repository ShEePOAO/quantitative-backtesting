from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.indicators import ema
from core.metrics import TRADE_COLUMNS, compute_metrics

HEDGE_TRADE_COLUMNS = ["方向", "用途"] + TRADE_COLUMNS

STATE_FLAT = 0
STATE_LONG = 1
STATE_SHORT = -1
STATE_LOCKED = 2

STATE_LABELS = {STATE_FLAT: "空倉", STATE_LONG: "多單", STATE_SHORT: "空單", STATE_LOCKED: "鎖倉中"}

DEFAULT_HEDGE_PARAMS = {
    "trend_type": "ema",
    "fast": 20,
    "slow": 60,
    "breakout_n": 20,
    "tp_pct": 0.05,
    "add_step_pct": 0.0,
    "add_max": 0,
    "hedge_pct": 0.01,
    "hedge_ratio": 1.0,
    "grid_step_pct": 0.01,
    "grid_tp_pct": 0.008,
    "grid_max": 5,
    "unlock_mode": "net",
    "unlock_target": 0.0,
    "unlock_retrace_pct": 0.02,
    "unlock_action": "close_all",
}

DEFAULT_HEDGE_SETTINGS = {
    "initial_capital": 10000.0,
    "order_notional_pct": 1.0,
    "leverage": 10.0,
    "maintenance_rate": 0.005,
    "funding_apr": 0.10,
    "fee_rate": 0.0005,
    "slippage": 0.0005,
}

PARAM_KEYS = [
    "tp_pct", "add_step_pct", "add_max", "hedge_pct", "hedge_ratio",
    "grid_step_pct", "grid_tp_pct", "grid_max",
    "unlock_mode", "unlock_target", "unlock_retrace_pct", "unlock_action",
]


@dataclass
class HedgeResult:
    equity: pd.Series
    stop_equity: pd.Series
    trades: pd.DataFrame
    metrics: dict
    stop_metrics: dict
    stats: dict
    states: pd.Series
    net_exposure: pd.Series
    gross_exposure: pd.Series


def trend_signal(df, params):
    close = df["close"].astype(float)
    sig = pd.Series(0, index=df.index, dtype=int)
    if params.get("trend_type", "ema") == "breakout":
        n = int(params["breakout_n"])
        hi = df["high"].astype(float).rolling(n).max().shift(1)
        lo = df["low"].astype(float).rolling(n).min().shift(1)
        sig[close > hi] = 1
        sig[close < lo] = -1
        return sig
    fast = ema(close, int(params["fast"]))
    slow = ema(close, int(params["slow"]))
    sig[fast > slow] = 1
    sig[fast < slow] = -1
    sig[fast.isna() | slow.isna()] = 0
    return sig


def _unrealized(leg, price):
    if leg["side"] == 1:
        return leg["qty"] * (price - leg["entry"])
    return leg["qty"] * (leg["entry"] - price)


def _wavg_entry(legs):
    num = sum(x["qty"] * x["entry"] for x in legs)
    den = sum(x["qty"] for x in legs)
    return num / den if den else 0.0


def _simulate(df, trend, cfg, lock_mode):
    n = len(df)
    open_ = df["open"].astype(float).values
    high = df["high"].astype(float).values
    low = df["low"].astype(float).values
    close = df["close"].astype(float).values
    tr = trend.values

    fee_rate = cfg["fee_rate"]
    slip = cfg["slippage"]
    order_notional = cfg["order_notional"]
    tp_pct = cfg["tp_pct"]
    add_step = cfg["add_step_pct"]
    add_max = int(cfg["add_max"])
    hedge_pct = cfg["hedge_pct"]
    hedge_ratio = cfg["hedge_ratio"]
    grid_step = cfg["grid_step_pct"]
    grid_tp = cfg["grid_tp_pct"]
    grid_max = int(cfg["grid_max"])
    unlock_mode = cfg["unlock_mode"]
    unlock_target = cfg["unlock_target"]
    unlock_retrace = cfg["unlock_retrace_pct"]
    unlock_action = cfg["unlock_action"]
    leverage = cfg["leverage"]
    maintenance = cfg["maintenance_rate"]
    maint_ratio = max(maintenance, 1.0 / leverage) if leverage > 0 else maintenance
    fund_per_bar = cfg["funding_apr"] / cfg["periods_per_year"]

    cash = cfg["initial_capital"]
    legs = []
    cycle = None
    trades = []
    states = np.zeros(n, dtype=int)
    net_exp = np.zeros(n)
    gross_exp = np.zeros(n)
    equity_vals = np.zeros(n)

    stat = {
        "fees_paid": 0.0,
        "funding_cost": 0.0,
        "add_opens": 0,
        "hedge_events": 0,
        "grid_opens": 0,
        "grid_closes": 0,
        "unlock_events": 0,
        "keep_events": 0,
        "liquidations": 0,
        "margin_skips": 0,
        "max_gross": 0.0,
        "max_legs": 0,
        "max_margin_ratio": 0.0,
        "liquidated": False,
    }

    def equity_at(price):
        return cash + sum(_unrealized(x, price) for x in legs)

    def entry_fill(side, price):
        return price * (1 + slip) if side == 1 else price * (1 - slip)

    def exit_fill(side, price):
        return price * (1 - slip) if side == 1 else price * (1 + slip)

    def open_leg(side, price, purpose, time, notional=None, qty=None):
        nonlocal cash
        fill = entry_fill(side, price)
        if qty is None:
            qty = (order_notional if notional is None else notional) / fill
        gross_now = sum(abs(x["qty"]) * price for x in legs)
        eq = equity_at(price)
        if gross_now + qty * fill > eq * leverage:
            stat["margin_skips"] += 1
            return None
        efee = qty * fill * fee_rate
        cash -= efee
        stat["fees_paid"] += efee
        leg = {"side": side, "qty": qty, "entry": fill, "purpose": purpose, "entry_time": time, "entry_fee": efee}
        legs.append(leg)
        return leg

    def close_leg(leg, price, time, reason):
        nonlocal cash
        fill = exit_fill(leg["side"], price)
        gross_pnl = _unrealized(leg, fill)
        xfee = leg["qty"] * fill * fee_rate
        cash += gross_pnl - xfee
        stat["fees_paid"] += xfee
        pnl_net = gross_pnl - leg["entry_fee"] - xfee
        cost = leg["qty"] * leg["entry"]
        trades.append(
            {
                "方向": "多" if leg["side"] == 1 else "空",
                "用途": leg["purpose"],
                "進場時間": leg["entry_time"],
                "進場價": leg["entry"],
                "出場時間": time,
                "出場價": fill,
                "數量": leg["qty"],
                "成本": cost,
                "收入": leg["qty"] * fill,
                "盈虧": pnl_net,
                "收益率": pnl_net / cost if cost else 0.0,
                "原因": reason,
            }
        )
        legs.remove(leg)
        if leg["purpose"] == "grid":
            stat["grid_closes"] += 1
            if cycle is not None:
                cycle["realized"] += pnl_net

    def close_all(price, time, reason):
        for leg in list(legs):
            close_leg(leg, price, time, reason)

    for i in range(n):
        o, h, l, c = open_[i], high[i], low[i], close[i]
        time = df.index[i]
        dirn = int(tr[i - 1]) if i > 0 else 0

        if not stat["liquidated"] and not legs and i > 0 and dirn != 0:
            leg = open_leg(dirn, o, "main", time)
            if leg is not None:
                cycle = {
                    "side": dirn, "add_count": 0, "last_add": leg["entry"], "locked": False,
                    "extreme": None, "grid_count": 0, "last_grid": None, "realized": 0.0,
                    "locked_loss": 0.0, "target_override": None,
                }

        if legs and cycle is not None:
            side = cycle["side"]
            if not cycle["locked"]:
                avg = _wavg_entry(legs)
                if lock_mode and add_step > 0 and cycle["add_count"] < add_max:
                    trig = cycle["last_add"] * (1 - side * add_step)
                    hit = l <= trig if side == 1 else h >= trig
                    if hit:
                        px = min(o, trig) if side == 1 else max(o, trig)
                        aleg = open_leg(side, px, "add", time)
                        if aleg is not None:
                            cycle["add_count"] += 1
                            cycle["last_add"] = aleg["entry"]
                            stat["add_opens"] += 1
                            avg = _wavg_entry(legs)
                lock_px = avg * (1 - side * hedge_pct)
                hit_lock = l <= lock_px if side == 1 else h >= lock_px
                if hit_lock:
                    px = min(o, lock_px) if side == 1 else max(o, lock_px)
                    if lock_mode:
                        total_notional = sum(x["qty"] * x["entry"] for x in legs)
                        hq = hedge_ratio * total_notional / px
                        hleg = open_leg(-side, px, "hedge", time, qty=hq)
                        if hleg is not None:
                            cycle["locked"] = True
                            cycle["locked_loss"] = abs(sum(_unrealized(x, hleg["entry"]) for x in legs))
                            cycle["extreme"] = min(hleg["entry"], l) if side == 1 else max(hleg["entry"], h)
                            cycle["grid_count"] = 0
                            cycle["last_grid"] = hleg["entry"]
                            cycle["realized"] = 0.0
                            stat["hedge_events"] += 1
                    else:
                        close_all(px, time, "停損")
                        cycle = None
                else:
                    tgt = cycle["target_override"] if cycle["target_override"] else avg * (1 + side * tp_pct)
                    hit_tp = h >= tgt if side == 1 else l <= tgt
                    if hit_tp:
                        px = max(o, tgt) if side == 1 else min(o, tgt)
                        close_all(px, time, "止盈")
                        cycle = None
            else:
                gside = -side
                if cycle["grid_count"] < grid_max:
                    trig = cycle["last_grid"] * (1 + gside * grid_step)
                    hit = h >= trig if gside == 1 else l <= trig
                    if hit:
                        px = max(o, trig) if gside == 1 else min(o, trig)
                        gleg = open_leg(gside, px, "grid", time)
                        if gleg is not None:
                            cycle["grid_count"] += 1
                            cycle["last_grid"] = gleg["entry"]
                            stat["grid_opens"] += 1
                for leg in list(legs):
                    if leg["purpose"] != "grid":
                        continue
                    gs = leg["side"]
                    tgt = leg["entry"] * (1 + gs * grid_tp)
                    hit = h >= tgt if gs == 1 else l <= tgt
                    if hit:
                        px = max(o, tgt) if gs == 1 else min(o, tgt)
                        close_leg(leg, px, time, "網格止盈")
                cycle["extreme"] = min(cycle["extreme"], l) if side == 1 else max(cycle["extreme"], h)
                unlocked = False
                if unlock_mode == "retrace":
                    if side == 1:
                        unlocked = c >= cycle["extreme"] * (1 + unlock_retrace)
                    else:
                        unlocked = c <= cycle["extreme"] * (1 - unlock_retrace)
                else:
                    open_unrl = sum(_unrealized(x, c) for x in legs)
                    unlocked = open_unrl + cycle["realized"] >= unlock_target * cycle["locked_loss"]
                if unlocked:
                    stat["unlock_events"] += 1
                    if unlock_action == "keep_direction":
                        for leg in list(legs):
                            if leg["purpose"] in ("hedge", "grid"):
                                close_leg(leg, c, time, "解鎖平對沖")
                        cycle["locked"] = False
                        cycle["add_count"] = 0
                        cycle["last_add"] = c
                        cycle["target_override"] = c * (1 + side * tp_pct)
                        cycle["extreme"] = None
                        cycle["realized"] = 0.0
                        cycle["locked_loss"] = 0.0
                        stat["keep_events"] += 1
                    else:
                        close_all(c, time, "解鎖")
                        cycle = None

        gross = sum(abs(x["qty"]) * c for x in legs)
        net_signed = sum(x["side"] * x["qty"] * c for x in legs)
        eq = equity_at(c)

        if legs and not stat["liquidated"] and eq <= gross * maint_ratio:
            close_all(c, time, "爆倉")
            stat["liquidations"] += 1
            stat["liquidated"] = True
            cycle = None
            eq = equity_at(c)

        if legs and fund_per_bar:
            fund = net_signed * fund_per_bar
            cash -= fund
            stat["funding_cost"] += fund

        if not legs:
            states[i] = STATE_FLAT
        elif cycle is not None and cycle["locked"]:
            states[i] = STATE_LOCKED
        else:
            states[i] = STATE_LONG if legs[0]["side"] == 1 else STATE_SHORT

        equity_vals[i] = equity_at(c)
        net_exp[i] = net_signed
        gross_exp[i] = gross
        eq_now = equity_vals[i]
        stat["max_gross"] = max(stat["max_gross"], gross)
        stat["max_legs"] = max(stat["max_legs"], len(legs))
        if eq_now > 0:
            stat["max_margin_ratio"] = max(stat["max_margin_ratio"], gross / (eq_now * leverage))
        if eq_now <= 0:
            stat["liquidated"] = True

    equity = pd.Series(equity_vals, index=df.index, name="equity")
    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        trades_df = pd.DataFrame(columns=HEDGE_TRADE_COLUMNS)
    else:
        trades_df = trades_df[HEDGE_TRADE_COLUMNS]
    closes = df["close"].astype(float)
    bh = float(closes.iloc[-1] / closes.iloc[0] - 1) if closes.iloc[0] else 0.0
    exposure = float(np.mean(states != STATE_FLAT))
    metrics = compute_metrics(equity, trades_df, periods_per_year=cfg["periods_per_year"], exposure=exposure, buy_hold_return=bh)
    return {
        "equity": equity,
        "trades": trades_df,
        "metrics": metrics,
        "stats": stat,
        "states": pd.Series(states, index=df.index, name="state"),
        "net_exposure": pd.Series(net_exp, index=df.index, name="net"),
        "gross_exposure": pd.Series(gross_exp, index=df.index, name="gross"),
    }


def run_hedge_backtest(df, params, settings, periods_per_year=365, custom_signal=None):
    if len(df) < 30:
        raise ValueError("數據不足，無法回測")
    cfg = dict(settings)
    cfg["periods_per_year"] = periods_per_year
    base = dict(DEFAULT_HEDGE_PARAMS)
    base.update(params or {})
    cfg.update({k: base[k] for k in PARAM_KEYS if k in base})
    cfg["order_notional"] = cfg.get("initial_capital", 10000.0) * cfg.get("order_notional_pct", 1.0)
    if custom_signal is not None:
        if isinstance(custom_signal, pd.Series):
            s = custom_signal.reindex(df.index).fillna(0.0)
        else:
            arr = np.asarray(custom_signal, dtype=float).ravel()
            s = pd.Series(arr, index=df.index) if len(arr) == len(df) else pd.Series(0.0, index=df.index)
        trend = s.apply(lambda v: 1 if v > 0 else (-1 if v < 0 else 0)).astype(int)
    else:
        trend = trend_signal(df, base)

    lock = _simulate(df, trend, cfg, lock_mode=True)
    stop = _simulate(df, trend, cfg, lock_mode=False)

    return HedgeResult(
        equity=lock["equity"],
        stop_equity=stop["equity"],
        trades=lock["trades"],
        metrics=lock["metrics"],
        stop_metrics=stop["metrics"],
        stats=lock["stats"],
        states=lock["states"],
        net_exposure=lock["net_exposure"],
        gross_exposure=lock["gross_exposure"],
    )
