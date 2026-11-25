"""Raw trends plot for the agent_run5 DiD run (step 4).

Mean outcome per year for treated vs control units, with a vertical line at
treatment start. Saves results/agent_run5/fig_raw_trends.png and a small csv
of the series. Column names from did_config.json.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import didlib as dl
import csv

cfg = dl.load_config()
DATA, UNIT, TIME, OUT = cfg["data_path"], cfg["unit"], cfg["time"], cfg["outcome"]
GRP, TSTART = cfg["treatment_group_col"], cfg["treatment_start"]

cols, n = dl.read_panel(DATA)
state = dl.as_int(cols[UNIT])
year = dl.as_int(cols[TIME])
y = dl.as_float(cols[OUT])
grp = dl.as_bool(cols[GRP])
print(f"rows used: {n} (no filter; balanced panel verified by 01_panel_checks.py)")

years = np.unique(year)
mean_tr = np.array([y[(year == t) & grp].mean() for t in years])
mean_ct = np.array([y[(year == t) & ~grp].mean() for t in years])

with open("results/agent_run5/raw_trends.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow([TIME, f"mean_{OUT}_treated_state3", f"mean_{OUT}_control_38states"])
    for t, a, b in zip(years, mean_tr, mean_ct):
        w.writerow([int(t), f"{a:.4f}", f"{b:.4f}"])
print("wrote results/agent_run5/raw_trends.csv")

pre_gap = (mean_tr[years < TSTART] - mean_ct[years < TSTART])
print(f"pre-period treated-control gap: {pre_gap[0]:.1f} (1970) -> {pre_gap[-1]:.1f} (1988)")
print(f"gap change over pre-period: {pre_gap[-1] - pre_gap[0]:.1f} packs/person/year")

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(years, mean_tr, "o-", label=f"California (treated, state 3)", color="tab:red")
ax.plot(years, mean_ct, "o-", label="Other 38 states (control mean)", color="tab:gray")
ax.axvline(TSTART - 0.5, color="black", ls="--", lw=1,
           label=f"Treatment start ({TSTART}: Proposition 99 tax)")
ax.set_xlabel("year")
ax.set_ylabel(f"{OUT} (packs per person per year)")
ax.set_title(f"Mean {OUT}: California vs 38 control states")
ax.legend()
fig.tight_layout()
fig.savefig("results/agent_run5/fig_raw_trends.png", dpi=150)
print("wrote results/agent_run5/fig_raw_trends.png")
