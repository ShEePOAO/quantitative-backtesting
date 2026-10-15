import ast
import inspect
import itertools
import os

import numpy as np
import pandas as pd

from config import ASSETS, INTERVALS, PERIODS_PER_YEAR, STOCK_INTERVALS, STOCK_SYMBOLS
from core.backtest import run_backtest, run_long_short_backtest
from core.hedge import DEFAULT_HEDGE_PARAMS, DEFAULT_HEDGE_SETTINGS, run_hedge_backtest
from core import indicators as ind
from core.metrics import TRADE_COLUMNS, compute_metrics
from data.fetcher import get_data, import_available, interval_available

APP_DIR = os.path.dirname(os.path.abspath(__file__))
USER_STRAT_DIR = os.path.join(APP_DIR, "user_strategies")
os.makedirs(USER_STRAT_DIR, exist_ok=True)

_QS_CURRENT = {}


def _qs_param(name, default):
    return _QS_CURRENT.get(name, default)


def _period(label, default, mn=2, mx=400):
    return {"label": label, "type": "int", "min": mn, "max": mx, "step": 1, "default": default}


def _float(label, default, mn=0.5, mx=6.0, step=0.1):
    return {"label": label, "type": "float", "min": mn, "max": mx, "step": step, "default": default}


INDICATOR_SPECS = {
    "sma": {"args": ["n"], "meta": {"n": _period("SMA 週期", 20)}},
    "ema": {"args": ["n"], "meta": {"n": _period("EMA 週期", 20)}},
    "wma": {"args": ["n"], "meta": {"n": _period("WMA 週期", 20)}},
    "rma": {"args": ["n"], "meta": {"n": _period("RMA 週期", 14)}},
    "dema": {"args": ["n"], "meta": {"n": _period("DEMA 週期", 20)}},
    "hma": {"args": ["n"], "meta": {"n": _period("HMA 週期", 20)}},
    "stdev": {"args": ["n"], "meta": {"n": _period("標準差 週期", 20)}},
    "zscore": {"args": ["n"], "meta": {"n": _period("Z分數 週期", 20)}},
    "rsi": {"args": ["n"], "meta": {"n": _period("RSI 週期", 14, 2, 100)}},
    "roc": {"args": ["n"], "meta": {"n": _period("ROC 週期", 20)}},
    "mom": {"args": ["n"], "meta": {"n": _period("動量 週期", 10, 1, 400)}},
    "trix": {"args": ["n"], "meta": {"n": _period("TRIX 週期", 15)}},
    "macd": {"args": ["fast", "slow", "signal"], "meta": {"fast": _period("MACD 快線週期", 12, 2, 200), "slow": _period("MACD 慢線週期", 26, 3, 400), "signal": _period("MACD 訊號週期", 9, 2, 100)}},
    "ppo": {"args": ["fast", "slow", "signal"], "meta": {"fast": _period("PPO 快線週期", 12, 2, 200), "slow": _period("PPO 慢線週期", 26, 3, 400), "signal": _period("PPO 訊號週期", 9, 2, 100)}},
    "bollinger": {"args": ["n", "k"], "meta": {"n": _period("布林 週期", 20), "k": _float("布林 標準差倍數", 2.0, 0.5, 6.0)}},
    "tr": {"args": [], "meta": {}},
    "atr": {"args": ["n"], "meta": {"n": _period("ATR 週期", 14)}},
    "natr": {"args": ["n"], "meta": {"n": _period("NATR 週期", 14)}},
    "dmi": {"args": ["n"], "meta": {"n": _period("DMI 週期", 14)}},
    "adx": {"args": ["n"], "meta": {"n": _period("ADX 週期", 14)}},
    "cci": {"args": ["n"], "meta": {"n": _period("CCI 週期", 20)}},
    "mfi": {"args": ["n"], "meta": {"n": _period("MFI 週期", 14)}},
    "willr": {"args": ["n"], "meta": {"n": _period("威廉 週期", 14)}},
    "obv": {"args": [], "meta": {}},
    "vwap": {"args": ["n"], "meta": {"n": _period("VWAP 週期", 20)}},
    "vwma": {"args": ["n"], "meta": {"n": _period("VWMA 週期", 20)}},
    "cmf": {"args": ["n"], "meta": {"n": _period("CMF 週期", 20)}},
    "kdj": {"args": ["n", "m1", "m2"], "meta": {"n": _period("KDJ 週期", 9, 2, 100), "m1": _period("KDJ 平滑K", 3, 1, 20), "m2": _period("KDJ 平滑D", 3, 1, 20)}},
    "stoch": {"args": ["n", "m1", "m2"], "meta": {"n": _period("STOCH 週期", 14, 2, 100), "m1": _period("STOCH 平滑K", 3, 1, 20), "m2": _period("STOCH 平滑D", 3, 1, 20)}},
    "aroon": {"args": ["n"], "meta": {"n": _period("Aroon 週期", 25, 2, 200)}},
    "donchian": {"args": ["n"], "meta": {"n": _period("Donchian 週期", 20)}},
    "ao": {"args": ["fast", "slow"], "meta": {"fast": _period("AO 快線週期", 5, 2, 200), "slow": _period("AO 慢線週期", 34, 3, 400)}},
    "tema": {"args": ["n"], "meta": {"n": _period("TEMA 週期", 20)}},
    "kama": {"args": ["n", "fast", "slow"], "meta": {"n": _period("KAMA 週期", 10, 2, 200), "fast": _period("KAMA 快線週期", 2, 1, 50), "slow": _period("KAMA 慢線週期", 30, 3, 200)}},
    "linreg": {"args": ["n"], "meta": {"n": _period("線性迴歸 週期", 14)}},
    "midpoint": {"args": ["n"], "meta": {"n": _period("中間價 週期", 14)}},
    "bias": {"args": ["n"], "meta": {"n": _period("乖離率 週期", 20)}},
    "dpo": {"args": ["n"], "meta": {"n": _period("DPO 週期", 20)}},
    "cmo": {"args": ["n"], "meta": {"n": _period("CMO 週期", 14)}},
    "uo": {"args": ["fast", "mid", "slow"], "meta": {"fast": _period("UO 快線週期", 7, 2, 100), "mid": _period("UO 中線週期", 14, 3, 200), "slow": _period("UO 慢線週期", 28, 4, 400)}},
    "tsi": {"args": ["long", "short"], "meta": {"long": _period("TSI 長週期", 25, 2, 200), "short": _period("TSI 短週期", 13, 2, 100)}},
    "fi": {"args": ["n"], "meta": {"n": _period("FI 週期", 13)}},
    "eom": {"args": ["n"], "meta": {"n": _period("EOM 週期", 14)}},
    "supertrend": {"args": ["n", "mult"], "meta": {"n": _period("超級趨勢 週期", 10, 2, 100), "mult": _float("超級趨勢 倍數", 3.0, 0.5, 10.0)}},
    "psar": {"args": ["af", "maxaf"], "meta": {"af": _float("PSAR 加速", 0.02, 0.01, 0.5, 0.01), "maxaf": _float("PSAR 上限", 0.2, 0.05, 0.5, 0.01)}},
    "keltner": {"args": ["n", "mult"], "meta": {"n": _period("肯特納 週期", 20), "mult": _float("肯特納 倍數", 2.0, 0.5, 5.0)}},
    "stochrsi": {"args": ["n", "k"], "meta": {"n": _period("StochRSI 週期", 14, 2, 100), "k": _period("StochRSI 平滑", 3, 1, 20)}},
    "pvo": {"args": ["fast", "slow", "signal"], "meta": {"fast": _period("PVO 快線週期", 12, 2, 200), "slow": _period("PVO 慢線週期", 26, 3, 400), "signal": _period("PVO 訊號週期", 9, 2, 100)}},
    "rvi": {"args": ["n"], "meta": {"n": _period("RVI 週期", 10)}},
    "hh": {"args": ["n"], "meta": {"n": _period("最高價 週期", 20)}},
    "ll": {"args": ["n"], "meta": {"n": _period("最低價 週期", 20)}},
    "aroonosc": {"args": ["n"], "meta": {"n": _period("Aroon 擺盪 週期", 25, 2, 200)}},
    "medprice": {"args": [], "meta": {}},
    "typprice": {"args": [], "meta": {}},
    "wclprice": {"args": [], "meta": {}},
    "bop": {"args": [], "meta": {}},
    "nvi": {"args": [], "meta": {}},
    "pvi": {"args": [], "meta": {}},
}

NAMESPACE_EXTRA = {"pd": pd, "np": np, "_qs_param": _qs_param}
for _name in INDICATOR_SPECS:
    NAMESPACE_EXTRA[_name] = getattr(ind, _name)


class _IndicatorBinder(ast.NodeTransformer):
    def __init__(self):
        self.defs = {}
        self.counts = {}

    @staticmethod
    def _is_num(node):
        return isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)

    @staticmethod
    def _wrap(key, val):
        return ast.Call(func=ast.Name(id="_qs_param", ctx=ast.Load()),
                        args=[ast.Constant(value=key), val], keywords=[])

    def _next(self, base):
        n = self.counts.get(base, 0) + 1
        self.counts[base] = n
        return base if n == 1 else f"{base}~{n}"

    def _meta_for(self, ind_name, pname, key):
        m = dict(INDICATOR_SPECS[ind_name]["meta"].get(pname, {}))
        if "~" in key:
            m["label"] = (m.get("label") or pname) + " " + key.split("~")[1]
        return m

    def visit_Call(self, node):
        self.generic_visit(node)
        fn = node.func
        if not (isinstance(fn, ast.Name) and fn.id in INDICATOR_SPECS):
            return node
        spec = INDICATOR_SPECS[fn.id]
        names = spec["args"]
        provided = set()
        for i, arg in enumerate(node.args):
            if i == 0:
                continue
            pname = names[i - 1] if i - 1 < len(names) else None
            if pname:
                provided.add(pname)
                if self._is_num(arg):
                    key = self._next(f"{fn.id}__{pname}")
                    self.defs[key] = self._meta_for(fn.id, pname, key)
                    node.args[i] = self._wrap(key, arg)
        for kw in node.keywords:
            if kw.arg in names:
                provided.add(kw.arg)
                if self._is_num(kw.value):
                    key = self._next(f"{fn.id}__{kw.arg}")
                    self.defs[key] = self._meta_for(fn.id, kw.arg, key)
                    kw.value = self._wrap(key, kw.value)
        for p in [p for p in names if p not in provided]:
            key = self._next(f"{fn.id}__{p}")
            meta = self._meta_for(fn.id, p, key)
            self.defs[key] = meta
            dn = ast.Call(func=ast.Name(id="_qs_param", ctx=ast.Load()),
                          args=[ast.Constant(value=key), ast.Constant(value=meta.get("default"))], keywords=[])
            if node.keywords:
                node.keywords.append(ast.keyword(arg=p, value=dn))
            else:
                node.args.append(dn)
        return node


def _bind_indicators(code):
    tree = ast.parse(code)
    binder = _IndicatorBinder()
    tree = binder.visit(tree)
    ast.fix_missing_locations(tree)
    return compile(tree, "<custom_strategy>", "exec"), binder.defs


TEMPLATE = '''import pandas as pd
import numpy as np

PARAM_DEFS = {
    "fast": {"label": "快線週期", "type": "int", "min": 2, "max": 200, "default": 20, "step": 1},
    "slow": {"label": "慢線週期", "type": "int", "min": 5, "max": 400, "default": 60, "step": 1},
}

def generate(df, params):
    fast = df["close"].ewm(span=params["fast"], adjust=False).mean()
    slow = df["close"].ewm(span=params["slow"], adjust=False).mean()
    return (fast > slow).astype(int)
'''

_DF_CACHE = {}


def assets_payload():
    rows = []
    for sym, meta in ASSETS.items():
        rows.append({
            "symbol": sym,
            "label": meta.get("label", sym),
            "is_stock": sym in STOCK_SYMBOLS,
            "has_data": import_available(sym),
        })
    return {
        "assets": rows,
        "intervals": [{"value": k, "label": v} for k, v in INTERVALS.items()],
        "stock_intervals": STOCK_INTERVALS,
        "periods_per_year": PERIODS_PER_YEAR,
        "template": TEMPLATE,
    }


def availability_payload(symbol, source="csv"):
    return {iv: bool(interval_available(symbol, iv, source)) for iv in INTERVALS}


def load_df(symbol, interval, start, end, refresh, source):
    key = (symbol, interval, str(start), str(end), source)
    if not refresh and key in _DF_CACHE:
        return _DF_CACHE[key].copy()
    df = get_data(symbol, interval, start, end, refresh=refresh, source=source)
    _DF_CACHE[key] = df
    return df.copy()


def exec_custom(code):
    ns = dict(NAMESPACE_EXTRA)
    compiled, auto = _bind_indicators(code)
    ns["__QS_INDICATOR_DEFS__"] = auto
    exec(compiled, ns)
    return ns


def param_defs(ns):
    user = ns.get("PARAM_DEFS")
    user = user if isinstance(user, dict) else {}
    auto = ns.get("__QS_INDICATOR_DEFS__", {}) or {}
    merged = dict(user)
    for k, v in auto.items():
        if k not in merged:
            merged[k] = v
    return merged or None


def call_generate(ns, df, params):
    global _QS_CURRENT
    _QS_CURRENT = params or {}
    fn = ns.get("generate")
    if not callable(fn):
        raise ValueError("程式碼需定義 generate(df, params) 或 generate(df) 函式")
    nargs = len([p for p in inspect.signature(fn).parameters.values()
                 if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])
    sig = fn(df, params) if nargs >= 2 else fn(df)
    s = pd.Series(np.asarray(sig, dtype=float).ravel())
    if len(s) != len(df):
        s = pd.Series(sig)
        s = s.reindex(df.index).fillna(0.0)
    else:
        s.index = df.index
    return s.fillna(0.0)


def lookahead_check(ns, df, params, n_probes=12):
    full = call_generate(ns, df, params)
    n = len(df)
    lo = max(60, int(n * 0.1))
    if n - lo < n_probes + 5:
        return "pass", []
    idxs = sorted(set(np.linspace(lo, n - 1, n_probes).astype(int).tolist()))
    bad = []
    for k in idxs:
        sub = df.iloc[: k + 1]
        try:
            s = call_generate(ns, sub, params)
            v_sub = float(s.iloc[-1])
            v_full = float(full.iloc[k])
        except Exception:
            return "error", []
        if not np.isclose(v_sub, v_full, atol=1e-9, equal_nan=True):
            bad.append((str(df.index[k]), v_full, v_sub))
    return ("pass" if not bad else "fail"), bad


def run_custom(df, sig, settings, periods_per_year, use_hedge=False):
    if use_hedge:
        h_settings = dict(DEFAULT_HEDGE_SETTINGS)
        h_settings.update({k: v for k, v in settings.items() if k in ("initial_capital", "fee_rate", "slippage")})
        h_settings["order_notional_pct"] = settings.get("position_pct", 1.0)
        h_params = dict(DEFAULT_HEDGE_PARAMS)
        res = run_hedge_backtest(df, params=h_params, settings=h_settings,
                                 periods_per_year=periods_per_year, custom_signal=sig)
        return res, True, True
    if (sig < 0).any():
        ls_keys = {k: v for k, v in settings.items()
                   if k in ("initial_capital", "fee_rate", "slippage", "position_pct", "leverage", "vol_target", "risk_mgmt")}
        return run_long_short_backtest(df, sig, periods_per_year=periods_per_year, **ls_keys), True, False
    return run_backtest(df, sig.clip(0, 1), periods_per_year=periods_per_year, **settings), False, False


def _weights(symbols, weights):
    n = len(symbols)
    if weights:
        raw = {s: max(float(weights.get(s, 0.0) or 0.0), 0.0) for s in symbols}
        ssum = sum(raw.values())
        return {s: (v / ssum if ssum > 0 else 1.0 / n) for s, v in raw.items()}
    return {s: 1.0 / n for s in symbols}


def _combine_portfolio(curves, bh_curves, per_asset, trades_all, exposures, engines, caps, total, n, periods_per_year):
    cap_series = pd.Series(caps)
    eq_df = pd.DataFrame(curves).ffill().fillna(cap_series)
    bh_df = pd.DataFrame(bh_curves).ffill().fillna(cap_series)
    port_eq = eq_df.sum(axis=1)
    port_bh = bh_df.sum(axis=1)
    trades = pd.concat(trades_all, ignore_index=True) if trades_all else pd.DataFrame(columns=TRADE_COLUMNS)
    exposure = float(sum(exposures) / n) if n else 0.0
    bh_return = float(port_bh.iloc[-1] / port_bh.iloc[0] - 1) if len(port_bh) else 0.0
    metrics = compute_metrics(port_eq, trades, periods_per_year=periods_per_year,
                              exposure=exposure, buy_hold_return=bh_return)
    metrics["open_position"] = any(m.get("open_position") for m in per_asset.values())
    metrics["unrealized"] = float(sum(m.get("unrealized", 0.0) for m in per_asset.values()))
    return dict(portfolio_equity=port_eq, portfolio_bh=port_bh, equity_curves=eq_df,
                metrics=metrics, per_asset=per_asset, engines=engines, trades=trades, per_cap=total / n)


def _one_asset(ns, params, sym, interval, start, end, refresh, source, settings, use_hedge, cap, periods_per_year):
    settings_i = dict(settings)
    settings_i["initial_capital"] = cap
    df = load_df(sym, interval, start, end, refresh, source)
    sig = call_generate(ns, df, params)
    res, is_ls, is_hedge = run_custom(df, sig, settings_i, periods_per_year, use_hedge)
    return df, res, is_ls, is_hedge


def run_custom_portfolio(ns, params, symbols, interval, start, end, refresh, source,
                         settings, use_hedge, periods_per_year, weights=None, progress=None):
    n = len(symbols)
    total = float(settings["initial_capital"])
    w = _weights(symbols, weights)
    caps = {s: total * w[s] for s in symbols}
    curves, bh_curves, per_asset = {}, {}, {}
    trades_all, exposures = [], []
    engines = set()
    for i, sym in enumerate(symbols):
        if progress:
            progress(i, n, sym)
        df, res, is_ls, is_hedge = _one_asset(ns, params, sym, interval, start, end, refresh, source,
                                              settings, use_hedge, caps[sym], periods_per_year)
        curves[sym] = res.equity
        bh_curves[sym] = caps[sym] * df["close"].astype(float) / float(df["close"].iloc[0])
        per_asset[sym] = res.metrics
        exposures.append(res.metrics.get("exposure", 0.0))
        engines.add("網格鎖倉" if is_hedge else ("多空" if is_ls else "做多"))
        if len(res.trades):
            trades_all.append(res.trades.assign(資產=sym))
    out = _combine_portfolio(curves, bh_curves, per_asset, trades_all, exposures, engines, caps, total, n, periods_per_year)
    out["weights"] = w
    return out


def _fnum(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if np.isnan(f) or np.isinf(f):
        return None
    return f


def series_payload(s, max_points=6000):
    s = s.dropna()
    n = len(s)
    if n == 0:
        return {"t": [], "v": []}
    step = max(1, int(np.ceil(n / max_points)))
    s = s.iloc[::step]
    return {"t": [t.isoformat() for t in s.index], "v": [_fnum(v) for v in s.values]}


def trades_payload(df):
    if df is None or len(df) == 0:
        return []
    out = []
    for _, row in df.iterrows():
        rec = {}
        for col in df.columns:
            v = row[col]
            if isinstance(v, pd.Timestamp):
                rec[col] = v.isoformat()
            elif isinstance(v, (np.floating, float)):
                rec[col] = _fnum(v)
            elif isinstance(v, (np.integer, int)):
                rec[col] = int(v)
            else:
                rec[col] = v if v == v else None
        out.append(rec)
    return out


def _metrics_payload(m):
    keys = ["total_return", "cagr", "max_drawdown", "sharpe", "sortino", "calmar",
            "n_trades", "win_rate", "profit_factor", "avg_trade", "avg_win", "avg_loss",
            "best_trade", "worst_trade", "exposure", "buy_hold_return", "excess_return"]
    out = {k: _fnum(m.get(k)) for k in keys}
    out["open_position"] = bool(m.get("open_position", False))
    out["unrealized"] = _fnum(m.get("unrealized", 0.0))
    out["liquidated"] = bool(m.get("liquidated", False))
    return out


def _price_payload(df, max_points=6000):
    n = len(df)
    step = max(1, int(np.ceil(n / max_points)))
    sub = df.iloc[::step]
    return {
        "t": [t.isoformat() for t in sub.index],
        "o": [_fnum(v) for v in sub["open"].values],
        "h": [_fnum(v) for v in sub["high"].values],
        "l": [_fnum(v) for v in sub["low"].values],
        "c": [_fnum(v) for v in sub["close"].values],
    }


def _marks(series_flag, close):
    idx = series_flag.index[series_flag.values]
    return [{"t": t.isoformat(), "v": _fnum(close.loc[t])} for t in idx]


def _downsample_indexed(df, max_points=6000):
    n = len(df)
    step = max(1, int(np.ceil(n / max_points)))
    return df.iloc[::step]


def _exposure_series(df, trades):
    exp = pd.Series(0.0, index=df.index)
    if trades is None or len(trades) == 0:
        return exp
    idx = df.index
    pos = idx.searchsorted(idx, side="left")
    for _, tr in trades.iterrows():
        et = tr.get("進場時間"); xt = tr.get("出場時間")
        if pd.isna(et) or pd.isna(xt):
            continue
        i0 = idx.searchsorted(pd.Timestamp(et), side="left")
        i1 = idx.searchsorted(pd.Timestamp(xt), side="left")
        if i1 > i0:
            exp.iloc[i0:i1] = 1.0
    return exp


def _fees_series(df, trades):
    fees = pd.Series(0.0, index=df.index)
    if trades is None or len(trades) == 0:
        return fees
    for _, tr in trades.iterrows():
        try:
            f = (float(tr["成本"]) - float(tr["進場價"]) * float(tr["數量"])) + \
                (float(tr["出場價"]) * float(tr["數量"]) - float(tr["收入"]))
        except (KeyError, TypeError, ValueError):
            continue
        xt = pd.Timestamp(tr.get("出場時間"))
        if xt in fees.index:
            fees.loc[xt] += max(f, 0.0)
    return fees.cumsum()


def _data_quality(df, interval, start, end):
    tol_days = {"1w": 30, "1d": 10, "12h": 5, "6h": 5, "4h": 5, "1h": 3, "30m": 2, "15m": 2, "5m": 1}.get(interval, 5)
    tol = pd.Timedelta(days=tol_days)
    a0, a1 = df.index[0], df.index[-1]
    warns = []
    if start:
        rs = pd.Timestamp(start)
        if a0 - rs > tol:
            warns.append({"kind": "start_late", "requested": str(rs.date()), "actual": str(a0.date())})
    if end:
        re_ = pd.Timestamp(end)
        if re_ - a1 > tol:
            warns.append({"kind": "end_early", "requested": str(re_.date()), "actual": str(a1.date())})
    if len(df) < 50:
        warns.append({"kind": "few_bars", "n": int(len(df))})
    return {"start": str(a0.date()), "end": str(a1.date()), "bars": int(len(df)), "warnings": warns}


def run_single(ns, params, symbol, interval, start, end, refresh, source, settings, use_hedge):
    ppy = PERIODS_PER_YEAR[interval]
    df = load_df(symbol, interval, start, end, refresh, source)
    if len(df) < 2:
        raise ValueError("數據不足，無法回測")
    sig = call_generate(ns, df, params)
    res, is_ls, is_hedge = run_custom(df, sig, settings, ppy, use_hedge)
    la_status, la_bad = lookahead_check(ns, df, params)
    payload = {
        "mode": "single",
        "symbol": symbol,
        "interval": interval,
        "bars": int(len(df)),
        "engine": "網格鎖倉" if is_hedge else ("多空" if is_ls else "做多"),
        "nonzero_signals": int((sig != 0).sum()),
        "lookahead": {"status": la_status, "bad": la_bad},
        "data": _data_quality(df, interval, start, end),
        "metrics": _metrics_payload(res.metrics),
        "equity": series_payload(res.equity),
        "price": _price_payload(df),
        "buy_marks": _marks(res.buy_marks, df["close"].astype(float)),
        "sell_marks": _marks(res.sell_marks, df["close"].astype(float)),
        "trades": trades_payload(res.trades),
        "trade_columns": list(res.trades.columns),
    }
    bh = float(settings["initial_capital"]) * df["close"].astype(float) / float(df["close"].iloc[0])
    payload["buy_hold"] = series_payload(bh)
    payload["exposure"] = series_payload(_exposure_series(df, res.trades))
    payload["fees_cum"] = series_payload(_fees_series(df, res.trades))
    settings_g = dict(settings)
    settings_g["fee_rate"] = 0.0
    settings_g["slippage"] = 0.0
    try:
        res_g, _, _ = run_custom(df, sig, settings_g, ppy, use_hedge)
        payload["gross_equity"] = series_payload(res_g.equity)
    except Exception:
        payload["gross_equity"] = payload["equity"]
    if is_hedge:
        stats = dict(res.stats)
        stats = {k: (_fnum(v) if isinstance(v, (int, float, np.floating, np.integer)) else v) for k, v in stats.items()}
        payload["hedge"] = {
            "stats": stats,
            "stop_equity": series_payload(res.stop_equity),
            "states": series_payload(res.states),
            "gross_exposure": series_payload(res.gross_exposure),
            "net_exposure": series_payload(res.net_exposure),
            "stop_metrics": _metrics_payload(res.stop_metrics),
        }
    return payload


def _multi_response(port, symbols, interval, ns, params, first_df, start=None, end=None):
    try:
        la_status, la_bad = lookahead_check(ns, first_df, params)
    except Exception:
        la_status, la_bad = "error", []
    curves = {s: series_payload(port["equity_curves"][s]) for s in port["equity_curves"].columns}
    per_asset = {s: _metrics_payload(m) for s, m in port["per_asset"].items()}
    return {
        "mode": "multi",
        "symbols": symbols,
        "weights": port["weights"],
        "per_cap": _fnum(port["per_cap"]),
        "interval": interval,
        "engine": " / ".join(sorted(port["engines"])),
        "lookahead": {"status": la_status, "bad": la_bad},
        "data": _data_quality(first_df, interval, start, end),
        "metrics": _metrics_payload(port["metrics"]),
        "equity": series_payload(port["portfolio_equity"]),
        "buy_hold": series_payload(port["portfolio_bh"]),
        "equity_curves": curves,
        "per_asset": per_asset,
        "trades": trades_payload(port["trades"]),
        "trade_columns": list(port["trades"].columns),
    }


def _parse_request(req):
    ns = exec_custom(req.get("code", ""))
    params = dict(req.get("params") or {})
    settings = dict(req.get("settings") or {})
    settings.setdefault("initial_capital", 10000.0)
    settings.setdefault("fee_rate", 0.001)
    settings.setdefault("slippage", 0.0005)
    settings.setdefault("position_pct", 1.0)
    for k in ("stop_loss_pct", "take_profit_pct"):
        if settings.get(k) in (0, "", None):
            settings[k] = None
    settings.setdefault("leverage", 1.0)
    settings.setdefault("vol_target", None)
    settings.setdefault("risk_mgmt", None)
    return ns, params, settings


def run_request_stream(req):
    ns, params, settings = _parse_request(req)
    interval = req.get("interval", "1d")
    start = req.get("start") or None
    end = req.get("end") or None
    source = req.get("source", "csv")
    refresh = bool(req.get("refresh", False))
    use_hedge = bool(req.get("use_hedge", False))
    ppy = PERIODS_PER_YEAR[interval]

    if req.get("mode") == "multi":
        symbols = req.get("symbols") or []
        if not symbols:
            raise ValueError("請至少選擇一種資產")
        n = len(symbols)
        total = float(settings["initial_capital"])
        w = _weights(symbols, req.get("weights"))
        caps = {s: total * w[s] for s in symbols}
        curves, bh_curves, per_asset = {}, {}, {}
        trades_all, exposures = [], []
        engines = set()
        first_df = None
        for i, sym in enumerate(symbols):
            yield {"type": "progress", "done": i, "total": n, "label": sym}
            df, res, is_ls, is_hedge = _one_asset(ns, params, sym, interval, start, end, refresh, source,
                                                  settings, use_hedge, caps[sym], ppy)
            if first_df is None:
                first_df = df
            curves[sym] = res.equity
            bh_curves[sym] = caps[sym] * df["close"].astype(float) / float(df["close"].iloc[0])
            per_asset[sym] = res.metrics
            exposures.append(res.metrics.get("exposure", 0.0))
            engines.add("網格鎖倉" if is_hedge else ("多空" if is_ls else "做多"))
            if len(res.trades):
                trades_all.append(res.trades.assign(資產=sym))
        yield {"type": "progress", "done": n, "total": n, "label": "組合"}
        port = _combine_portfolio(curves, bh_curves, per_asset, trades_all, exposures, engines, caps, total, n, ppy)
        port["weights"] = w
        yield {"type": "result", "result": _multi_response(port, symbols, interval, ns, params, first_df, start, end)}
        return

    symbol = req.get("symbol", "BTC")
    yield {"type": "progress", "done": 0, "total": 1, "label": symbol}
    yield {"type": "result", "result": run_single(ns, params, symbol, interval, start, end, refresh, source, settings, use_hedge)}


def run_request(req):
    result = None
    for ev in run_request_stream(req):
        if ev.get("type") == "result":
            result = ev["result"]
    return result


MAX_COMBOS = 400
OPT_METRICS = ["sharpe", "total_return", "cagr", "max_drawdown", "calmar", "profit_factor", "win_rate"]


def optimize_stream(req):
    ns, params, settings = _parse_request(req)
    interval = req.get("interval", "1d")
    start = req.get("start") or None
    end = req.get("end") or None
    source = req.get("source", "csv")
    refresh = bool(req.get("refresh", False))
    use_hedge = bool(req.get("use_hedge", False))
    ppy = PERIODS_PER_YEAR[interval]
    symbol = req.get("symbol", "BTC")
    metric = req.get("metric", "sharpe")
    grid = req.get("grid") or {}
    split = float(req.get("split") or 0)
    if not grid:
        raise ValueError("請設定要掃描的參數範圍")

    df = load_df(symbol, interval, start, end, refresh, source)
    if len(df) < 30:
        raise ValueError("數據不足，無法優化")

    df_tr, df_te = df, None
    if 0.05 <= split <= 0.95:
        k = int(round(len(df) * split))
        if k >= 30 and (len(df) - k) >= 15:
            df_tr, df_te = df.iloc[:k], df.iloc[k:]

    axes = {}
    for k, spec in grid.items():
        lo = float(spec.get("min")); hi = float(spec.get("max")); st = float(spec.get("step") or 0)
        if st <= 0 or hi < lo:
            raise ValueError(f"參數 {k} 的範圍/步長不合法")
        vals = np.arange(lo, hi + st * 0.5, st)
        if spec.get("int"):
            vals = [int(round(v)) for v in vals]
        else:
            vals = [round(float(v), 6) for v in vals]
        if not vals:
            raise ValueError(f"參數 {k} 沒有可掃描的值")
        axes[k] = vals

    keys = list(axes.keys())
    combos = list(itertools.product(*[axes[k] for k in keys]))
    if len(combos) > MAX_COMBOS:
        raise ValueError(f"組合數 {len(combos)} 超過上限 {MAX_COMBOS}，請縮小範圍或加大步長")

    total = len(combos) * (2 if df_te is not None else 1)
    rows = []
    done = 0
    for combo in combos:
        p = dict(params)
        for k, v in zip(keys, combo):
            p[k] = v
        try:
            sig = call_generate(ns, df_tr, p)
            res, _, _ = run_custom(df_tr, sig, settings, ppy, use_hedge)
            m = _metrics_payload(res.metrics)
        except Exception:
            m = {k2: None for k2 in OPT_METRICS}
        rows.append({"p": {k: v for k, v in zip(keys, combo)}, "metrics": {k2: m.get(k2) for k2 in OPT_METRICS}})
        done += 1
        if done % 4 == 0 or done == total:
            yield {"type": "progress", "done": done, "total": total, "label": ""}

    if df_te is not None:
        for combo, row in zip(combos, rows):
            p = dict(params)
            for k, v in zip(keys, combo):
                p[k] = v
            try:
                sig = call_generate(ns, df_te, p)
                res, _, _ = run_custom(df_te, sig, settings, ppy, use_hedge)
                m = _metrics_payload(res.metrics)
            except Exception:
                m = {}
            row["oos"] = {k2: m.get(k2) for k2 in OPT_METRICS}
            done += 1
            if done % 4 == 0 or done == total:
                yield {"type": "progress", "done": done, "total": total, "label": ""}

    res = {
        "keys": keys, "metric": metric, "metrics": OPT_METRICS,
        "rows": rows, "symbol": symbol, "interval": interval, "combos": len(combos),
        "split": (split if df_te is not None else 0),
        "n_train": int(len(df_tr)),
        "n_test": (int(len(df_te)) if df_te is not None else 0),
        "train_end": (str(df_tr.index[-1].date()) if df_te is not None else None),
        "test_start": (str(df_te.index[0].date()) if df_te is not None else None),
    }
    yield {"type": "result", "result": res}


def run_optimize(req):
    result = None
    for ev in optimize_stream(req):
        if ev.get("type") == "result":
            result = ev["result"]
    return result


def _safe_name(name):
    base = os.path.basename(str(name)).strip()
    if not base:
        raise ValueError("檔名不可為空")
    if not base.endswith(".py"):
        base += ".py"
    if base.startswith(".") or os.sep in base or "/" in base:
        raise ValueError("檔名不合法")
    return base


def list_strategies():
    return sorted(f for f in os.listdir(USER_STRAT_DIR) if f.endswith(".py"))


def read_strategy(name):
    path = os.path.join(USER_STRAT_DIR, _safe_name(name))
    if not os.path.exists(path):
        raise ValueError("找不到策略檔")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def save_strategy(name, code):
    path = os.path.join(USER_STRAT_DIR, _safe_name(name))
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return os.path.basename(path)


def delete_strategy(name):
    path = os.path.join(USER_STRAT_DIR, _safe_name(name))
    if os.path.exists(path):
        os.remove(path)
    return os.path.basename(path)
