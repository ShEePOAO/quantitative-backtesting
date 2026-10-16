# -*- coding: utf-8 -*-
"""clean_tw.py -- 清洗台股 1 分 K（update_tw.py 下載的 data/import_csv/<SYM>_1m.csv）

清洗內容：
1) 移除交易時段外（09:00–13:30）的列
2) 以 Fugle 日 K「還原 vs 未還原」推得每日還原係數，回推調整分鐘 OHLC，
   使除權息／分割日不再有假跳空（total-return 連續序列）
   - volume 不改（維持 Fugle 的張數）
3) 依時間排序

用法：
    python clean_tw.py                 # 清洗全部 *_1m.csv
    python clean_tw.py 2330 0050       # 只清指定代號
"""
import argparse
import datetime
import glob
import os
import time

import pandas as pd
import requests

BASE = "https://api.fugle.tw/marketdata/v1.0/stock/historical/candles"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(BASE_DIR, "data", "import_csv")
START = "2023-05-23"
SESSION = (datetime.time(9, 0), datetime.time(13, 30))


def load_key():
    key = os.environ.get("FUGLE_API_KEY")
    if key:
        return key.strip()
    path = os.path.join(BASE_DIR, "fugle_key.txt")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    raise SystemExit("缺少 Fugle API key")


def chunk_ranges(start, end, days=300):
    cur = datetime.date.fromisoformat(start)
    last = datetime.date.fromisoformat(end)
    while cur < last:
        nxt = min(cur + datetime.timedelta(days=days), last)
        yield cur.isoformat(), nxt.isoformat()
        cur = nxt + datetime.timedelta(days=1)


def daily_close(session, key, sym, adjusted, frm, to, retries=4):
    params = {"timeframe": "D", "from": frm, "to": to, "sort": "asc", "fields": "close"}
    if adjusted:
        params["adjusted"] = "true"
    for _ in range(retries):
        r = session.get(f"{BASE}/{sym}", params=params, headers={"X-API-KEY": key}, timeout=60)
        if r.status_code == 200:
            return {x["date"][:10]: x["close"] for x in r.json().get("data", [])}
        if r.status_code == 404:
            return {}
        if r.status_code in (429, 503):
            time.sleep(max(float(r.headers.get("Retry-After", 5)), 5))
            continue
        r.raise_for_status()
    return {}


def build_factor(session, key, sym, today):
    raw, adj = {}, {}
    for frm, to in chunk_ranges(START, today, 300):
        raw.update(daily_close(session, key, sym, False, frm, to))
        time.sleep(0.5)
        adj.update(daily_close(session, key, sym, True, frm, to))
        time.sleep(0.5)
    fac = {d: adj[d] / raw[d] for d in (set(raw) & set(adj)) if raw.get(d)}
    if not fac:
        return None
    return pd.Series(fac).sort_index()


def clean(session, key, sym, today):
    path = os.path.join(PROJ, f"{sym}_1m.csv")
    if not os.path.exists(path):
        return None
    d = pd.read_csv(path)
    d["DateTime"] = pd.to_datetime(d["DateTime"])
    n0 = len(d)
    tod = d["DateTime"].dt.time
    d = d[(tod >= SESSION[0]) & (tod <= SESSION[1])].copy()
    n_oob = n0 - len(d)

    ser = build_factor(session, key, sym, today)
    fac_lo = fac_hi = None
    if ser is not None and len(ser):
        day = d["DateTime"].dt.date.astype(str)
        f = day.map(ser).ffill().bfill().astype(float)
        if f.notna().all():
            for c in ("Open", "High", "Low", "Close"):
                d[c] = (d[c] * f).round(4)
            fac_lo, fac_hi = float(ser.min()), float(ser.max())

    d = d.sort_values("DateTime")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(",DateTime,Open,High,Low,Close,Volume\n")
        for i, row in enumerate(d.itertuples(index=False)):
            fh.write(f"{i},{row.DateTime:%Y-%m-%d %H:%M:%S},{row.Open},{row.High},"
                     f"{row.Low},{row.Close},{row.Volume}\n")
    return n_oob, len(d), fac_lo, fac_hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="*")
    args = ap.parse_args()
    key = load_key()
    today = datetime.date.today().isoformat()
    syms = args.symbols or [os.path.basename(p)[:-7] for p in sorted(glob.glob(os.path.join(PROJ, "*_1m.csv")))]
    session = requests.Session()
    for sym in syms:
        t0 = time.time()
        try:
            res = clean(session, key, sym, today)
        except Exception as e:  # noqa: BLE001
            print(f"[{sym}] ERROR {e!r}", flush=True)
            continue
        if res is None:
            print(f"[{sym}] 無檔", flush=True)
            continue
        n_oob, n, flo, fhi = res
        fac = f"{flo:.4f}~{fhi:.4f}" if flo is not None else "n/a"
        print(f"[{sym:6s}] rows={n:>7d}  oob_dropped={n_oob}  factor={fac}  ({time.time()-t0:.0f}s)", flush=True)
    print("done")


if __name__ == "__main__":
    main()
