"""KOSPI 전종목 일별 시총 -> data/kospi_mcap.csv, data/kospi_index.csv
- 종목/이름/현재 시총: 네이버 증권 모바일 API (우선주 포함, ETF/ETN 제외)
- 일별 종가: Yahoo (split 조정 종가)
- 일별 시총 = 종가 x 발행주식수. 주식수 = 네이버 현재 시총 / 현재 종가(상수),
  시총 상위 보통주는 Yahoo 주식수 변화율(유증/소각)을 반영
(KRX 직접 수집은 해외 IP에서 막혀 우회한 근사치)
"""
import os, sys, time, warnings
import numpy as np, pandas as pd, requests, yfinance as yf
warnings.filterwarnings("ignore")
START = "2024-12-20"
H = {"User-Agent": "Mozilla/5.0"}
os.makedirs("data", exist_ok=True)

# ---- 1) 네이버 전종목
stocks = []
for p in range(1, 40):
    j = requests.get(f"https://m.stock.naver.com/api/stocks/marketValue/KOSPI?page={p}&pageSize=100",
                     headers=H, timeout=30).json()
    s = j.get("stocks", [])
    stocks += s
    if len(s) < 100: break
meta = {}
for x in stocks:
    if x.get("stockEndType") != "stock": continue
    try:
        mv, px = float(x["marketValueRaw"]), float(x["closePriceRaw"])
    except Exception:
        continue
    if mv > 0 and px > 0:
        meta[x["itemCode"]] = {"name": x["stockName"], "shares": mv / px, "mv": mv}
print("naver stocks", len(meta))
if len(meta) < 300: sys.exit("naver list failed")
codes = sorted(meta, key=lambda c: -meta[c]["mv"])

# ---- 2) Yahoo 종가 (배치)
closes = {}
for b in range(0, len(codes), 80):
    batch = codes[b:b + 80]
    try:
        d = yf.download([c + ".KS" for c in batch], start=START, auto_adjust=False,
                        group_by="ticker", threads=True, progress=False)
        for c in batch:
            try:
                s = d[c + ".KS"]["Close"].dropna()
                if len(s): closes[c] = s
            except Exception:
                pass
    except Exception as e:
        print("batch ERR", b, repr(e)[:150])
    print("batch", b, "got", len(closes)); time.sleep(1)
print("tickers with prices", len(closes), "of", len(codes))
if len(closes) < 300: sys.exit("price download failed")

# ---- 3) 상위 보통주: 주식수 변화율
ratio = {}
for c in [c for c in codes if c.endswith("0")][:120]:
    if c not in closes: continue
    try:
        sh = yf.Ticker(c + ".KS").get_shares_full(start=START)
        if sh is None or len(sh) < 2: continue
        sh.index = pd.DatetimeIndex(sh.index).tz_localize(None).normalize()
        sh = sh[~sh.index.duplicated(keep="last")].sort_index()
        r = sh / sh.iloc[-1]
        if 0.5 < r.min() and r.max() < 2:          # 이상치 방지
            ratio[c] = r
    except Exception as e:
        pass
    time.sleep(0.15)
print("share-ratio tickers", len(ratio))

# ---- 4) 합치기
rows = []
for c, cl in closes.items():
    cl.index = pd.DatetimeIndex(cl.index).tz_localize(None).normalize()
    cl = cl[~cl.index.duplicated(keep="last")]
    sh = meta[c]["shares"]
    if c in ratio:
        rr = ratio[c].reindex(cl.index.union(ratio[c].index)).ffill().reindex(cl.index).bfill()
        shs = sh * rr
    else:
        shs = pd.Series(sh, index=cl.index)
    d = pd.DataFrame({"close": cl, "mcap": cl * shs})
    d["chg"] = d["close"].pct_change() * 100
    d["ticker"], d["name"] = c, meta[c]["name"]
    d.index.name = "date"
    rows.append(d.reset_index())
out = pd.concat(rows, ignore_index=True).dropna(subset=["mcap"])
out["mcap"] = out["mcap"].round(0).astype("int64"); out["close"] = out["close"].round(1); out["chg"] = out["chg"].round(3)
out.to_csv("data/kospi_mcap.csv", index=False, encoding="utf-8-sig")
print("saved", len(out), "rows", out["date"].nunique(), "days", out["ticker"].nunique(), "tickers")

# ---- 5) 코스피 지수
ixh = yf.Ticker("^KS11").history(start=START)
ixh.index = ixh.index.tz_localize(None).normalize(); ixh.index.name = "date"
ixh[["Close"]].rename(columns={"Close": "close"}).reset_index().to_csv("data/kospi_index.csv", index=False)
print("index rows", len(ixh))
