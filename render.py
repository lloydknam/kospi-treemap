"""KOSPI 시총 트리맵 영상 (면적=시총, 색=등락률, 상승=빨강/하락=파랑)
사용: python render.py kospi_mcap.csv out.mp4 [--top 60] [--color daily|ytd] [--sub 4]
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
ap.add_argument("--color", default="daily", choices=["daily", "ytd"])
ap.add_argument("--sub", type=int, default=4, help="하루당 보간 프레임")
ap.add_argument("--fps", type=int, default=24)
ap.add_argument("--note", default="")
a = ap.parse_args()

for f in ["Noto Sans CJK KR", "NanumGothic", "Malgun Gothic", "AppleGothic", "Noto Sans CJK JP"]:
    if any(f == x.name for x in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = f; break
plt.rcParams["axes.unicode_minus"] = False

df = pd.read_csv(a.csv, parse_dates=["date"])
dates = sorted(df["date"].unique())
first = df[df.date == dates[0]].set_index("ticker")["close"]
topn = df[df.date == dates[-1]].nlargest(a.top, "mcap")["ticker"].tolist()
W, H = 100.0, 56.25

def layout(day):
    d = df[df.date == day].set_index("ticker")
    sel = d.loc[d.index.intersection(topn)].copy()
    vals = sel["mcap"].astype(float)
    vals = vals.sort_values(ascending=False)
    sizes = squarify.normalize_sizes(vals.values, W, H)
    rects = squarify.squarify(sizes, 0, 0, W, H)
    pos = {t: (r["x"], r["y"], r["dx"], r["dy"]) for t, r in zip(vals.index, rects)}
    if a.color == "daily":
        chg = sel["chg"].to_dict()
    else:
        chg = ((sel["close"] / first.reindex(sel.index) - 1) * 100).to_dict()
    return pos, chg, d["mcap"].sum()

names = df.drop_duplicates("ticker").set_index("ticker")["name"].to_dict()
L = [layout(d) for d in dates]

lim = 3.0 if a.color == "daily" else 30.0
cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
    "kr", ["#1f4fd8", "#2a2f45", "#d8302a"])
def col(v): return cmap((np.clip(v, -lim, lim) + lim) / (2 * lim))

ff = subprocess.Popen(
    ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
     "-s", "1280x720", "-r", str(a.fps), "-i", "-", "-c:v", "libx264",
     "-pix_fmt", "yuv420p", a.out], stdin=subprocess.PIPE)

fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor="#12141c")
ax = fig.add_axes([0.01, 0.01, 0.98, 0.88])
title = fig.text(0.015, 0.94, "", color="white", fontsize=20, weight="bold", va="center")
sub = fig.text(0.985, 0.94, "", color="#aab", fontsize=14, ha="right", va="center")
if a.note:
    fig.text(0.5, 0.5, a.note, color="white", alpha=0.15, fontsize=70,
             ha="center", va="center", rotation=20, weight="bold", zorder=10)

for i in range(max(len(dates) - 1, 1)):
    j = min(i + 1, len(dates) - 1)
    for s in range(a.sub):
        f = s / a.sub
        ax.clear(); ax.axis("off"); ax.set_xlim(0, W); ax.set_ylim(H, 0)
        for k in set(L[i][0]) | set(L[j][0]):
            p0 = L[i][0].get(k, L[j][0].get(k)); p1 = L[j][0].get(k, p0)
            x, y, w, h = [p0[n] * (1 - f) + p1[n] * f for n in range(4)]
            c0 = L[i][1].get(k, 0); c1 = L[j][1].get(k, c0)
            c = c0 * (1 - f) + c1 * f
            ax.add_patch(Rectangle((x, y), w, h, fc=col(c), ec="#12141c", lw=1.2))
            if w > 4 and h > 3:
                fs = max(6, min(22, (w * h) ** 0.5 * 1.1))
                ax.text(x + w / 2, y + h / 2, f"{names.get(k, k)}\n{c:+.1f}%",
                        color="white", ha="center", va="center", fontsize=fs * 0.7)
        d = pd.Timestamp(dates[i])
        title.set_text(f"KOSPI 시가총액 지도  {d:%Y-%m-%d}")
        tot = (L[i][2] * (1 - f) + L[j][2] * f) / 1e12
        sub.set_text(f"면적=시총 · 색={'전일대비' if a.color=='daily' else '연초대비'} 등락률 · 상위 {len(topn)}개 합계 {tot:,.0f}조원")
        fig.canvas.draw()
        ff.stdin.write(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].tobytes())
ff.stdin.close(); ff.wait()
print("done", a.out)
