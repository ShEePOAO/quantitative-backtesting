# -*- coding: utf-8 -*-
"""
update_stocks.py -- 下載股票歷史資料（yfinance）供 Quant Studio 使用

抓兩種粒度，寫進 backtester 讀得懂的位置（預設與 Quant Studio 相同）：
  - 日線(1d, 全歷史)   -> <IMPORT_DIR>/<KEY>.csv      (供 1d / 1w)
  - 小時(1h, ~730 天)  -> <IMPORT_DIR>/<KEY>_1h.csv   (供 1h / 4h / 6h / 12h)

CSV 格式（與 data/fetcher._read_import_raw 相符）：
    ,DateTime,Open,High,Low,Close,Volume
    0,2024-10-21 00:00:00,14.29,20.36,14.09,20.0,13616700.0

用法：
    python update_stocks.py                # 更新全部
    python update_stocks.py 2330 0050 TSLA
    python update_stocks.py --list
"""
import argparse
import datetime
import glob
import os
import sys

import pandas as pd
import yfinance as yf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMPORT_DIR = os.environ.get("QUANT_IMPORT_DIR", r"C:\crypto-backtester\data\import_csv")
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")

# KEY -> (yahoo ticker, 顯示名稱)
STOCKS = {
    # 台股
    "2330": ("2330.TW", "台積電"),
    "0050": ("0050.TW", "元大台灣50"),
    "2317": ("2317.TW", "鴻海"),
    "2454": ("2454.TW", "聯發科"),
    "2308": ("2308.TW", "台達電"),
    "2303": ("2303.TW", "聯電"),
    # 美股
    "AAPL": ("AAPL", "Apple"),
    "MSFT": ("MSFT", "Microsoft"),
    "NVDA": ("NVDA", "Nvidia"),
    "GOOGL": ("GOOGL", "Alphabet"),
    "AMZN": ("AMZN", "Amazon"),
    "META": ("META", "Meta"),
    "TSLA": ("TSLA", "Tesla"),
    "AMD": ("AMD", "AMD"),
    "TSM": ("TSM", "TSMC ADR"),
    "AVGO": ("AVGO", "Broadcom"),
    # 既有（Serenity 相關）
    "NBIS": ("NBIS", "Nebius"),
    "SIVE": ("SIVE.ST", "Sivers (SIVE.ST)"),
    "LITE": ("LITE", "Lumentum"),
    "AXTI": ("AXTI", "AXT"),
    "AAOI": ("AAOI", "Applied Optoelectronics"),
    "IREN": ("IREN", "IREN"),
    "COIN": ("COIN", "Coinbase"),
    "CRCL": ("CRCL", "Circle"),
    "MSTR": ("MSTR", "MicroStrategy"),
    "RIOT": ("RIOT", "Riot"),
}

HEADER = ",DateTime,Open,High,Low,Close,Volume"
COLS = ["Open", "High", "Low", "Close", "Volume"]
JOBS = [("1d", "max", ""), ("1h", "730d", "_1h")]


def log(msg):
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def fetch(ticker, interval, period):
    df = yf.download(ticker, period=period, interval=interval,
                     auto_adjust=False, actions=False, progress=False, prepost=False, threads=False)
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[COLS].dropna(how="any")
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)
    return df.sort_index()


def write_csv(df, path, interval):
    fmt = "%Y-%m-%d 00:00:00" if interval.endswith("d") else "%Y-%m-%d %H:%M:%S"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(HEADER + "\n")
        for i, (dt, row) in enumerate(df.iterrows()):
            fh.write(f"{i},{dt.strftime(fmt)},{row['Open']},{row['High']},{row['Low']},{row['Close']},{row['Volume']}\n")


def clear_cache(key):
    removed = 0
    for p in glob.glob(os.path.join(CACHE_DIR, f"{key}_*_import.csv")):
        try:
            os.remove(p)
            removed += 1
        except OSError:
            pass
    return removed


def main():
    ap = argparse.ArgumentParser(description="Download stock history for Quant Studio")
    ap.add_argument("symbols", nargs="*", help="asset keys, e.g. 2330 0050 TSLA")
    ap.add_argument("--list", action="store_true", help="列出可用代號")
    ap.add_argument("--no-cache-clear", action="store_true")
    args = ap.parse_args()

    if args.list:
        for k, (t, name) in STOCKS.items():
            print(f"  {k:6s} {t:10s} {name}")
        return

    keys = args.symbols or list(STOCKS.keys())
    unknown = [s for s in keys if s not in STOCKS]
    if unknown:
        log(f"未知代號 {unknown}，可用：{list(STOCKS.keys())}")
        sys.exit(1)

    os.makedirs(IMPORT_DIR, exist_ok=True)
    log(f"IMPORT_DIR = {IMPORT_DIR}")
    for key in keys:
        ticker = STOCKS[key][0]
        for interval, period, suffix in JOBS:
            try:
                df = fetch(ticker, interval, period)
                if df is None or df.empty:
                    log(f"{key:6s} ({ticker:9s}) {interval:>3s} -> 無資料")
                    continue
                path = os.path.join(IMPORT_DIR, f"{key}{suffix}.csv")
                write_csv(df, path, interval)
                log(f"{key:6s} ({ticker:9s}) {interval:>3s} -> {len(df):>6d} rows  {df.index[0]} .. {df.index[-1]}")
            except Exception as e:  # noqa: BLE001
                log(f"{key:6s} ({ticker:9s}) {interval:>3s} FAILED: {e!r}")
        if not args.no_cache_clear:
            n = clear_cache(key)
            if n:
                log(f"{key:6s} cache cleared: {n}")
    log("done")


if __name__ == "__main__":
    main()
