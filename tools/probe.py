import yfinance as yf, requests, re, warnings, json
warnings.filterwarnings("ignore")
from yfinance import EquityQuery
try:
    q = EquityQuery("eq", ["exchange", "KSC"])
    rows = []
    for off in range(0, 1500, 250):
        r = yf.screen(q, size=250, offset=off, sortField="intradaymarketcap", sortAsc=False)
        qs = r.get("quotes", [])
        if off == 0: print("total", r.get("total"), "keys", list(qs[0].keys())[:40])
        rows += qs
        if len(qs) < 250: break
    print("rows", len(rows))
    for x in rows[:4]: print(x.get("symbol"), x.get("shortName"), x.get("marketCap"), x.get("quoteType"), x.get("sharesOutstanding"))
    print("quoteTypes", {t: sum(1 for x in rows if x.get("quoteType") == t) for t in set(x.get("quoteType") for x in rows)})
    print("code0", sum(1 for x in rows if x["symbol"].split(".")[0].endswith("0")))
except Exception as e:
    print("screen ERR", repr(e)[:300])
H = {"User-Agent": "Mozilla/5.0"}
for u in ["https://m.stock.naver.com/api/stocks/marketValue/KOSPI?page=1&pageSize=100",
          "https://m.stock.naver.com/api/stocks/marketValue/KOSPI?page=9&pageSize=100"]:
    try:
        r = requests.get(u, headers=H, timeout=20)
        print(u[-30:], r.status_code, len(r.text), r.text[:300].replace("\n", " "))
    except Exception as e:
        print("naver ERR", repr(e)[:200])
