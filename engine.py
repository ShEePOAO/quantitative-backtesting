import inspect
import itertools
import os

import numpy as np
import pandas as pd

from config import ASSETS, INTERVALS, PERIODS_PER_YEAR, STOCK_INTERVALS, STOCK_SYMBOLS
from core.backtest import run_backtest, run_long_short_backtest
from core.hedge import DEFAULT_HEDGE_PARAMS, DEFAULT_HEDGE_SETTINGS, run_hedge_backtest
from core.indicators import atr, bollinger, ema, macd, roc, rsi, sma
from core.metrics import TRADE_COLUMNS, compute_metrics
from data.fetcher import get_data, import_available

APP_DIR = os.path.dirname(os.path.abspath(__file__))
USER_STRAT_DIR = os.path.join(APP_DIR, "user_strategies")
os.makedirs(USER_STRAT_DIR, exist_ok=True)

NAMESPACE_EXTRA = {
    "pd": pd, "np": np, "sma": sma, "ema": ema, "rsi": rsi,
    "macd": macd, "bollinger": bollinger, "atr": atr, "roc": roc,
}

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


def load_df(symbol, interval, start, end, refresh, source):
    key = (symbol, interval, str(start), str(end), source)
    if not refresh and key in _DF_CACHE:
        return _DF_CACHE[key].copy()
    df = get_data(symbol, interval, start, end, refresh=refresh, source=source)
    _DF_CACHE[key] = df
    return df.copy()


def exec_custom(code):
    ns = dict(NAMESPACE_EXTRA)
    exec(compile(code, "<custom_strategy>", "exec"), ns)
    return ns


def param_defs(ns):
    pd_defs = ns.get("PARAM_DEFS")
    if isinstance(pd_defs, dict) and pd_defs:
        return pd_defs
    return None


def call_generate(ns, df, params):
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


def _multi_response(port, symbols, interval, ns, params, first_df):
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
        yield {"type": "result", "result": _multi_response(port, symbols, interval, ns, params, first_df)}
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
    if not grid:
        raise ValueError("請設定要掃描的參數範圍")

    df = load_df(symbol, interval, start, end, refresh, source)
    if len(df) < 30:
        raise ValueError("數據不足，無法優化")

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

    total = len(combos)
    rows = []
    for i, combo in enumerate(combos):
        p = dict(params)
        for k, v in zip(keys, combo):
            p[k] = v
        try:
            sig = call_generate(ns, df, p)
            res, _, _ = run_custom(df, sig, settings, ppy, use_hedge)
            m = _metrics_payload(res.metrics)
        except Exception:
            m = {k2: None for k2 in OPT_METRICS}
        rows.append({"p": {k: v for k, v in zip(keys, combo)}, "metrics": {k2: m.get(k2) for k2 in OPT_METRICS}})
        if i % 4 == 0 or i == total - 1:
            yield {"type": "progress", "done": i + 1, "total": total, "label": ""}

    yield {"type": "result", "result": {
        "keys": keys, "metric": metric, "metrics": OPT_METRICS,
        "rows": rows, "symbol": symbol, "interval": interval, "combos": total,
    }}


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
