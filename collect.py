"""KOSPI 상위 종목 일별 시총 -> data/kospi_mcap.csv
종목/이름: 네이버 금융 시총순위, 종가: Yahoo, 시총 = 종가 x (일별 발행주식수, Yahoo)
(KRX 직접 수집은 해외 IP에서 막혀 우회. 시총은 보통주 기준 근사치)
"""
import re, sys, time, warnings
import pandas as pd, requests, yfinance as yf
warnings.filterwarnings("ignore")
START, TOPN = "2026-01-01", 120
H = {"User-Agent": "Mozilla/5.0"}

codes, names = [], {}
for pg in range(1, 4):
    r = requests.get("https://finance.naver.com/sise/sise_market_sum.naver",
                     params={"sosok": 0, "page": pg}, headers=H, timeout=20)
    r.encoding = "euc-kr"
    for c, n in re.findall(r'href="/item/main\.naver\?code=(\d{6})"[^>]*>([^<]+)<', r.text):
        if c not in names:
            names[c] = n.strip(); codes.append(c)
codes = codes[:TOPN]
print("tickers", len(codes), codes[:5], [names[c] for c in codes[:5]])
if len(codes) < 30: sys.exit("ticker list failed")

rows = []
for i, c in enumerate(codes):
    try:
        t = yf.Ticker(c + ".KS")
        h = t.history(start=START, auto_adjust=False)
        sh = t.get_shares_full(start=START)
        if h.empty or sh is None or len(sh) == 0: print(c, names[c], "no data"); continue
        h.index = h.index.tz_localize(None).normalize()
        sh.index = sh.index.tz_localize(None).normalize()
        sh = sh[~sh.index.duplicated(keep="last")].sort_index()
        s = sh.reindex(h.index.union(sh.index)).ffill().reindex(h.index)
        s = s.bfill()
        d = pd.DataFrame({"close": h["Close"], "mcap": h["Close"] * s})
        d["chg"] = d["close"].pct_change() * 100
        d["ticker"], d["name"] = c, names[c]
        d.index.name = "date"
        rows.append(d.reset_index()); print(i, c, names[c], len(d))
    except Exception as e:
        print(c, names[c], "ERR", repr(e)[:120])
    time.sleep(0.2)

if not rows: sys.exit("no data")
out = pd.concat(rows, ignore_index=True).dropna(subset=["mcap"])
out = out[out["date"] >= "2026-01-02"]
out.to_csv("data/kospi_mcap.csv", index=False, encoding="utf-8-sig")
print("saved", len(out), "rows", out["date"].nunique(), "days")
