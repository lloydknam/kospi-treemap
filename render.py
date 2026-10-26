"""KOSPI 전종목 시총 트리맵 영상 (1:1, 면적=시총, 색=등락률 파스텔, 아래 코스피 지수 차트)
사용: python render.py data.csv out.mp4 --index data/kospi_index.csv [--abs] [--top 0] [--sub 2]
--top 0 : 전종목(기본). 숫자면 마지막 시점 시총 상위 N개만.
--abs   : 면적=시총 절대값 (전체 크기가 시총에 따라 변함, 점선=기간 중 최대)
"""
import argparse, subprocess, os
import numpy as np, pandas as pd, squarify
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection

ap = argparse.ArgumentParser()
ap.add_argument("csv"); ap.add_argument("out")
ap.add_argument("--index", default="data/kospi_index.csv")
ap.add_argument("--top", type=int, default=0)
ap.add_argument("--freq", default="daily", choices=["weekly", "daily"])
ap.add_argument("--start", default="2025-01-01")
ap.add_argument("--sub", type=int, default=2, help="구간당 보간 프레임 (작을수록 빠름)")
ap.add_argument("--fps", type=int, default=24)
ap.add_argument("--abs", action="store_true")
ap.add_argument("--credit", default="Lloyd's Balcony Lab\nwith claude · GitHub(@lloydknam)")
ap.add_argument("--credit-logo", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "brand", "lockup-light.png"),
                help="크레딧 로고 PNG(있으면 글자 대신 로고를 넣음)")
ap.add_argument("--note", default="")
a = ap.parse_args()

import glob, os
for fp in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "*.otf")):
    fm.fontManager.addfont(fp)                      # Pretendard (OFL)
for f in ["Pretendard", "Noto Sans CJK KR", "NanumGothic", "Malgun Gothic", "AppleGothic", "Noto Sans CJK JP"]:
    if any(f == x.name for x in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = f; break
plt.rcParams["axes.unicode_minus"] = False

df = pd.read_csv(a.csv, parse_dates=["date"], dtype={"ticker": str}).sort_values(["ticker", "date"])
df = df[df["date"] >= a.start]
if a.freq == "weekly":
    keep = df.groupby(df["date"].dt.to_period("W"))["date"].max().values
    df = df[df["date"].isin(keep)].copy()
    df["chg"] = df.groupby("ticker")["close"].pct_change() * 100
df["chg"] = df["chg"].fillna(0.0)
dates = sorted(df["date"].unique())
N = len(dates)
last = df[df.date == dates[-1]]
topn = (last.nlargest(a.top, "mcap") if a.top else last)["ticker"].tolist()
df = df[df.ticker.isin(topn)]
names = df.drop_duplicates("ticker").set_index("ticker")["name"].to_dict()
unit = "주간" if a.freq == "weekly" else "전일대비"
lim = 8.0 if a.freq == "weekly" else 3.0

ix = pd.read_csv(a.index, parse_dates=["date"]).set_index("date")["close"].sort_index().dropna()
ixv = ix.reindex(pd.DatetimeIndex(dates), method="ffill").values
xn = mdates.date2num(pd.DatetimeIndex(dates).to_pydatetime())

PX = 1000
TM = [0.04, 0.285, 0.92, 0.575]
W = 100.0
H = W * (TM[3] * PX) / (TM[2] * PX)
UPX = TM[2] * PX / W            # 좌표 1단위 = 픽셀

tot_by = df.groupby("date")["mcap"].sum()
REF = tot_by.max()

def layout(day):
    d = df[df.date == day].set_index("ticker")
    vals = d["mcap"].astype(float).sort_values(ascending=False)
    k = (vals.sum() / REF) ** 0.5 if a.abs else 1.0
    w_, h_ = W * k, H * k
    sizes = squarify.normalize_sizes(vals.values, w_, h_)
    rects = squarify.squarify(sizes, (W - w_) / 2, (H - h_) / 2, w_, h_)   # 가운데 정렬
    pos = {t: (r["x"], r["y"], r["dx"], r["dy"]) for t, r in zip(vals.index, rects)}
    return pos, d["chg"].to_dict(), vals.sum(), (vals / 1e12).to_dict()

L = [layout(d) for d in dates]

BG, INK, SOFT, HEAD = "#ffffff", "#2f3347", "#7a7f96", "#2f3347"   # 흰 배경, 칸 사이 틈=흰색
cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
    "pastel", ["#7fb8ff", "#b9d8ff", "#f6f4fa", "#ffc6cf", "#ff8fa3"])

def tw(s):  # 글자 폭 추정(전각=1, 반각=0.58)
    return sum(1.0 if ord(c) > 127 else 0.58 for c in s)

ff = subprocess.Popen(
    ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
     "-s", f"{PX}x{PX}", "-r", str(a.fps), "-i", "-", "-c:v", "libx264",
     "-pix_fmt", "yuv420p", a.out], stdin=subprocess.PIPE)

def make_bg():
    """흰 배경 + 얇은 청록 그라데이션 테두리"""
    from PIL import Image, ImageDraw
    yy, xx = np.mgrid[0:PX, 0:PX]
    t = xx / PX * 0.25 + yy / PX * 0.75
    def lerp(t, stops):
        out = np.zeros(t.shape + (3,))
        for (p, ca), (q, cb) in zip(stops[:-1], stops[1:]):
            m = (t >= p) & (t <= q); u = ((t - p) / (q - p))[m][:, None]
            out[m] = np.array(ca) * (1 - u) + np.array(cb) * u
        return out
    base = np.full((PX, PX, 3), 255.0)   # 흰 배경
    bd = lerp(xx / PX * 0.45 + yy / PX * 0.55, [(0, (60, 208, 180)), (0.5, (21, 151, 127)), (1.0, (8, 92, 82))])   # 청록 그라데이션
    S, inset, th, rad = 4, 14, 4, 26
    mk = Image.new("L", (PX * S, PX * S), 0)
    ImageDraw.Draw(mk).rounded_rectangle([inset * S, inset * S, (PX - inset) * S - 1, (PX - inset) * S - 1],
                                         radius=rad * S, outline=255, width=th * S)
    mk = np.asarray(mk.resize((PX, PX), Image.LANCZOS), dtype=float)[:, :, None] / 255
    return (base * (1 - mk) + bd * mk).astype("uint8")

fig = plt.figure(figsize=(PX / 100, PX / 100), dpi=100, facecolor=BG)
fig.figimage(make_bg(), 0, 0, zorder=-10)
ax = fig.add_axes(TM)
cx = fig.add_axes([0.095, 0.095, 0.83, 0.15], facecolor="none")
date_t = fig.text(0.05, 0.925, "", color=HEAD, fontsize=30, weight="bold", va="center")
head_t = fig.text(0.95, 0.955, "KOSPI 시가총액 지도", color=HEAD, fontsize=17, weight="semibold", ha="right", va="center")
sub1 = fig.text(0.95, 0.918, "", color=SOFT, fontsize=10.5, ha="right", va="center")
sub2 = fig.text(0.95, 0.888, "", color=SOFT, fontsize=10.5, ha="right", va="center")
fig.text(0.95, 0.024, "출처: 네이버 증권(종목·시가총액), Yahoo Finance(종가·KOSPI 지수) · 시총은 종가×주식수 근사치",
         color="#a3a8bd", fontsize=8.5, ha="right", va="bottom")
if a.credit_logo and os.path.exists(a.credit_logo):
    from PIL import Image as _Im
    _lg = _Im.open(a.credit_logo).convert("RGBA")
    _h = int(PX * 0.042)                                   # 크레딧 로고 높이(px)
    _lg = _lg.resize((int(_lg.width * _h / _lg.height), _h), _Im.LANCZOS)
    fig.figimage(np.asarray(_lg).astype(float) / 255, int(PX * 0.05), int(PX * 0.024), zorder=5)
elif a.credit:
    fig.text(0.05, 0.024, a.credit, color="#4f8f84", fontsize=8.8, ha="left", va="bottom", fontweight="medium", linespacing=1.3)
if a.note:
    fig.text(0.5, 0.55, a.note, color=INK, alpha=0.12, fontsize=70, ha="center", va="center", rotation=20, weight="bold", zorder=10)

ymin, ymax = np.nanmin(ixv), np.nanmax(ixv)
pad = (ymax - ymin) * 0.12

def chart(f, i, j, tot):
    cx.clear(); cx.set_facecolor("none")
    cx.set_xlim(xn[0], xn[-1]); cx.set_ylim(ymin - pad, ymax + pad * 4.2)
    cx.plot(xn, ixv, color="#d5d8e6", lw=2.2, solid_capstyle="round")
    k = i + 1
    px = list(xn[:k]) + [xn[i] * (1 - f) + xn[j] * f]
    py = list(ixv[:k]) + [ixv[i] * (1 - f) + ixv[j] * f]
    cx.fill_between(px, py, ymin - pad, color="#3cd0b4", alpha=0.18, lw=0)
    cx.plot(px, py, color="#17a58b", lw=2.6, solid_capstyle="round")
    cx.plot([px[-1]], [py[-1]], "o", ms=9, color="white", mec="#0f8a74", mew=2.6, zorder=5)
    cx.text(0.005, 0.97, "KOSPI 지수", transform=cx.transAxes, color=SOFT, fontsize=14, va="top")
    cx.text(0.185, 1.0, f"{py[-1]:,.0f}", transform=cx.transAxes, color=HEAD, fontsize=32, weight="bold", va="top")
    cx.text(0.43, 0.96, "시총", transform=cx.transAxes, color=SOFT, fontsize=15, va="top")
    cx.text(0.495, 1.0, f"{tot:,.0f}조원", transform=cx.transAxes, color="#0f8a74", fontsize=32, weight="bold", va="top")
    cx.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 4, 7, 10)))
    cx.xaxis.set_major_formatter(mdates.DateFormatter("%Y.%m"))
    cx.xaxis.set_minor_locator(mdates.MonthLocator())
    cx.tick_params(axis="x", which="major", length=6, color="#9aa0b8", labelsize=9, labelcolor=SOFT)
    cx.tick_params(axis="x", which="minor", length=3, color="#c9cde0")
    cx.tick_params(axis="y", length=0, labelsize=8.5, labelcolor=SOFT)
    cx.yaxis.tick_right()
    cx.grid(axis="y", color="#eceef6", lw=1)
    for sp in ["top", "left", "right"]: cx.spines[sp].set_visible(False)
    cx.spines["bottom"].set_color("#c9cde0")

def fmt_cap(v):  # 조원 단위
    if v >= 10: return f"{v:,.0f}조"
    if v >= 1: return f"{v:.1f}조"
    return f"{v:.2f}조"

def label(k, x, y, w, h, m):
    nm = names.get(k, k)
    wp, hp = w * UPX, h * UPX
    if wp < 22 or hp < 12: return
    tn = max(tw(nm), 4.6)
    fw = wp * 0.9 / (tn * 1.39)
    fs2 = min(fw, hp * 0.82 / (2 * 1.39 * 1.2), 30)
    if fs2 >= 6.3:
        ax.text(x + w / 2, y + h / 2, f"{nm}\n{fmt_cap(m)}", color=INK, ha="center", va="center",
                fontsize=fs2, linespacing=1.18, fontweight="medium")
        return
    fs1 = min(fw, hp * 0.8 / 1.39, 30)
    if fs1 >= 5.5:
        ax.text(x + w / 2, y + h / 2, nm, color=INK, ha="center", va="center", fontsize=fs1, fontweight="medium")

steps = max(N - 1, 1)
for i in range(steps):
    j = min(i + 1, N - 1)
    lastseg = (i == steps - 1)
    for s in range(a.sub + (a.fps if lastseg else 0)):
        f = min(s / a.sub, 1.0)
        ax.clear(); ax.axis("off"); ax.set_xlim(0, W); ax.set_ylim(H, 0)
        if a.abs:
            ax.add_patch(Rectangle((0, 0), W, H, fill=False, ec="#c9cde0", lw=1.5, ls="--"))
        keys = list(set(L[i][0]) | set(L[j][0]))
        rects, cs, geo = [], [], []
        for k in keys:
            p0 = L[i][0].get(k, L[j][0].get(k)); p1 = L[j][0].get(k, p0)
            x, y, w, h = [p0[n] * (1 - f) + p1[n] * f for n in range(4)]
            c = L[i][1].get(k, 0) * (1 - f) + L[j][1].get(k, 0) * f
            m0 = L[i][3].get(k); m1 = L[j][3].get(k)
            m = (m0 if m1 is None else m1) if (m0 is None or m1 is None) else m0 * (1 - f) + m1 * f
            rects.append(Rectangle((x, y), w, h)); cs.append(c); geo.append((k, x, y, w, h, m))
        fc = cmap((np.clip(cs, -lim, lim) + lim) / (2 * lim))
        ax.add_collection(PatchCollection(rects, facecolors=fc, edgecolors=BG, linewidths=1.0))
        for g in geo: label(*g)
        dcur = pd.Timestamp(dates[j] if f >= 0.5 else dates[i])
        date_t.set_text(f"{dcur:%Y.%m.%d}")
        tot = (L[i][2] * (1 - f) + L[j][2] * f) / 1e12
        sub1.set_text((f"면적=시총 절대값 (점선=최대 {REF/1e12:,.0f}조원)" if a.abs else "면적=시총 비중")
                      + f" · 색={unit} 등락률")
        sub2.set_text(f"{'전체' if not a.top else '상위 ' + str(a.top) + '개'} {len(topn)}종목 합계 {tot:,.0f}조원"
                      + (" · 매주 금요일 종가" if a.freq == "weekly" else ""))
        chart(f, i, j, tot)
        fig.canvas.draw()
        ff.stdin.write(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].tobytes())
ff.stdin.close(); ff.wait()
print("done", a.out, N, "points", len(topn), "tickers")
