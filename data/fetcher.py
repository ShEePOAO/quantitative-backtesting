import os
import sys
import time

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import ASSETS, STOCK_SYMBOLS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
IMPORT_DIR = os.environ.get("QUANT_IMPORT_DIR", r"C:\crypto-backtester\data\import_csv")
BUNDLED_IMPORT_DIR = os.path.join(BASE_DIR, "data", "import_csv")
IMPORT_DIRS = [IMPORT_DIR]
if os.path.abspath(BUNDLED_IMPORT_DIR) != os.path.abspath(IMPORT_DIR):
    IMPORT_DIRS.append(BUNDLED_IMPORT_DIR)
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(IMPORT_DIR, exist_ok=True)

BINANCE_BASE_URLS = ["https://data-api.binance.vision", "https://api.binance.com"]

INTERVAL_MS = {
    "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "4h": 14_400_000, "6h": 21_600_000, "12h": 43_200_000,
    "1d": 86_400_000, "1w": 604_800_000,
}

RESAMPLE_RULE = {
    "5m": "5min", "15m": "15min", "30m": "30min",
    "1h": "1h", "4h": "4h", "6h": "6h", "12h": "12h", "1d": "1D", "1w": "1W",
}
OHLCV_AGG = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}


def import_available(symbol):
    return any(os.path.exists(os.path.join(d, f"{symbol}.csv")) for d in IMPORT_DIRS)


_IV_RANK = {"5m": 0, "15m": 1, "30m": 2, "1h": 3, "4h": 4, "6h": 5, "12h": 6, "1d": 7, "1w": 8}


def _native_rank(symbol):
    for suffix, iv in (("_1m", "5m"), ("_5m", "5m"), ("_1h", "1h")):
        for d in IMPORT_DIRS:
            if os.path.exists(os.path.join(d, f"{symbol}{suffix}.csv")):
                return _IV_RANK[iv]
    for d in IMPORT_DIRS:
        if os.path.exists(os.path.join(d, f"{symbol}.csv")):
            return _IV_RANK["1d"] if symbol in STOCK_SYMBOLS else _IV_RANK["5m"]
    return None


def interval_available(symbol, interval, source="csv"):
    if source == "binance":
        return True
    if os.path.exists(os.path.join(CACHE_DIR, f"{symbol}_{interval}_import.csv")):
        return True
    nr = _native_rank(symbol)
    if nr is None:
        return False
    return _IV_RANK[interval] >= nr


def any_available(symbol):
    for iv in _IV_RANK:
        if os.path.exists(os.path.join(CACHE_DIR, f"{symbol}_{iv}_import.csv")):
            return True
    return _native_rank(symbol) is not None


def get_data(symbol, interval="1d", start=None, end=None, refresh=False, source="binance"):
    if source == "csv":
        return _get_import(symbol, interval, start, end, refresh)
    binance_symbol = ASSETS[symbol]["binance"]
    return _get_binance(binance_symbol, interval, start, end, refresh)


def _norm_ts(ts, default):
    ts = pd.to_datetime(ts) if ts is not None else default
    if ts.tzinfo is not None:
        ts = ts.tz_localize(None)
    return ts


def _read_cache(path):
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        needed = ["open", "high", "low", "close", "volume"]
        if not all(c in df.columns for c in needed):
            return None
        for col in needed:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["open", "high", "low", "close"])
        return df[~df.index.duplicated()].sort_index()
    except Exception:
        return None


def _slice(df, start, end):
    mask = (df.index >= start) & (df.index <= end)
    return df.loc[mask]


def _fetch_klines_paginated(symbol, interval, start, end):
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    step = INTERVAL_MS[interval]
    rows = []
    cur = start_ms
    errors = 0
    while cur < end_ms:
        batch = None
        for base in BINANCE_BASE_URLS:
            try:
                resp = requests.get(
                    f"{base}/api/v3/klines",
                    params={
                        "symbol": symbol,
                        "interval": interval,
                        "startTime": cur,
                        "endTime": end_ms,
                        "limit": 1000,
                    },
                    timeout=20,
                )
                resp.raise_for_status()
                batch = resp.json()
                break
            except Exception:
                continue
        if batch is None:
            errors += 1
            if errors >= 3:
                raise ConnectionError("Binance API 連線失敗，請檢查網絡連線後重試")
            time.sleep(2)
            continue
        if not batch:
            break
        rows.extend(batch)
        last_ts = batch[-1][0]
        if last_ts <= cur:
            break
        cur = last_ts + step
        time.sleep(0.15)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(
        rows,
        columns=[
            "open_time", "open", "high", "low", "close", "volume", "close_time",
            "quote_vol", "trades", "taker_base", "taker_quote", "ignore",
        ],
    )
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df.set_index("open_time")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df[["open", "high", "low", "close", "volume"]]


def _get_binance(symbol, interval, start, end, refresh):
    cache_path = os.path.join(CACHE_DIR, f"{symbol}_{interval}.csv")
    start = _norm_ts(start, pd.Timestamp("2017-08-17"))
    end = _norm_ts(end, pd.Timestamp.now(tz="UTC").tz_localize(None))
    cached = None if refresh else _read_cache(cache_path)
    df = cached
    need_fetch = True
    if df is not None and not df.empty:
        c_min, c_max = df.index.min(), df.index.max()
        gap = pd.Timedelta(milliseconds=INTERVAL_MS[interval])
        if start >= c_min and c_max >= end - gap:
            need_fetch = False
    if need_fetch:
        fetch_start = start
        if df is not None and not df.empty and df.index.min() <= start:
            fetch_start = df.index.max() + pd.Timedelta(milliseconds=INTERVAL_MS[interval])
        new_df = _fetch_klines_paginated(symbol, interval, fetch_start, end)
        if df is not None and not df.empty and not new_df.empty:
            df = pd.concat([df, new_df]).sort_index()
            df = df[~df.index.duplicated(keep="last")]
        elif not new_df.empty:
            df = new_df
        if df is not None and not df.empty:
            df.to_csv(cache_path)
    if df is None or df.empty:
        raise ValueError(f"Binance 無法取得 {symbol} {interval} 數據，請檢查網絡或稍後重試")
    return _slice(df, start, end)


SUBDaily_INTERVALS = {"5m", "15m", "30m", "1h", "4h", "6h", "12h"}


def _import_path(symbol, interval=None):
    if interval in SUBDaily_INTERVALS:
        for suffix in ("_1m", "_5m", "_1h"):
            for d in IMPORT_DIRS:
                p = os.path.join(d, f"{symbol}{suffix}.csv")
                if os.path.exists(p):
                    return p
    for d in IMPORT_DIRS:
        p = os.path.join(d, f"{symbol}.csv")
        if os.path.exists(p):
            return p
    return None


def _read_import_raw(symbol, interval=None):
    path = _import_path(symbol, interval)
    if path is None:
        raise ValueError(f"找不到 {symbol} 的 CSV 檔案（{IMPORT_DIRS}）")
    df = pd.read_csv(path, index_col=0)
    df.index = pd.to_datetime(df["DateTime"])
    df = df.drop(columns=["DateTime"])
    df.columns = [c.lower() for c in df.columns]
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"])
    bad_low = df["low"] <= 0
    df.loc[bad_low, "low"] = df.loc[bad_low, ["open", "close"]].min(axis=1)
    bad_high = df["high"] <= 0
    df.loc[bad_high, "high"] = df.loc[bad_high, ["open", "close"]].max(axis=1)
    df = df[~df.index.duplicated()].sort_index()
    return df[["open", "high", "low", "close", "volume"]]


def _get_import(symbol, interval, start, end, refresh):
    cache_path = os.path.join(CACHE_DIR, f"{symbol}_{interval}_import.csv")
    if not refresh:
        cached = _read_cache(cache_path)
        if cached is not None and not cached.empty:
            start = _norm_ts(start, cached.index.min())
            end = _norm_ts(end, cached.index.max())
            return _slice(cached, start, end)
    raw = _read_import_raw(symbol, interval)
    if raw.empty:
        raise ValueError(f"{symbol} 的 CSV 數據為空")
    df = raw.resample(RESAMPLE_RULE[interval]).agg(OHLCV_AGG).dropna(subset=["open"])
    df.to_csv(cache_path)
    start = _norm_ts(start, df.index.min())
    end = _norm_ts(end, df.index.max())
    return _slice(df, start, end)
