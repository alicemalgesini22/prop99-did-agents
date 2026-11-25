"""Robustness: California-specific linear pre-trend (step 8, plan.md test 4).

Variant A: TWFE + California dummy x linear time (year centered at 1989),
           trend coefficient estimated on the full sample.
Variant B: trend slope fitted ONLY on the pre-period (1970-1988) from
           California's own series, extrapolated to the post-period,
           California detrended by it, then the same TWFE re-run.
Saves results/agent_run5/robust_trend.json. Column names from did_config.json.
"""
import json

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
trt = (grp & (year >= TSTART)).astype(float)
print(f"rows used: {n} (no filter)")

base = dl.twfe(y, state, year, [trt], state)
print(f"baseline TWFE treated coefficient: {base['coef']:.4f}")

# Variant A: California dummy x linear time, centered at treatment start
ca = grp.astype(float)
trend = (year - TSTART).astype(float)
resA = dl.twfe(y, state, year, [trt, ca * trend], state)
# coefficient position: first extra column
print(f"\nVariant A (unit x linear time, full sample, centered at {TSTART}):")
print(f"  treated x post coefficient: {resA['coef']:.4f} "
      f"(SE cluster {resA['se_cluster']:.4f}, SE classical {resA['se_classical']:.4f})")
print(f"  change vs baseline: {resA['coef'] - base['coef']:+.4f} "
      f"({100 * (resA['coef'] - base['coef']) / abs(base['coef']):+.1f}%)")

# Variant B: slope fitted on pre-period only, from California's own series
pre = year < TSTART
pre_ca = pre & grp
b, _, rank, _ = dl.ols(y[pre_ca], np.column_stack([np.ones(int(pre_ca.sum())), year[pre_ca]]))
slope = float(b[1])
print(f"\nVariant B (slope fitted on pre-period only):")
print(f"  California pre-period OLS slope: {slope:.4f} packs/person/year "
      f"(1970-1988, {int(pre_ca.sum())} obs)")
y_det = y.copy()
mask_ca = grp
y_det[mask_ca] = y[mask_ca] - slope * (year[mask_ca] - TSTART)
resB = dl.twfe(y_det, state, year, [trt], state)
print(f"  treated x post coefficient after detrending California: {resB['coef']:.4f} "
      f"(SE cluster {resB['se_cluster']:.4f})")
print(f"  change vs baseline: {resB['coef'] - base['coef']:+.4f} "
      f"({100 * (resB['coef'] - base['coef']) / abs(base['coef']):+.1f}%)")

out = {
    "baseline_coef": base["coef"],
    "baseline_se_cluster": base["se_cluster"],
    "variantA_coef": resA["coef"],
    "variantA_se_cluster": resA["se_cluster"],
    "variantA_se_classical": resA["se_classical"],
    "variantB_coef": resB["coef"],
    "variantB_se_cluster": resB["se_cluster"],
    "preperiod_slope": slope,
}
with open("results/agent_run5/robust_trend.json", "w") as f:
    json.dump(out, f, indent=2)
print("\nwrote results/agent_run5/robust_trend.json")
