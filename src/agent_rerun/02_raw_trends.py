"""Step 4: raw trends for the agent_rerun run.

Mean outcome by year, treated (California, state 3) vs controls, with a
vertical line at treatment start. Writes:
  results/agent_rerun/02_group_means.csv
  results/agent_rerun/02_raw_trends.png
"""
import json
import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import didlib

cfg = didlib.load_config()
cols, _ = didlib.read_panel(cfg)

unit = didlib.as_int(cols[cfg["unit"]])
year = didlib.as_int(cols[cfg["time"]])
y = cols[cfg["outcome"]]
is_treated = cols[cfg["treatment_group_column"]]  # group membership, constant within unit
t0 = cfg["treatment_start"]

years = np.arange(year.min(), year.max() + 1)
mean_t = np.array([y[(year == t) & is_treated].mean() for t in years])
mean_c = np.array([y[(year == t) & ~is_treated].mean() for t in years])
gap = mean_t - mean_c

out_csv = os.path.join(didlib.RESULTS_DIR, "02_group_means.csv")
with open(out_csv, "w", encoding="utf-8") as f:
    f.write("year,mean_treated,mean_control,gap_treated_minus_control\n")
    for t, a, b, g in zip(years, mean_t, mean_c, gap):
        f.write(f"{t},{a:.4f},{b:.4f},{g:.4f}\n")
print(f"wrote {out_csv}  ({len(years)} yearly rows; means over "
      f"{int(is_treated.sum() // len(years))} treated and {int((~is_treated).sum() // len(years))} control units)")

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

ax = axes[0]
ax.plot(years, mean_t, marker="o", ms=3, label=f"California (state {cfg['treated_units'][0]})", color="#b2182b")
ax.plot(years, mean_c, marker="s", ms=3, label="38 control states (mean)", color="#2166ac")
ax.axvline(t0, color="black", ls="--", lw=1)
ax.text(t0 + 0.3, ax.get_ylim()[1] * 0.97, f"treatment starts {t0}", va="top", fontsize=9)
ax.set_xlabel("year")
ax.set_ylabel(f"mean {cfg['outcome']} (packs/person/year)")
ax.set_title("Raw mean outcome by year")
ax.legend(fontsize=8)

ax = axes[1]
ax.plot(years, gap, marker="o", ms=3, color="#4d4d4d", label="gap: California − controls")
ax.axvline(t0, color="black", ls="--", lw=1)
ax.axhline(0, color="grey", lw=0.5)
ax.set_xlabel("year")
ax.set_ylabel(f"{cfg['outcome']} gap (packs/person/year)")
ax.set_title("Treated-minus-control gap by year")
ax.legend(fontsize=8)

fig.suptitle("Per-capita cigarette sales, California vs control states", fontsize=11)
fig.tight_layout()
out_png = os.path.join(didlib.RESULTS_DIR, "02_raw_trends.png")
fig.savefig(out_png, dpi=150)
plt.close(fig)
print(f"wrote {out_png}")

# pre-1989 linear slope of the raw gap, packs/person/year per year (descriptive)
pre = years < t0
slope = np.polyfit(years[pre], gap[pre], 1)[0]
post_slope = np.polyfit(years[~pre], gap[~pre], 1)[0]
print(f"descriptive OLS slope of the raw gap, pre {t0}: {slope:.3f} packs/person/year per year")
print(f"descriptive OLS slope of the raw gap, post {t0 - 1}: {post_slope:.3f} packs/person/year per year")
with open(os.path.join(didlib.RESULTS_DIR, "02_group_means.json"), "w", encoding="utf-8") as f:
    json.dump({"slope_gap_pre": float(slope), "slope_gap_post": float(post_slope),
               "treatment_start": t0}, f, indent=2)
