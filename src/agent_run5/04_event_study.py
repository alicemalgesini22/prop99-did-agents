"""Event study for the agent_run5 DiD run (step 6).

One coefficient per year relative to the last pre-treatment year (1988):
cigsale ~ treated x year-dummies (all years except 1988) + state FE + year FE.
Plots the coefficients; saves results/agent_run5/event_study.csv and
fig_event_study.png. Column names from did_config.json.
"""
import csv
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import didlib as dl

cfg = dl.load_config()
DATA, UNIT, TIME, OUT = cfg["data_path"], cfg["unit"], cfg["time"], cfg["outcome"]
GRP, TSTART = cfg["treatment_group_col"], cfg["treatment_start"]
REF = TSTART - 1  # 1988, last pre-treatment year, per plan.md test 2

cols, n = dl.read_panel(DATA)
state = dl.as_int(cols[UNIT])
year = dl.as_int(cols[TIME])
y = dl.as_float(cols[OUT])
grp = dl.as_bool(cols[GRP])
print(f"rows used: {n} (no filter)")

years = np.unique(year)
extra = []
labels = []
for t in years:
    if t == REF:
        continue
    extra.append(((grp & (year == t)).astype(float)))
    labels.append(int(t))
res = dl.twfe(y, state, year, extra, state)

betas = res["beta_all"][-len(extra):]
ses = np.array([res["se_classical"]] * len(extra))  # placeholder, recomputed below
# recompute classical SEs per coefficient from the same fit: rerun with one column at a time
# is wasteful; instead pull the full vcov once:
units = np.unique(state)
years_u = np.unique(year)
D_unit = np.zeros((n, len(units)))
for j, g in enumerate(units):
    D_unit[state == g, j] = 1.0
D_year = np.zeros((n, len(years_u) - 1))
for j, t in enumerate(years_u[1:]):
    D_year[year == t, j] = 1.0
X = np.column_stack([D_unit, D_year] + [np.asarray(c, dtype=float) for c in extra])
beta, u, rank, vcov = dl.ols(y, X)
ses = np.sqrt(np.diag(vcov))[-len(extra):]

rows = []
for t, b, s in zip(labels, betas, ses):
    rel = t - REF
    rows.append({"year": t, "rel": rel, "coef": float(b), "se": float(s),
                 "lo": float(b - 1.96 * s), "hi": float(b + 1.96 * s)})
with open("results/agent_run5/event_study.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["year", "rel", "coef", "se", "lo", "hi"])
    w.writeheader()
    w.writerows(rows)

print(f"reference year: {REF} (coefficient normalized to 0)")
pre = [r for r in rows if r["rel"] < 0]
post = [r for r in rows if r["rel"] > 0]
print(f"pre-period coefficients ({len(pre)} years 1970-1987 vs 1988):")
for r in pre:
    print(f"  {r['year']}: {r['coef']:+.2f} (95% CI {r['lo']:+.2f}, {r['hi']:+.2f})")
print(f"post-period coefficients ({len(post)} years 1989-2000 vs 1988):")
for r in post:
    print(f"  {r['year']}: {r['coef']:+.2f} (95% CI {r['lo']:+.2f}, {r['hi']:+.2f})")

pre_c = np.array([r["coef"] for r in pre])
print(f"\npre-trend pattern: first-half mean {pre_c[:len(pre_c)//2].mean():+.2f}, "
      f"second-half mean {pre_c[len(pre_c)//2:].mean():+.2f}")
print(f"max |pre| coefficient: {np.abs(pre_c).max():.2f} at year {pre[int(np.abs(pre_c).argmax())]['year']}")
print("verdict (computed above): pre-1989 coefficients "
      + ("roughly flat" if np.abs(pre_c).max() < 5 else "NOT flat"))

fig, ax = plt.subplots(figsize=(10, 5))
rel = np.array([r["rel"] for r in rows])
c = np.array([r["coef"] for r in rows])
lo = np.array([r["lo"] for r in rows])
hi = np.array([r["hi"] for r in rows])
ax.errorbar(rel, c, yerr=[c - lo, hi - c], fmt="o", capsize=3, color="tab:blue")
ax.axvline(0, color="black", ls="--", lw=1, label=f"reference year {REF}")
ax.axhline(0, color="gray", lw=0.8)
ax.set_xlabel(f"years relative to {REF} (treatment starts {TSTART})")
ax.set_ylabel(f"{OUT} gap vs 1988 (packs/person/year)")
ax.set_title("Event study: California vs 38 control states")
ax.legend()
fig.tight_layout()
fig.savefig("results/agent_run5/fig_event_study.png", dpi=150)
print("\nwrote results/agent_run5/event_study.csv and fig_event_study.png")
