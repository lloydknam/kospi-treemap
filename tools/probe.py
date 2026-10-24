import requests, json
H = {"User-Agent": "Mozilla/5.0"}
r = requests.get("https://m.stock.naver.com/api/stocks/marketValue/KOSPI?page=1&pageSize=100", headers=H, timeout=20).json()
print({k: v for k, v in r.items() if k != "stocks"})
print(json.dumps(r["stocks"][0], ensure_ascii=False))
print(json.dumps(r["stocks"][1], ensure_ascii=False)[:600])
allr = []
for p in range(1, 15):
    j = requests.get(f"https://m.stock.naver.com/api/stocks/marketValue/KOSPI?page={p}&pageSize=100", headers=H, timeout=20).json()
    s = j.get("stocks", [])
    allr += s
    if len(s) < 100: break
print("pages", p, "n", len(allr))
from collections import Counter
print(Counter(x["stockEndType"] for x in allr))
print([ (x["itemCode"], x["stockName"], x.get("marketValue")) for x in allr if x["stockEndType"]=="stock"][-3:])
print(sum(1 for x in allr if x["stockEndType"]=="stock" and x["itemCode"].endswith("0")))
