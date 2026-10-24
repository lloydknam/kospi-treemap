"""KOSPI 전종목 시총 트리맵 영상 (1:1, 면적=시총, 색=등락률 파스텔, 아래 코스피 지수 차트)
사용: python render.py data.csv out.mp4 --index data/kospi_index.csv [--abs] [--top 0] [--sub 2]
--top 0 : 전종목(기본). 숫자면 마지막 시점 시총 상위 N개만.
--abs   : 면적=시총 절대값 (전체 크기가 시총에 따라 변함, 점선=기간 중 최대)
"""
import argparse, subprocess
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
ap.add_argument("--note", default="")
a = ap.parse_args()

for f in ["Noto Sans CJK KR", "NanumGothic", "Malgun Gothic", "AppleGothic", "Noto Sans CJK JP"]:
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

ix = pd.read_csv(a.index, parse_dates=["date"]).set_index("date")["close"].sort_index()
ixv = ix.reindex(pd.DatetimeIndex(dates), method="ffill").values
xn = mdates.date2num(pd.DatetimeIndex(dates).to_pydatetime())

PX = 1000
TM = [0.01, 0.285, 0.98, 0.575]
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
    return pos, d["chg"].to_dict(), vals.sum()

L = [layout(d) for d in dates]

BG, INK, SOFT = "#fbfbfe", "#2f3347", "#7a7f96"
cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
    "pastel", ["#7fb8ff", "#b9d8ff", "#f6f4fa", "#ffc6cf", "#ff8fa3"])

def tw(s):  # 글자 폭 추정(전각=1, 반각=0.58)
    return sum(1.0 if ord(c) > 127 else 0.58 for c in s)

ff = subprocess.Popen(
    ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
     "-s", f"{PX}x{PX}", "-r", str(a.fps), "-i", "-", "-c:v", "libx264",
     "-pix_fmt", "yuv420p", a.out], stdin=subprocess.PIPE)

fig = plt.figure(figsize=(PX / 100, PX / 100), dpi=100, facecolor=BG)
ax = fig.add_axes(TM)
cx = fig.add_axes([0.075, 0.07, 0.89, 0.165], facecolor=BG)
date_t = fig.text(0.025, 0.925, "", color=INK, fontsize=42, weight="bold", va="center")
head_t = fig.text(0.975, 0.955, "KOSPI 시가총액 지도", color=INK, fontsize=17, weight="bold", ha="right", va="center")
sub1 = fig.text(0.975, 0.918, "", color=SOFT, fontsize=10.5, ha="right", va="center")
sub2 = fig.text(0.975, 0.888, "", color=SOFT, fontsize=10.5, ha="right", va="center")
fig.text(0.975, 0.012, "출처: 네이버 증권(종목·시가총액), Yahoo Finance(종가·KOSPI 지수) · 시총은 종가×주식수 근사치",
         color="#a3a8bd", fontsize=8.5, ha="right", va="bottom")
if a.note:
    fig.text(0.5, 0.55, a.note, color=INK, alpha=0.12, fontsize=70, ha="center", va="center", rotation=20, weight="bold", zorder=10)

ymin, ymax = np.nanmin(ixv), np.nanmax(ixv)
pad = (ymax - ymin) * 0.12

def chart(f, i, j, tot):
    cx.clear(); cx.set_facecolor(BG)
    cx.set_xlim(xn[0], xn[-1]); cx.set_ylim(ymin - pad, ymax + pad * 2.6)
    cx.plot(xn, ixv, color="#d5d8e6", lw=2.2, solid_capstyle="round")
    k = i + 1
    px = list(xn[:k]) + [xn[i] * (1 - f) + xn[j] * f]
    py = list(ixv[:k]) + [ixv[i] * (1 - f) + ixv[j] * f]
    cx.fill_between(px, py, ymin - pad, color="#ffc6cf", alpha=0.35, lw=0)
    cx.plot(px, py, color="#ff8fa3", lw=2.6, solid_capstyle="round")
    cx.plot([px[-1]], [py[-1]], "o", ms=9, color="white", mec="#ff6f8a", mew=2.6, zorder=5)
    cx.text(0.005, 0.97, "KOSPI 지수", transform=cx.transAxes, color=SOFT, fontsize=14, va="top")
    cx.text(0.175, 0.99, f"{py[-1]:,.0f}", transform=cx.transAxes, color=INK, fontsize=23, weight="bold", va="top")
    cx.text(0.345, 0.97, "시총", transform=cx.transAxes, color=SOFT, fontsize=14, va="top")
    cx.text(0.405, 0.99, f"{tot:,.0f}조원", transform=cx.transAxes, color="#e0526d", fontsize=23, weight="bold", va="top")
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

def label(k, x, y, w, h, c):
    nm = names.get(k, k)
    wp, hp = w * UPX, h * UPX
    if wp < 22 or hp < 12: return
    tn = max(tw(nm), 3.8)
    fw = wp * 0.9 / (tn * 1.39)
    fs2 = min(fw, hp * 0.82 / (2 * 1.39 * 1.2), 30)
    if fs2 >= 6.3:
        ax.text(x + w / 2, y + h / 2, f"{nm}\n{c:+.1f}%", color=INK, ha="center", va="center",
                fontsize=fs2, linespacing=1.15)
        return
    fs1 = min(fw, hp * 0.8 / 1.39, 30)
    if fs1 >= 5.5:
        ax.text(x + w / 2, y + h / 2, nm, color=INK, ha="center", va="center", fontsize=fs1)

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
            rects.append(Rectangle((x, y), w, h)); cs.append(c); geo.append((k, x, y, w, h, c))
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
