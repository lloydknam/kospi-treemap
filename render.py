"""KOSPI 시총 트리맵 영상 (면적=시총, 색=등락률, 상승=빨강/하락=파랑, 파스텔)
사용: python render.py data.csv out.mp4 [--top 60] [--freq weekly|daily] [--sub 10]
weekly: 매주 마지막 거래일(보통 금요일) 종가만 사용, 색=주간 등락률
"""
import argparse, subprocess
import numpy as np, pandas as pd, squarify
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle

ap = argparse.ArgumentParser()
ap.add_argument("csv"); ap.add_argument("out")
ap.add_argument("--top", type=int, default=60)
ap.add_argument("--freq", default="weekly", choices=["weekly", "daily"])
ap.add_argument("--sub", type=int, default=10, help="구간당 보간 프레임")
ap.add_argument("--fps", type=int, default=24)
ap.add_argument("--note", default="")
a = ap.parse_args()

for f in ["Noto Sans CJK KR", "NanumGothic", "Malgun Gothic", "AppleGothic", "Noto Sans CJK JP"]:
    if any(f == x.name for x in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = f; break
plt.rcParams["axes.unicode_minus"] = False

df = pd.read_csv(a.csv, parse_dates=["date"], dtype={"ticker": str}).sort_values(["ticker", "date"])
if a.freq == "weekly":
    keep = df.groupby(df["date"].dt.to_period("W"))["date"].max().values  # 주 마지막 거래일
    df = df[df["date"].isin(keep)].copy()
    df["chg"] = df.groupby("ticker")["close"].pct_change() * 100
df["chg"] = df["chg"].fillna(0.0)
dates = sorted(df["date"].unique())
N = len(dates)
topn = df[df.date == dates[-1]].nlargest(a.top, "mcap")["ticker"].tolist()
names = df.drop_duplicates("ticker").set_index("ticker")["name"].to_dict()
W, H = 100.0, 56.25
unit = "주간" if a.freq == "weekly" else "전일대비"
lim = 8.0 if a.freq == "weekly" else 3.0

def layout(day):
    d = df[df.date == day].set_index("ticker")
    sel = d.loc[d.index.intersection(topn)]
    vals = sel["mcap"].astype(float).sort_values(ascending=False)
    sizes = squarify.normalize_sizes(vals.values, W, H)
    rects = squarify.squarify(sizes, 0, 0, W, H)
    pos = {t: (r["x"], r["y"], r["dx"], r["dy"]) for t, r in zip(vals.index, rects)}
    return pos, sel["chg"].to_dict(), vals.sum()

L = [layout(d) for d in dates]

BG, INK, SOFT = "#fbfbfe", "#2f3347", "#7a7f96"
cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
    "pastel", ["#7fb8ff", "#b9d8ff", "#f6f4fa", "#ffc6cf", "#ff8fa3"])
def col(v): return cmap((np.clip(v, -lim, lim) + lim) / (2 * lim))

ff = subprocess.Popen(
    ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
     "-s", "1280x720", "-r", str(a.fps), "-i", "-", "-c:v", "libx264",
     "-pix_fmt", "yuv420p", a.out], stdin=subprocess.PIPE)

fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor=BG)
ax = fig.add_axes([0.01, 0.105, 0.98, 0.77])
rl = fig.add_axes([0.03, 0.02, 0.94, 0.06])
date_t = fig.text(0.02, 0.93, "", color=INK, fontsize=44, weight="bold", va="center")   # 큰 날짜
head_t = fig.text(0.98, 0.95, "KOSPI 시가총액 지도", color=INK, fontsize=18, weight="bold", ha="right", va="center")
sub_t = fig.text(0.98, 0.905, "", color=SOFT, fontsize=11.5, ha="right", va="center")
if a.note:
    fig.text(0.5, 0.5, a.note, color=INK, alpha=0.12, fontsize=70, ha="center", va="center", rotation=20, weight="bold", zorder=10)

d0, d1 = pd.Timestamp(dates[0]), pd.Timestamp(dates[-1])

def ruler(pct):
    rl.clear(); rl.set_xlim(-1, 101); rl.set_ylim(0, 1); rl.axis("off")
    rl.plot([0, 100], [0.62, 0.62], color="#d5d8e6", lw=6, solid_capstyle="round")
    rl.plot([0, pct], [0.62, 0.62], color="#ff8fa3", lw=6, solid_capstyle="round")
    for t in range(0, 101, 10):
        rl.plot([t, t], [0.50, 0.74], color="#9aa0b8", lw=1.2)
        rl.text(t, 0.28, str(t), color=SOFT, fontsize=10, ha="center", va="center")
    rl.plot([pct], [0.62], "o", ms=13, color="white", mec="#ff6f8a", mew=3, zorder=5)
    rl.text(0, 0.02, f"{d0:%Y-%m-%d}", color=SOFT, fontsize=9, ha="left", va="center")
    rl.text(100, 0.02, f"{d1:%Y-%m-%d}", color=SOFT, fontsize=9, ha="right", va="center")

steps = max(N - 1, 1)
for i in range(steps):
    j = min(i + 1, N - 1)
    last = (i == steps - 1)
    for s in range(a.sub + (a.fps if last else 0)):      # 마지막엔 1초 정지
        f = min(s / a.sub, 1.0)
        ax.clear(); ax.axis("off"); ax.set_xlim(0, W); ax.set_ylim(H, 0)
        for k in set(L[i][0]) | set(L[j][0]):
            p0 = L[i][0].get(k, L[j][0].get(k)); p1 = L[j][0].get(k, p0)
            x, y, w, h = [p0[n] * (1 - f) + p1[n] * f for n in range(4)]
            c = L[i][1].get(k, 0) * (1 - f) + L[j][1].get(k, 0) * f
            ax.add_patch(Rectangle((x, y), w, h, fc=col(c), ec=BG, lw=2.2))
            if w > 4 and h > 3:
                fs = max(6, min(22, (w * h) ** 0.5 * 1.1)) * 0.7
                ax.text(x + w / 2, y + h / 2, f"{names.get(k, k)}\n{c:+.1f}%",
                        color=INK, ha="center", va="center", fontsize=fs)
        dcur = pd.Timestamp(dates[j] if f >= 0.5 else dates[i])
        date_t.set_text(f"{dcur:%Y.%m.%d}")
        tot = (L[i][2] * (1 - f) + L[j][2] * f) / 1e12
        sub_t.set_text(f"면적=시총 · 색={unit} 등락률 · 상위 {len(topn)}개 {tot:,.0f}조원"
                       + (" · 매주 금요일 종가" if a.freq == "weekly" else ""))
        ruler((i + f) / steps * 100)
        fig.canvas.draw()
        ff.stdin.write(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].tobytes())
ff.stdin.close(); ff.wait()
print("done", a.out, N, "points")
