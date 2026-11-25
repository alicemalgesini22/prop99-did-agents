"""Step 4: raw trends. Mean outcome by period for treated and control units, with a
vertical line at the treatment start.

Run: uv run python src/school_tutoring/04_raw_trends.py
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from didlib import RESULTS, load_config, load_panel  # noqa: E402

cfg = load_config()
df = load_panel(cfg)
START = cfg["treatment_start"]

g = (df.groupby(["_time", "_treated"])["_y"].agg(["mean", "std", "count"])
       .reset_index())
wide = g.pivot(index="_time", columns="_treated", values="mean")
wide.columns = ["control", "treated"]
wide["difference"] = wide["treated"] - wide["control"]
wide.index.name = "year"
wide.round(4).to_csv(RESULTS / "raw_trends.csv")
print(wide.round(3).to_string())
print(f"\nwrote results/{RESULTS.name}/raw_trends.csv")

fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
ax[0].plot(wide.index, wide["treated"], "o-", color="#c0392b", label="treated (20 schools)")
ax[0].plot(wide.index, wide["control"], "o-", color="#2c3e50", label="control (40 schools)")
ax[0].axvline(START, ls="--", color="grey", lw=1)
ax[0].set_title("Mean reading score by group")
ax[0].set_xlabel("year")
ax[0].set_ylabel(cfg["outcome"])
ax[0].legend(frameon=False)

ax[1].plot(wide.index, wide["difference"], "o-", color="#8e44ad")
ax[1].axvline(START, ls="--", color="grey", lw=1)
ax[1].axhline(0, color="black", lw=0.8)
ax[1].set_title("Difference in means (treated - control)")
ax[1].set_xlabel("year")
ax[1].set_ylabel("test points")

for a in ax:
    a.axvspan(START - 0.5, wide.index.max() + 0.5, color="grey", alpha=0.08)
fig.suptitle(f"Raw trends, vertical line at treatment start ({START})", fontsize=10)
fig.tight_layout()
fig.savefig(RESULTS / "raw_trends.png", dpi=150)
print(f"wrote results/{RESULTS.name}/raw_trends.png")

# how the gap moves across the break, for the write-up
pre_gap = wide.loc[wide.index < START, "difference"].mean()
post_gap = wide.loc[wide.index >= START, "difference"].mean()
print(f"\nmean gap before {START}: {pre_gap:.3f}; from {START}: {post_gap:.3f}; "
      f"change in gap: {post_gap - pre_gap:.3f}")
