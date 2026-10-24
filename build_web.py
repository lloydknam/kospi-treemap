"""CSV -> site/data.json (웹 인터랙티브 차트용 압축 데이터)
사용: python build_web.py data/kospi_mcap.csv data/kospi_index.csv site/data.json [--start 2025-04-01]
mcap: 억원 정수, chg: 등락률 x100 정수(전일대비 %), 없으면 null
"""
import sys, json, argparse
import numpy as np, pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("csv"); ap.add_argument("index"); ap.add_argument("out")
ap.add_argument("--start", default="2025-04-01")
a = ap.parse_args()

df = pd.read_csv(a.csv, parse_dates=["date"], dtype={"ticker": str})
df = df[df.date >= a.start]
dates = sorted(df.date.unique())
ix = pd.read_csv(a.index, parse_dates=["date"]).set_index("date")["close"].reindex(dates).ffill().bfill()

tickers = []
for t, g in df.groupby("ticker"):
    g = g.drop_duplicates("date", keep="last").set_index("date").reindex(dates)
    m = (g["mcap"] / 1e8).round()
    r = (g["chg"] * 100).round()
    if m.notna().sum() < 5: continue
    tickers.append({
        "c": t, "n": g["name"].dropna().iloc[-1],
        "m": [None if pd.isna(v) else int(v) for v in m],
        "r": [None if pd.isna(v) else int(v) for v in r],
    })
tickers.sort(key=lambda x: -(x["m"][-1] or 0))
out = {
    "updated": pd.Timestamp(dates[-1]).strftime("%Y-%m-%d"),
    "dates": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in dates],
    "index": [round(float(v), 2) for v in ix],
    "tickers": tickers,
}
with open(a.out, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
import os
print("saved", a.out, len(dates), "days", len(tickers), "tickers", round(os.path.getsize(a.out) / 1e6, 2), "MB")
