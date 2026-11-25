"""Placebo test for the agent_run5 DiD run (step 7).

With 1 treated unit, clustered SEs are not reliable, so inference uses placebos:
assign the (placebo) treatment in 1989 to each of the 38 control states in turn,
re-estimate the same TWFE, and compare all 39 estimates (California's real one
among them). California's rank (1 = most negative) gives the placebo
p-value = rank / 39. Saves results/agent_run5/placebo.csv and
fig_placebo.png.
"""
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import didlib as dl

cfg = dl.load_config()
DATA, UNIT, TIME, OUT = cfg["data_path"], cfg["unit"], cfg["time"], cfg["outcome"]
GRP, TSTART = cfg["treatment_group_col"], cfg["treatment_start"]

cols, n = dl.read_panel(DATA)
state = dl.as_int(cols[UNIT])
year = dl.as_int(cols[TIME])
y = dl.as_float(cols[OUT])
grp = dl.as_bool(cols[GRP])
print(f"rows used: {n} (no filter)")

units = np.unique(state)
rows = []
for u in units:
    placebo = ((state == u) & (year >= TSTART)).astype(float)
    res = dl.twfe(y, state, year, [placebo], state)
    rows.append({"unit": int(u), "real_california": bool(grp[state == u][0]),
                 "coef": res["coef"]})
rows.sort(key=lambda r: r["coef"])  # most negative first
for i, r in enumerate(rows, start=1):
    r["rank"] = i

ca = next(r for r in rows if r["real_california"])
n_units = len(rows)
pval = ca["rank"] / n_units
print(f"\nCalifornia (state {ca['unit']}) estimate: {ca['coef']:.4f}")
print(f"placebo estimates range: {rows[0]['coef']:.4f} (state {rows[0]['unit']}) .. "
      f"{rows[-1]['coef']:.4f} (state {rows[-1]['unit']})")
print(f"California's rank among {n_units} (1 = most negative): {ca['rank']}")
print(f"placebo p-value = rank / {n_units} = {pval:.4f}")
print("verdict: California IS the most negative" if ca["rank"] == 1 else
      "verdict: California is NOT the most negative")

with open("results/agent_run5/placebo.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["rank", "unit", "real_california", "coef"])
    w.writeheader()
    w.writerows(rows)
print(f"wrote results/agent_run5/placebo.csv")

coefs = np.array([r["coef"] for r in rows])
fig, ax = plt.subplots(figsize=(9, 5))
ax.hist(coefs, bins=13, color="tab:gray", edgecolor="white")
ax.axvline(ca["coef"], color="tab:red", lw=2,
           label=f"California estimate {ca['coef']:.1f} (rank {ca['rank']} of {n_units}, p = {pval:.3f})")
ax.set_xlabel(f"TWFE coefficient on placebo treatment ({OUT}, packs/person/year)")
ax.set_ylabel("number of states")
ax.set_title("Placebo distribution: same design with each control state as 'treated'")
ax.legend()
fig.tight_layout()
fig.savefig("results/agent_run5/fig_placebo.png", dpi=150)
print("wrote results/agent_run5/fig_placebo.png")
