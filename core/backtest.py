from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.indicators import atr as _atr
from core.metrics import TRADE_COLUMNS, compute_metrics

LS_TRADE_COLUMNS = ["方向"] + TRADE_COLUMNS


@dataclass
class BacktestResult:
    equity: pd.Series
    trades: pd.DataFrame
    metrics: dict
    signals: pd.Series
    buy_marks: pd.Series
    sell_marks: pd.Series


class PositionSizer:
    """動態倉位（廣義逆馬丁 / 馬丁）。

    每筆交易結束後，用「最近交易盈虧的加權平均」決定下一筆的倉位倍率：
      - 近期為正 → scale *= win
      - 近期為負 → scale *= loss
    倍率限制在 [floor, cap]，換倉時實際倉位 = base_pct * scale，再限制在 [min_pos, max_pos]。
    - 逆馬丁：win>1（連勝加倉）、loss<1（連虧縮倉）
    - 馬丁：loss>1（連虧加倉）、win<1
    mode="fixed"（或 cfg 為 None）時完全不調整。
    """

    def __init__(self, cfg=None):
        cfg = cfg or {}
        self.enabled = cfg.get("mode", "fixed") != "fixed"
        self.win = float(cfg.get("win", 1.1))
        self.loss = float(cfg.get("loss", 0.9))
        self.cap = float(cfg.get("cap", 2.0))
        self.floor = float(cfg.get("floor", 0.25))
        self.lookback = max(1, int(cfg.get("lookback", 1)))
        self.decay = float(cfg.get("decay", 0.5))
        self.min_pos = float(cfg.get("min_pos", 0.05))
        self.max_pos = float(cfg.get("max_pos", 1.0))
        self.hist = []
        self.scale = 1.0

    def pct(self, base_pct):
        if not self.enabled:
            return base_pct
        return min(max(base_pct * self.scale, self.min_pos), self.max_pos)

    def update(self, pnl):
        if not self.enabled:
            return
        self.hist.append(float(pnl))
        if len(self.hist) > self.lookback:
            self.hist.pop(0)
        weights = [self.decay ** (len(self.hist) - 1 - i) for i in range(len(self.hist))]
        s = sum(w * p for w, p in zip(weights, self.hist))
        if s > 0:
            self.scale = min(self.scale * self.win, self.cap)
        elif s < 0:
            self.scale = max(self.scale * self.loss, self.floor)


def _vol_scale(df, target, window, cap, floor, periods_per_year):
    """波動目標：回傳每根 bar 的倉位縮放倍率（年化目標波動 ÷ 平滑後已實現波動，夾在 [floor, cap]）。
    只依「當根以前」的資料計算，無前視。target 為 None 時回傳 None（停用）。"""
    if target is None:
        return None
    r = df["close"].astype(float).pct_change().fillna(0.0)
    rv = r.rolling(int(window)).std() * np.sqrt(periods_per_year)
    rv = rv.ewm(span=max(1, int(window) // 3)).mean()
    sc = (float(target) / rv).clip(lower=float(floor), upper=float(cap))
    return sc.bfill().fillna(1.0)


def _atr_series(df, atr_stop_mult, atr_stop_n):
    if atr_stop_mult and float(atr_stop_mult) > 0:
        try:
            return _atr(df, int(atr_stop_n)).astype(float)
        except Exception:
            return None
    return None


def run_backtest(
    df,
    signals,
    initial_capital=10000.0,
    fee_rate=0.001,
    slippage=0.0005,
    stop_loss_pct=None,
    take_profit_pct=None,
    position_pct=1.0,
    leverage=1.0,
    vol_target=None,
    vol_window=60,
    vol_cap=2.0,
    vol_floor=0.2,
    periods_per_year=365,
    risk_mgmt=None,
    trailing_stop_pct=None,
    max_hold_bars=None,
    atr_stop_mult=None,
    atr_stop_n=14,
    max_drawdown_stop=None,
):
    if len(df) < 2:
        raise ValueError("數據不足，無法回測")
    sig = signals.reindex(df.index).fillna(0.0).clip(0, 1)
    vol_scale = _vol_scale(df, vol_target, vol_window, vol_cap, vol_floor, periods_per_year)
    atr_series = _atr_series(df, atr_stop_mult, atr_stop_n)
    trail_pct = float(trailing_stop_pct) if trailing_stop_pct else None
    atr_mult = float(atr_stop_mult) if atr_series is not None else None
    dds = float(max_drawdown_stop) if max_drawdown_stop else None
    mhold = int(max_hold_bars) if max_hold_bars else None
    n = len(df)
    cash = float(initial_capital)
    qty = 0.0
    entry_time = None
    entry_price = None
    entry_cost = None
    entry_i = -1
    stop_price = None
    take_price = None
    trail_peak = None
    halted = False
    peak_eq = float(initial_capital)
    equity_vals = np.zeros(n)
    in_market = np.zeros(n, dtype=bool)
    buy_marks = np.zeros(n, dtype=bool)
    sell_marks = np.zeros(n, dtype=bool)
    trades = []
    prev_equity = cash
    sizer = PositionSizer(risk_mgmt)
    liquidated = False

    def record_exit(i, px, reason):
        nonlocal cash, qty, entry_time, entry_price, entry_cost, stop_price, take_price, entry_i, trail_peak
        proceeds = qty * px * (1 - fee_rate)
        cash += proceeds
        trades.append(
            {
                "進場時間": entry_time,
                "進場價": entry_price,
                "出場時間": df.index[i],
                "出場價": px,
                "數量": qty,
                "成本": entry_cost,
                "收入": proceeds,
                "盈虧": proceeds - entry_cost,
                "收益率": (proceeds - entry_cost) / entry_cost if entry_cost else 0.0,
                "原因": reason,
            }
        )
        sizer.update(proceeds - entry_cost)
        sell_marks[i] = True
        qty = 0.0
        entry_time = entry_price = entry_cost = stop_price = take_price = None
        entry_i = -1
        trail_peak = None

    for i in range(n):
        o = float(df["open"].iloc[i])
        h = float(df["high"].iloc[i])
        l = float(df["low"].iloc[i])
        c = float(df["close"].iloc[i])
        exited = False
        if i > 0 and qty > 0:
            if trail_pct is not None and trail_peak is not None:
                trail_peak = max(trail_peak, h)
                tlvl = trail_peak * (1 - trail_pct)
            else:
                tlvl = None
            slvl = stop_price
            if tlvl is not None:
                slvl = tlvl if slvl is None else max(slvl, tlvl)
            if slvl is not None and l <= slvl:
                reason = "移動停損" if (tlvl is not None and slvl == tlvl) else "停損"
                record_exit(i, min(o, slvl) * (1 - slippage), reason)
                exited = True
            elif take_price is not None and h >= take_price:
                record_exit(i, max(o, take_price) * (1 - slippage), "止盈")
                exited = True
            elif mhold is not None and entry_i >= 0 and (i - entry_i) >= mhold:
                record_exit(i, o * (1 - slippage), "時間出場")
                exited = True
        target = float(sig.iloc[i - 1]) if i > 0 else 0.0
        if target > 0 and qty <= 0 and not exited and not halted:
            px = o * (1 + slippage)
            vsc = float(vol_scale.iloc[i - 1]) if (vol_scale is not None and i > 0) else 1.0
            spend = max(prev_equity, 0.0) * sizer.pct(position_pct) * leverage * vsc
            qty = spend / (px * (1 + fee_rate))
            cost = qty * px * (1 + fee_rate)
            cash -= cost
            entry_time = df.index[i]
            entry_price = px
            entry_cost = cost
            entry_i = i
            cands = []
            if stop_loss_pct:
                cands.append(px * (1 - float(stop_loss_pct)))
            if atr_series is not None:
                a = float(atr_series.iloc[max(0, i - 1)])
                if np.isfinite(a) and a > 0:
                    cands.append(px - atr_mult * a)
            stop_price = max(cands) if cands else None
            if take_profit_pct:
                take_price = px * (1 + float(take_profit_pct))
            trail_peak = h if trail_pct is not None else None
            buy_marks[i] = True
            slvl = stop_price
            if trail_pct is not None and trail_peak is not None:
                tlvl = trail_peak * (1 - trail_pct)
                slvl = tlvl if slvl is None else max(slvl, tlvl)
            if slvl is not None and l <= slvl:
                reason = "移動停損" if (tlvl is not None and slvl == tlvl) else "停損"
                record_exit(i, min(o, slvl) * (1 - slippage), reason)
                exited = True
            elif take_price is not None and h >= take_price:
                record_exit(i, max(o, take_price) * (1 - slippage), "止盈")
                exited = True
        elif target <= 0 and qty > 0 and not exited:
            record_exit(i, o * (1 - slippage), "訊號離場")
        equity_vals[i] = cash + qty * c
        in_market[i] = qty > 0
        prev_equity = equity_vals[i]
        peak_eq = max(peak_eq, equity_vals[i])
        if dds is not None and not halted and peak_eq > 0 and (peak_eq - equity_vals[i]) / peak_eq >= dds:
            if qty > 0:
                record_exit(i, c * (1 - slippage), "回撤停手")
                equity_vals[i] = cash
                in_market[i] = False
            halted = True
            prev_equity = equity_vals[i]
            peak_eq = equity_vals[i]
        if equity_vals[i] <= 0:
            liquidated = True
            equity_vals[i:] = 0.0
            cash = 0.0
            qty = 0.0
            break

    equity = pd.Series(equity_vals, index=df.index, name="equity")
    trades_df = pd.DataFrame(trades, columns=TRADE_COLUMNS)
    closes = df["close"].astype(float)
    buy_hold_return = float(closes.iloc[-1] / closes.iloc[0] - 1) if closes.iloc[0] else 0.0
    metrics = compute_metrics(
        equity,
        trades_df,
        periods_per_year=periods_per_year,
        exposure=float(in_market.mean()),
        buy_hold_return=buy_hold_return,
    )
    metrics["open_position"] = qty > 0
    metrics["unrealized"] = (
        float(qty * float(df["close"].iloc[-1]) - entry_cost)
        if (qty > 0 and entry_cost is not None) else 0.0
    )
    metrics["liquidated"] = liquidated
    return BacktestResult(
        equity=equity,
        trades=trades_df,
        metrics=metrics,
        signals=sig,
        buy_marks=pd.Series(buy_marks, index=df.index),
        sell_marks=pd.Series(sell_marks, index=df.index),
    )


def run_long_short_backtest(
    df,
    positions,
    initial_capital=10000.0,
    fee_rate=0.001,
    slippage=0.0005,
    position_pct=1.0,
    leverage=1.0,
    vol_target=None,
    vol_window=60,
    vol_cap=2.0,
    vol_floor=0.2,
    periods_per_year=365,
    risk_mgmt=None,
    trailing_stop_pct=None,
    max_hold_bars=None,
    atr_stop_mult=None,
    atr_stop_n=14,
    max_drawdown_stop=None,
):
    if len(df) < 2:
        raise ValueError("數據不足，無法回測")
    raw = pd.Series(np.asarray(positions, dtype=float), index=df.index).reindex(df.index).fillna(0.0)
    vol_scale = _vol_scale(df, vol_target, vol_window, vol_cap, vol_floor, periods_per_year)
    atr_series = _atr_series(df, atr_stop_mult, atr_stop_n)
    trail_pct = float(trailing_stop_pct) if trailing_stop_pct else None
    atr_mult = float(atr_stop_mult) if atr_series is not None else None
    dds = float(max_drawdown_stop) if max_drawdown_stop else None
    mhold = int(max_hold_bars) if max_hold_bars else None
    tgt = raw.apply(lambda v: 1.0 if v > 0 else (-1.0 if v < 0 else 0.0))
    o = df["open"].astype(float).values
    h = df["high"].astype(float).values
    l = df["low"].astype(float).values
    c = df["close"].astype(float).values
    n = len(df)
    cash = float(initial_capital)
    side = 0.0
    qty = 0.0
    entry_price = None
    entry_time = None
    entry_fee = 0.0
    entry_i = -1
    stop_price = None
    trail_ext = None
    halted = False
    peak_eq = float(initial_capital)
    equity_vals = np.zeros(n)
    in_market = np.zeros(n, dtype=bool)
    buy_marks = np.zeros(n, dtype=bool)
    sell_marks = np.zeros(n, dtype=bool)
    trades = []
    prev_equity = float(initial_capital)
    sizer = PositionSizer(risk_mgmt)
    liquidated = False

    def open_pos(s, i, price, time, notional):
        nonlocal cash, side, qty, entry_price, entry_time, entry_fee, entry_i, stop_price, trail_ext
        fill = price * (1 + slippage) if s > 0 else price * (1 - slippage)
        q = notional / fill
        fee = q * fill * fee_rate
        cash -= fee
        side, qty, entry_price, entry_time, entry_fee = s, q, fill, time, fee
        entry_i = i
        stop_price = None
        if atr_series is not None:
            a = float(atr_series.iloc[max(0, i - 1)])
            if np.isfinite(a) and a > 0:
                stop_price = fill - atr_mult * a if s > 0 else fill + atr_mult * a
        trail_ext = (h[i] if s > 0 else l[i]) if trail_pct is not None else None
        if s > 0:
            buy_marks[i] = True
        else:
            sell_marks[i] = True

    def close_pos(i, price, time, reason):
        nonlocal cash, side, qty, entry_price, entry_time, entry_fee, entry_i, stop_price, trail_ext
        fill = price * (1 - slippage) if side > 0 else price * (1 + slippage)
        gross = qty * (fill - entry_price) * side
        xfee = qty * fill * fee_rate
        cash += gross - xfee
        pnl_net = gross - entry_fee - xfee
        cost = qty * entry_price
        sizer.update(pnl_net)
        trades.append(
            {
                "方向": "多" if side > 0 else "空",
                "進場時間": entry_time,
                "進場價": entry_price,
                "出場時間": time,
                "出場價": fill,
                "數量": qty,
                "成本": cost,
                "收入": qty * fill,
                "盈虧": pnl_net,
                "收益率": pnl_net / cost if cost else 0.0,
                "原因": reason,
            }
        )
        if side > 0:
            sell_marks[i] = True
        else:
            buy_marks[i] = True
        side, qty, entry_price, entry_time, entry_fee = 0.0, 0.0, None, None, 0.0
        entry_i = -1
        stop_price = None
        trail_ext = None

    for i in range(n):
        stopped = False
        if side != 0.0 and i > 0:
            if trail_pct is not None and trail_ext is not None:
                trail_ext = max(trail_ext, h[i]) if side > 0 else min(trail_ext, l[i])
            slvl = stop_price
            tlvl = None
            if trail_pct is not None and trail_ext is not None:
                tlvl = trail_ext * (1 - trail_pct) if side > 0 else trail_ext * (1 + trail_pct)
                slvl = tlvl if slvl is None else (max(slvl, tlvl) if side > 0 else min(slvl, tlvl))
            hit = slvl is not None and ((side > 0 and l[i] <= slvl) or (side < 0 and h[i] >= slvl))
            if hit:
                px = min(o[i], slvl) if side > 0 else max(o[i], slvl)
                close_pos(i, px, df.index[i], "移動停損" if (tlvl is not None and slvl == tlvl) else "停損")
                stopped = True
            elif mhold is not None and entry_i >= 0 and (i - entry_i) >= mhold:
                close_pos(i, o[i], df.index[i], "時間出場")
                stopped = True
        target = float(tgt.iloc[i - 1]) if i > 0 else 0.0
        if not stopped and not halted and target != side:
            if side != 0.0:
                close_pos(i, o[i], df.index[i], "訊號離場" if target == 0 else "反手")
            if target != 0.0:
                vsc = float(vol_scale.iloc[i - 1]) if (vol_scale is not None and i > 0) else 1.0
                notional = max(prev_equity, 0.0) * sizer.pct(position_pct) * leverage * vsc
                if notional > 0 and o[i] > 0:
                    open_pos(target, i, o[i], df.index[i], notional)
        all_pnl = qty * (c[i] - entry_price) * side if side != 0.0 else 0.0
        equity_vals[i] = cash + all_pnl
        in_market[i] = side != 0.0
        prev_equity = equity_vals[i]
        peak_eq = max(peak_eq, equity_vals[i])
        if dds is not None and not halted and peak_eq > 0 and (peak_eq - equity_vals[i]) / peak_eq >= dds:
            if side != 0.0:
                close_pos(i, c[i], df.index[i], "回撤停手")
                equity_vals[i] = cash
                in_market[i] = False
            halted = True
            prev_equity = equity_vals[i]
            peak_eq = equity_vals[i]
        if equity_vals[i] <= 0:
            liquidated = True
            equity_vals[i:] = 0.0
            cash = 0.0
            side = 0.0
            qty = 0.0
            break

    equity = pd.Series(equity_vals, index=df.index, name="equity")
    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        trades_df = pd.DataFrame(columns=LS_TRADE_COLUMNS)
    else:
        trades_df = trades_df[LS_TRADE_COLUMNS]
    closes = df["close"].astype(float)
    buy_hold_return = float(closes.iloc[-1] / closes.iloc[0] - 1) if closes.iloc[0] else 0.0
    metrics = compute_metrics(
        equity, trades_df, periods_per_year=periods_per_year,
        exposure=float(in_market.mean()), buy_hold_return=buy_hold_return,
    )
    metrics["open_position"] = side != 0.0
    metrics["unrealized"] = (
        float(qty * (float(df["close"].iloc[-1]) - entry_price) * side)
        if (side != 0.0 and entry_price is not None) else 0.0
    )
    metrics["liquidated"] = liquidated
    return BacktestResult(
        equity=equity,
        trades=trades_df,
        metrics=metrics,
        signals=tgt,
        buy_marks=pd.Series(buy_marks, index=df.index),
        sell_marks=pd.Series(sell_marks, index=df.index),
    )
