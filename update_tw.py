# -*- coding: utf-8 -*-
"""update_tw.py -- 用 Fugle MarketData 抓台股 1 分 K（2023-05-23 起），存成 app 讀得到的 CSV

輸出：<專案>/data/import_csv/<SYMBOL>_1m.csv
格式：,DateTime,Open,High,Low,Close,Volume   （DateTime 為台北時間、naive）
      volume 單位＝「張」（Fugle 分 K 對整股為張；1 張 = 1000 股）

金鑰來源：環境變數 FUGLE_API_KEY，或專案根目錄 fugle_key.txt

用法：
    python update_tw.py                 # 抓全部 SYMBOLS
    python update_tw.py 2330 0050       # 只抓指定代號
    python update_tw.py --list
"""
import argparse
import datetime
import glob
import os
import sys
import time

import pandas as pd
import requests

BASE_URL = "https://api.fugle.tw/marketdata/v1.0/stock/historical/candles"
START = "2023-05-23"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.join(BASE_DIR, "data", "import_csv")
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
HEADER = ",DateTime,Open,High,Low,Close,Volume"

SYMBOLS = (
    ["0050", "0056", "006208", "00692", "00713", "00878", "00881", "00900", "00919", "00929"]
    + ["2330", "2317", "2454", "2308", "2303", "2412", "2379", "3711", "2301", "2357",
       "2382", "3231", "2377", "3008", "3034", "2408", "2474", "6505", "1301", "1303",
       "1326", "2002", "1101", "1216", "2207", "2603", "2609", "2615", "2618", "2881",
       "2882", "2891", "2884", "2892", "2886", "2885", "2880", "2890", "5871", "2912",
       "2707", "9910", "2105", "2395", "2385", "2409", "2344", "6176", "6669"]
)


def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def load_key():
    key = os.environ.get("FUGLE_API_KEY")
    if key:
        return key.strip()
    path = os.path.join(BASE_DIR, "fugle_key.txt")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    sys.exit("缺少 Fugle API key（設環境變數 FUGLE_API_KEY 或放 fugle_key.txt）")


def chunk_ranges(start, end, days=180):
    cur = datetime.date.fromisoformat(start)
    last = datetime.date.fromisoformat(end)
    while cur < last:
        nxt = min(cur + datetime.timedelta(days=days), last)
        yield cur.isoformat(), nxt.isoformat()
        cur = nxt + datetime.timedelta(days=1)


def fetch(session, key, symbol, frm, to, retries=4):
    params = {"timeframe": "1", "from": frm, "to": to, "sort": "asc",
              "fields": "open,high,low,close,volume"}
    for attempt in range(retries):
        r = session.get(f"{BASE_URL}/{symbol}", params=params,
                        headers={"X-API-KEY": key}, timeout=90)
        if r.status_code == 200:
            return r.json().get("data", [])
        if r.status_code == 404:
            return []
        if r.status_code in (429, 503):
            wait = float(r.headers.get("Retry-After", 5))
            time.sleep(max(wait, 5))
            continue
        r.raise_for_status()
    raise RuntimeError(f"{symbol} {frm}~{to} 重試多次仍失敗")


def to_df(rows):
    if not rows:
        return None
    df = pd.DataFrame(rows)
    dt = pd.to_datetime(df["date"], utc=True).dt.tz_convert("Asia/Taipei").dt.tz_localize(None)
    out = pd.DataFrame({
        "DateTime": dt,
        "Open": pd.to_numeric(df["open"], errors="coerce"),
        "High": pd.to_numeric(df["high"], errors="coerce"),
        "Low": pd.to_numeric(df["low"], errors="coerce"),
        "Close": pd.to_numeric(df["close"], errors="coerce"),
        "Volume": pd.to_numeric(df["volume"], errors="coerce") * 1000,  # 分K 單位為「張」→ 統一成「股」
    }).dropna()
    return out.drop_duplicates("DateTime").sort_values("DateTime").reset_index(drop=True)


def write_csv(df, path):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(HEADER + "\n")
        for i, row in enumerate(df.itertuples(index=False)):
            fh.write(f"{i},{row.DateTime:%Y-%m-%d %H:%M:%S},{row.Open},{row.High},"
                     f"{row.Low},{row.Close},{row.Volume}\n")


def clear_cache(symbol):
    n = 0
    for p in glob.glob(os.path.join(CACHE_DIR, f"{symbol}_*_import.csv")):
        try:
            os.remove(p)
            n += 1
        except OSError:
            pass
    return n


def fetch_daily(session, key, sym, frm, to, retries=4):
    params = {"timeframe": "D", "from": frm, "to": to, "sort": "asc",
              "adjusted": "true", "fields": "open,high,low,close,volume"}
    for _ in range(retries):
        r = session.get(f"{BASE_URL}/{sym}", params=params,
                        headers={"X-API-KEY": key}, timeout=60)
        if r.status_code == 200:
            return r.json().get("data", [])
        if r.status_code == 404:
            return []
        if r.status_code in (429, 503):
            time.sleep(max(float(r.headers.get("Retry-After", 5)), 5))
            continue
        r.raise_for_status()
    return []


def to_df_daily(rows):
    if not rows:
        return None
    df = pd.DataFrame(rows)
    out = pd.DataFrame({
        "DateTime": pd.to_datetime(df["date"].str.slice(0, 10)),
        "Open": pd.to_numeric(df["open"], errors="coerce"),
        "High": pd.to_numeric(df["high"], errors="coerce"),
        "Low": pd.to_numeric(df["low"], errors="coerce"),
        "Close": pd.to_numeric(df["close"], errors="coerce"),
        "Volume": pd.to_numeric(df["volume"], errors="coerce"),
    }).dropna()
    return out.drop_duplicates("DateTime").sort_values("DateTime").reset_index(drop=True)


def target_dirs():
    dirs = [PROJ_DIR]
    other = r"C:\crypto-backtester\data\import_csv"
    if os.path.isdir(other) and os.path.abspath(other) != os.path.abspath(PROJ_DIR):
        dirs.append(other)
    return dirs


def run_daily(session, key, syms, today):
    dirs = target_dirs()
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    log(f"daily dirs = {dirs}")
    ok = 0
    for sym in syms:
        rows = []
        try:
            for frm, to in chunk_ranges("2010-01-01", today, 300):
                rows += fetch_daily(session, key, sym, frm, to)
                time.sleep(1.0)
        except Exception as e:  # noqa: BLE001
            log(f"{sym:6s} daily ERROR {e!r}")
            continue
        df = to_df_daily(rows)
        if df is None or df.empty:
            log(f"{sym:6s} daily -> 無資料")
            continue
        for d in dirs:
            write_csv(df, os.path.join(d, f"{sym}.csv"))
        clear_cache(sym)
        ok += 1
        log(f"{sym:6s} daily -> {len(df):>6d} rows  {df.DateTime.iloc[0].date()} .. {df.DateTime.iloc[-1].date()}")
    log(f"daily done  ok={ok}/{len(syms)}")


def main():
    ap = argparse.ArgumentParser(description="Fetch TW stock data from Fugle")
    ap.add_argument("symbols", nargs="*", help="代號，預設全部 SYMBOLS")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--days", type=int, default=180, help="每批查詢天數（<365）")
    ap.add_argument("--daily", action="store_true", help="抓日線（還原）→ <SYM>.csv，寫入兩個 import 目錄")
    args = ap.parse_args()
    if args.list:
        print(" ".join(SYMBOLS))
        return
    key = load_key()
    syms = args.symbols or SYMBOLS
    today = datetime.date.today().isoformat()
    session = requests.Session()
    if args.daily:
        run_daily(session, key, syms, today)
        return
    os.makedirs(PROJ_DIR, exist_ok=True)
    ok = 0
    for sym in syms:
        rows = []
        try:
            for frm, to in chunk_ranges(START, today, args.days):
                rows += fetch(session, key, sym, frm, to)
                time.sleep(1.0)
        except Exception as e:  # noqa: BLE001
            log(f"{sym:6s} ERROR {e!r}")
            continue
        df = to_df(rows)
        if df is None or df.empty:
            log(f"{sym:6s} -> 無資料")
            continue
        write_csv(df, os.path.join(PROJ_DIR, f"{sym}_1m.csv"))
        cl = clear_cache(sym)
        ok += 1
        log(f"{sym:6s} -> {len(df):>7d} rows  {df.DateTime.iloc[0]} .. {df.DateTime.iloc[-1]}  cache_cleared={cl}")
    log(f"done  ok={ok}/{len(syms)}")


if __name__ == "__main__":
    main()
