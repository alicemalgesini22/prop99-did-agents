"""Step 4: raw trends for the agent_framing run.

Mean outcome by year for the treated group vs the control group, with a
vertical line at the treatment start. Saves PNG + CSV of the means.

Writes results/agent_framing/03_raw_trends.png / 03_raw_trends.csv
"""
import csv
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import didlib

cfg = didlib.load_config()
cols, _ = didlib.read_panel(cfg)

unit = didlib.as_int(cols[cfg["unit"]])
year = didlib.as_int(cols[cfg["time"]])
y = cols[cfg["outcome"]]
grp = didlib.treated_units_mask(cols, cfg)
start = cfg["treatment_start"]

years = np.unique(year)
mean_t = np.array([y[(year == t) & grp].mean() for t in years])
mean_c = np.array([y[(year == t) & ~grp].mean() for t in years])
n_c_states = int((~grp).sum() / len(years))

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(years, mean_t, "o-", color="tab:red", label=f"Treated (state {cfg['treated_units'][0]}, California)")
ax.plot(years, mean_c, "o-", color="tab:blue", label=f"Controls ({n_c_states} states, mean)")
ax.axvline(start - 0.5, color="black", linestyle="--", linewidth=1,
           label=f"Treatment start ({start})")
ax.set_xlabel("Year")
ax.set_ylabel(f"{cfg['outcome']} (packs per person per year)")
ax.set_title("Per-capita cigarette sales: California vs control states\n"
             "(raw means, no adjustment)")
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
png = os.path.join(didlib.RESULTS_DIR, "03_raw_trends.png")
fig.savefig(png, dpi=150)

with open(os.path.join(didlib.RESULTS_DIR, "03_raw_trends.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["year", "mean_treated", "mean_control", "gap_treated_minus_control"])
    for t, mt, mc in zip(years, mean_t, mean_c):
        w.writerow([int(t), f"{mt:.4f}", f"{mc:.4f}", f"{mt - mc:.4f}"])

pre = year < start
gap_pre = float(np.nanmean(y[pre & grp]) - np.nanmean(y[pre & ~grp]))
gap_post = float(np.nanmean(y[~pre & grp]) - np.nanmean(y[~pre & ~grp]))
lines = [
    f"Raw trends (agent_framing): {cfg['outcome']} means by group",
    f"rows used: {len(y)} (all; no filters)",
    f"pre-period  ({year[pre].min()}-{year[pre].max()}): treated mean {np.nanmean(y[pre & grp]):.2f}, "
    f"control mean {np.nanmean(y[pre & ~grp]):.2f}, gap {gap_pre:.2f}",
    f"post-period ({year[~pre].min()}-{year[~pre].max()}): treated mean {np.nanmean(y[~pre & grp]):.2f}, "
    f"control mean {np.nanmean(y[~pre & ~grp]):.2f}, gap {gap_post:.2f}",
    f"change in gap (2x2 raw difference of means): {gap_post - gap_pre:.2f}",
    f"wrote {png}",
]
didlib.save_text("03_raw_trends.txt", lines)
print("\n".join(lines))
