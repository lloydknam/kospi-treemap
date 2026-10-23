"""KOSPI 시총 트리맵 영상 (1:1, 면적=시총, 색=등락률 파스텔, 아래 코스피 지수 차트)
사용: python render.py data.csv out.mp4 --index data/kospi_index.csv [--abs] [--top 60] [--sub 7]
weekly: 매주 마지막 거래일(보통 금요일) 종가만 사용, 색=주간 등락률
--abs : 면적=시총 절대값 (전체 크기가 시총에 따라 변함, 점선=기간 중 최대)
"""
import argparse, subprocess
import numpy as np, pandas as pd, squarify
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle

ap = argparse.ArgumentParser()
ap.add_argument("csv"); ap.add_argument("out")
ap.add_argument("--index", default="data/kospi_index.csv")
ap.add_argument("--top", type=int, default=60)
ap.add_argument("--freq", default="weekly", choices=["weekly", "daily"])
ap.add_argument("--sub", type=int, default=7, help="구간당 보간 프레임 (작을수록 빠름)")
ap.add_argument("--fps", type=int, default=24)
ap.add_argument("--abs", action="store_true")
ap.add_argument("--note", default="")
a = ap.parse_args()

for f in ["Noto Sans CJK KR", "NanumGothic", "Malgun Gothic", "AppleGothic", "Noto Sans CJK JP"]:
    if any(f == x.name for x in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = f; break
plt.rcParams["axes.unicode_minus"] = False

df = pd.read_csv(a.csv, parse_dates=["date"], dtype={"ticker": str}).sort_values(["ticker", "date"])
if a.freq == "weekly":
    keep = df.groupby(df["date"].dt.to_period("W"))["date"].max().values
    df = df[df["date"].isin(keep)].copy()
    df["chg"] = df.groupby("ticker")["close"].pct_change() * 100
df["chg"] = df["chg"].fillna(0.0)
dates = sorted(df["date"].unique())
N = len(dates)
topn = df[df.date == dates[-1]].nlargest(a.top, "mcap")["ticker"].tolist()
names = df.drop_duplicates("ticker").set_index("ticker")["name"].to_dict()
unit = "주간" if a.freq == "weekly" else "전일대비"
lim = 8.0 if a.freq == "weekly" else 3.0

# ---- 코스피 지수
ix = pd.read_csv(a.index, parse_dates=["date"]).set_index("date")["close"].sort_index()
ixv = ix.reindex(pd.DatetimeIndex(dates), method="ffill").values
xn = mdates.date2num(pd.DatetimeIndex(dates).to_pydatetime())

# ---- 1:1 캔버스 (1000x1000), 트리맵 영역 픽셀 비율에 맞춰 좌표계 설정
PX = 1000
TM = [0.01, 0.285, 0.98, 0.575]
W = 100.0
H = W * (TM[3] * PX) / (TM[2] * PX)

tot_by = df[df.ticker.isin(topn)].groupby("date")["mcap"].sum()
REF = tot_by.max()

def layout(day):
    d = df[df.date == day].set_index("ticker")
    sel = d.loc[d.index.intersection(topn)]
    vals = sel["mcap"].astype(float).sort_values(ascending=False)
    k = (vals.sum() / REF) ** 0.5 if a.abs else 1.0
    w_, h_ = W * k, H * k
    sizes = squarify.normalize_sizes(vals.values, w_, h_)
    rects = squarify.squarify(sizes, 0, H - h_, w_, h_)
    pos = {t: (r["x"], r["y"], r["dx"], r["dy"]) for t, r in zip(vals.index, rects)}
    return pos, sel["chg"].to_dict(), vals.sum()

L = [layout(d) for d in dates]

BG, INK, SOFT = "#fbfbfe", "#2f3347", "#7a7f96"
cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
    "pastel", ["#7fb8ff", "#b9d8ff", "#f6f4fa", "#ffc6cf", "#ff8fa3"])
def col(v): return cmap((np.clip(v, -lim, lim) + lim) / (2 * lim))

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
if a.note:
    fig.text(0.5, 0.55, a.note, color=INK, alpha=0.12, fontsize=70, ha="center", va="center", rotation=20, weight="bold", zorder=10)

ymin, ymax = np.nanmin(ixv), np.nanmax(ixv)
pad = (ymax - ymin) * 0.12

def chart(f, i, j):
    cx.clear()
    cx.set_facecolor(BG)
    cx.set_xlim(xn[0], xn[-1]); cx.set_ylim(ymin - pad, ymax + pad)
    cx.plot(xn, ixv, color="#d5d8e6", lw=2.2, solid_capstyle="round")
    k = i + 1
    px = list(xn[:k]) + [xn[i] * (1 - f) + xn[j] * f]
    py = list(ixv[:k]) + [ixv[i] * (1 - f) + ixv[j] * f]
    cx.fill_between(px, py, ymin - pad, color="#ffc6cf", alpha=0.35, lw=0)
    cx.plot(px, py, color="#ff8fa3", lw=2.6, solid_capstyle="round")
    cx.plot([px[-1]], [py[-1]], "o", ms=9, color="white", mec="#ff6f8a", mew=2.6, zorder=5)
    cx.text(0.01, 0.95, "KOSPI 지수", transform=cx.transAxes, color=SOFT, fontsize=10.5, va="top")
    cx.text(0.115, 0.97, f"{py[-1]:,.0f}", transform=cx.transAxes, color=INK, fontsize=16, weight="bold", va="top")
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

steps = max(N - 1, 1)
for i in range(steps):
    j = min(i + 1, N - 1)
    last = (i == steps - 1)
    for s in range(a.sub + (a.fps if last else 0)):
        f = min(s / a.sub, 1.0)
        ax.clear(); ax.axis("off"); ax.set_xlim(0, W); ax.set_ylim(H, 0)
        if a.abs:
            ax.add_patch(Rectangle((0, 0), W, H, fill=False, ec="#c9cde0", lw=1.5, ls="--"))
        for k in set(L[i][0]) | set(L[j][0]):
            p0 = L[i][0].get(k, L[j][0].get(k)); p1 = L[j][0].get(k, p0)
            x, y, w, h = [p0[n] * (1 - f) + p1[n] * f for n in range(4)]
            c = L[i][1].get(k, 0) * (1 - f) + L[j][1].get(k, 0) * f
            ax.add_patch(Rectangle((x, y), w, h, fc=col(c), ec=BG, lw=2.0))
            if w > 4.5 and h > 3.5:
                fs = max(5.5, min(22, (w * h) ** 0.5 * 1.1)) * 0.6
                ax.text(x + w / 2, y + h / 2, f"{names.get(k, k)}\n{c:+.1f}%",
                        color=INK, ha="center", va="center", fontsize=fs)
        dcur = pd.Timestamp(dates[j] if f >= 0.5 else dates[i])
        date_t.set_text(f"{dcur:%Y.%m.%d}")
        tot = (L[i][2] * (1 - f) + L[j][2] * f) / 1e12
        sub1.set_text((f"면적=시총 절대값 (점선=최대 {REF/1e12:,.0f}조원)" if a.abs else "면적=시총 비중")
                      + f" · 색={unit} 등락률")
        sub2.set_text(f"상위 {len(topn)}개 합계 {tot:,.0f}조원" + (" · 매주 금요일 종가" if a.freq == "weekly" else ""))
        chart(f, i, j)
        fig.canvas.draw()
        ff.stdin.write(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].tobytes())
ff.stdin.close(); ff.wait()
print("done", a.out, N, "points")
