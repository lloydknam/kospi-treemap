"""KOSPI 일별 시총/등락률 증분 수집 -> data/kospi_mcap.csv
사용: python collect.py [--start 20260102]
"""
import argparse, os, sys, time
from datetime import datetime
import pandas as pd
from pykrx import stock

OUT = "data/kospi_mcap.csv"
ap = argparse.ArgumentParser()
ap.add_argument("--start", default="20260102")
ap.add_argument("--end", default=datetime.now().strftime("%Y%m%d"))
a = ap.parse_args()

old = None
start = a.start
if os.path.exists(OUT):
    old = pd.read_csv(OUT, parse_dates=["date"], dtype={"ticker": str})
    start = (old["date"].max() + pd.Timedelta(days=1)).strftime("%Y%m%d")
if start > a.end:
    print("up to date"); sys.exit(0)

rows, errs = [], 0
for d in pd.bdate_range(start, a.end).strftime("%Y%m%d"):
    try:
        cap = stock.get_market_cap(d, market="KOSPI")
        ohl = stock.get_market_ohlcv(d, market="KOSPI")
    except Exception as e:
        errs += 1; print(d, "ERR", repr(e)[:200]); continue
    if cap.empty or cap["시가총액"].sum() == 0:
        print(d, "holiday"); continue
    df = cap[["시가총액"]].join(ohl[["종가", "등락률"]])
    df["date"] = pd.to_datetime(d); df["ticker"] = df.index
    rows.append(df); print(d, len(df)); time.sleep(0.3)

if not rows:
    print("no data fetched, errors:", errs); sys.exit(1 if errs else 0)
new = pd.concat(rows, ignore_index=True)
new["name"] = new["ticker"].map({t: stock.get_market_ticker_name(t) for t in new["ticker"].unique()})
new = new.rename(columns={"시가총액": "mcap", "종가": "close", "등락률": "chg"})
out = pd.concat([old, new], ignore_index=True) if old is not None else new
out.to_csv(OUT, index=False, encoding="utf-8-sig")
print("saved", len(out), "rows")
