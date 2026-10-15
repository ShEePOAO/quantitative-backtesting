# -*- coding: utf-8 -*-
"""repair_splits.py -- 偵測並回推修正未調整的股票分割斷點

Yahoo 對多數美股會自動做分割調整，但有些標的（如台股 0050）沒有分割記錄，
原始價會出現假的暴跌（例如 4:1 分割 = 單日約 -75%）。
本工具掃描 CSV，偵測「接近常見分割倍率（2/3/4/5/6/7/10/20）的單日暴跌」，
把斷點之前的 OHLC 除以倍率、成交量乘以倍率（back-adjust），使序列連續。

用法：
    python repair_splits.py                 # 掃描並修正 data/import_csv/*.csv
    python repair_splits.py --dry           # 只顯示將修正的斷點，不寫檔
    python repair_splits.py path1.csv ...   # 指定檔案
"""
import argparse
import glob
import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(BASE_DIR, "data", "import_csv")
COMMON = [2, 3, 4, 5, 6, 7, 10, 20]
TOL = 0.03


def detect_splits(close):
    ev = []
    for i in range(1, len(close)):
        f = close.iloc[i - 1] / close.iloc[i]
        if f < 1.15:
            continue
        best = min(COMMON, key=lambda k: abs(k - f) / k)
        if abs(best - f) / best <= TOL:
            ev.append((close.index[i], float(best)))
    return ev


def repair_file(path, dry=False):
    df = pd.read_csv(path, index_col=0)
    if "DateTime" not in df.columns:
        return []
    dts = pd.to_datetime(df["DateTime"])
    series = pd.Series(df["Close"].values, index=dts).sort_index()
    ev = detect_splits(series)
    if not ev:
        return []
    for date, ratio in ev:
        mask = dts < date
        for c in ("Open", "High", "Low", "Close"):
            df.loc[mask, c] = df.loc[mask, c] / ratio
        df.loc[mask, "Volume"] = df.loc[mask, "Volume"] * ratio
    if not dry:
        df["DateTime"] = dts
        df.to_csv(path, index=True, index_label="", date_format="%Y-%m-%d %H:%M:%S")
    return [(str(d.date()), r) for d, r in ev]


def main():
    ap = argparse.ArgumentParser(description="Repair unadjusted stock splits in CSVs")
    ap.add_argument("files", nargs="*", help="CSV paths (default: data/import_csv/*.csv)")
    ap.add_argument("--dry", action="store_true", help="show splits without writing")
    args = ap.parse_args()
    files = args.files or sorted(glob.glob(os.path.join(DEFAULT_DIR, "*.csv")))
    if not files:
        print("no files")
        return
    n = 0
    for f in files:
        ev = repair_file(f, dry=args.dry)
        if ev:
            n += 1
            print(f"{os.path.basename(f):16s} {'(dry)' if args.dry else 'fixed'}: {ev}")
    if n == 0:
        print("no split discontinuities found")
    print("done")


if __name__ == "__main__":
    main()
