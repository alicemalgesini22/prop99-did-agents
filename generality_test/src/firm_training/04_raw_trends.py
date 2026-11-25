"""Step 4: raw trends. Mean outcome by group over time, vertical line at treatment start.

Run: uv run python src/firm_training/04_raw_trends.py
Writes results/firm_training/raw_trends.png and raw_trends.csv
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import didlib  # noqa: E402

cfg = didlib.load_config()
df = didlib.load_panel(cfg)
start = cfg["treatment_start"]

means = df.groupby(["_time", "_treated"])["_y"].mean().unstack()
means.columns = ["control", "treated"]
means["gap"] = means["treated"] - means["control"]
means.to_csv(didlib.RESULTS / "raw_trends.csv")

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
ax = axes[0]
ax.plot(means.index, means["treated"], marker="o", ms=3, label="treated firms (15)")
ax.plot(means.index, means["control"], marker="o", ms=3, label="control firms (35)")
ax.axvline(start, color="black", ls="--", lw=1)
ax.text(start + 0.5, ax.get_ylim()[1], " launch (month 25)", va="top", fontsize=8)
ax.set_xlabel(cfg["time"])
ax.set_ylabel(f"mean {cfg['outcome']} (thousand euro)")
ax.set_title("Mean revenue by group")
ax.legend(frameon=False)

ax = axes[1]
ax.plot(means.index, means["gap"], marker="o", ms=3, color="C3")
ax.axvline(start, color="black", ls="--", lw=1)
ax.axhline(means.loc[means.index < start, "gap"].mean(), color="grey", ls=":", lw=1)
ax.set_xlabel(cfg["time"])
ax.set_ylabel("treated minus control mean")
ax.set_title("Gap between group means (dotted = mean pre-launch gap)")
fig.tight_layout()
out = didlib.RESULTS / "raw_trends.png"
fig.savefig(out, dpi=150)
print(f"wrote {out.relative_to(didlib.ROOT)}")
print("\nmean revenue by month and group:")
print(means.round(2).to_string())
print(f"\npre-launch gap mean: {means.loc[means.index < start, 'gap'].mean():.3f}")
print(f"post-launch gap mean: {means.loc[means.index >= start, 'gap'].mean():.3f}")
