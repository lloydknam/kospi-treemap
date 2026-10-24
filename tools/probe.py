import yfinance as yf, requests, re, warnings
warnings.filterwarnings("ignore")
from yfinance import EquityQuery
try:
    q = EquityQuery("and", [EquityQuery("eq", ["exchange", "KSC"])])
    tot = 0; rows = []
    for off in range(0, 1500, 250):
        r = yf.screen(q, size=250, offset=off, sortField="intradaymarketcap", sortAsc=False)
        qs = r.get("quotes", [])
        if off == 0: print("total", r.get("total"), "keys", list(qs[0].keys())[:40])
        rows += qs
        if len(qs) < 250: break
    print("rows", len(rows))
    for x in rows[:5]: print(x.get("symbol"), x.get("shortName"), x.get("longName"), x.get("marketCap"), x.get("quoteType"), x.get("sharesOutstanding"))
    print("quoteTypes", {t: sum(1 for x in rows if x.get("quoteType") == t) for t in set(x.get("quoteType") for x in rows)})
    print("code0", sum(1 for x in rows if x["symbol"].split(".")[0].endswith("0")))
except Exception as e:
    print("screen ERR", repr(e)[:300])
for u in ["https://finance.naver.com/sise/sise_market_sum.naver?sosok=0&page=1", "https://finance.naver.com/sise/sise_market_sum.naver?sosok=0&page=20"]:
    try:
        r = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.encoding = "euc-kr"
        print(u[-12:], r.status_code, len(r.text), len(re.findall(r"code=(\d{6})", r.text)), r.text[:150].replace("\n", " "))
        print(re.findall(r'href="/item/main\.naver\?code=(\d{6})"[^>]*>([^<]+)<', r.text)[:3])
    except Exception as e:
        print("naver ERR", repr(e)[:200])
