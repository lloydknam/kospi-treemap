"""KOSPI 상위 종목 일별 시총 -> data/kospi_mcap.csv
종목: 대형주 고정 유니버스(코드 직접 관리), 종가: Yahoo, 시총 = 종가 x (일별 발행주식수, Yahoo)
(KRX 직접 수집은 해외 IP에서 막혀 우회. 시총은 보통주 기준 근사치)
"""
import re, sys, time, warnings
import pandas as pd, requests, yfinance as yf
warnings.filterwarnings("ignore")
START, TOPN = "2024-01-01", 200
H = {"User-Agent": "Mozilla/5.0"}

UNIVERSE = """005930 삼성전자|000660 SK하이닉스|373220 LG에너지솔루션|207940 삼성바이오로직스|005380 현대차|000270 기아|068270 셀트리온|105560 KB금융|005490 POSCO홀딩스|035420 NAVER|055550 신한지주|012450 한화에어로스페이스|329180 HD현대중공업|034020 두산에너빌리티|035720 카카오|051910 LG화학|028260 삼성물산|012330 현대모비스|086790 하나금융지주|096770 SK이노베이션|042660 한화오션|009540 HD한국조선해양|011200 HMM|066570 LG전자|003550 LG|034730 SK|017670 SK텔레콤|030200 KT|015760 한국전력|032830 삼성생명|316140 우리금융지주|000810 삼성화재|010130 고려아연|003670 포스코퓨처엠|006400 삼성SDI|009150 삼성전기|018260 삼성SDS|011070 LG이노텍|010140 삼성중공업|267260 HD현대일렉트릭|064350 현대로템|047050 포스코인터내셔널|033780 KT&G|138040 메리츠금융지주|024110 기업은행|259960 크래프톤|352820 하이브|090430 아모레퍼시픽|097950 CJ제일제당|011170 롯데케미칼|010950 S-Oil|036570 엔씨소프트|251270 넷마블|000720 현대건설|028050 삼성E&A|003490 대한항공|323410 카카오뱅크|377300 카카오페이|402340 SK스퀘어|000100 유한양행|128940 한미약품|302440 SK바이오사이언스|326030 SK바이오팜|004020 현대제철|005830 DB손해보험|088350 한화생명|071050 한국금융지주|006800 미래에셋증권|016360 삼성증권|039490 키움증권|029780 삼성카드|078930 GS|004170 신세계|023530 롯데쇼핑|139480 이마트|069960 현대백화점|007070 GS리테일|271560 오리온|003230 삼양식품|161390 한국타이어앤테크놀로지|204320 HL만도|000880 한화|000150 두산|241560 두산밥캣|267250 HD현대|010620 HD현대미포|034220 LG디스플레이|006260 LS|298040 효성중공업|267270 HD건설기계|454910 두산로보틱스|079550 LIG넥스원|047810 한국항공우주|272210 한화시스템|120110 코오롱인더|004990 롯데지주|180640 한진칼|021240 코웨이|051900 LG생활건강|008770 호텔신라|032640 LG유플러스|086280 현대글로비스|011790 SKC|009830 한화솔루션"""
names = {x.split(" ", 1)[0]: x.split(" ", 1)[1] for x in UNIVERSE.split("|")}
codes = list(names)
print("tickers", len(codes), codes[:5], [names[c] for c in codes[:5]])
if len(codes) < 30: sys.exit("ticker list failed")

rows = []
for i, c in enumerate(codes):
    try:
        t = yf.Ticker(c + ".KS")
        h = t.history(start=START, auto_adjust=False)
        sh = t.get_shares_full(start=START)
        if h.empty: print(c, names[c], "no price"); continue
        if sh is None or len(sh) == 0:
            n = t.info.get("sharesOutstanding") or getattr(t.fast_info, "shares", None)
            if not n: print(c, names[c], "no shares"); continue
            sh = pd.Series([n], index=[h.index[0]])
            print(c, names[c], "const shares", n)
        h.index = h.index.tz_localize(None).normalize()
        sh.index = pd.DatetimeIndex(sh.index).tz_localize(None).normalize()
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
import os; os.makedirs("data", exist_ok=True)
ixh = yf.Ticker("^KS11").history(start=START)
ixh.index = ixh.index.tz_localize(None).normalize(); ixh.index.name = "date"
import os; os.makedirs("data", exist_ok=True)
ixh[["Close"]].rename(columns={"Close": "close"}).reset_index().to_csv("data/kospi_index.csv", index=False)
print("index rows", len(ixh))
out = pd.concat(rows, ignore_index=True).dropna(subset=["mcap"])
out = out[out["date"] >= "2024-01-02"]
out.to_csv("data/kospi_mcap.csv", index=False, encoding="utf-8-sig")
print("saved", len(out), "rows", out["date"].nunique(), "days")
