"""Main two-way FE estimate for the agent_run5 DiD run (step 5).

cigsale ~ treated + state FE + year FE, all rows, no covariates.
Cross-check: simple 2x2 difference of means. Mechanism check (plan.md Theory):
the same specification on retprice. Saves results/agent_run5/main_estimate.json.
Column names from did_config.json.
"""
import json

import numpy as np

import didlib as dl

cfg = dl.load_config()
DATA, UNIT, TIME = cfg["data_path"], cfg["unit"], cfg["time"]
GRP, TSTART = cfg["treatment_group_col"], cfg["treatment_start"]

cols, n = dl.read_panel(DATA)
state = dl.as_int(cols[UNIT])
year = dl.as_int(cols[TIME])
grp = dl.as_bool(cols[GRP])
trt = (grp & (year >= TSTART)).astype(float)

print(f"rows used: {n} (no filter; all rows kept)")
print(f"treated rows (treatment=1): {int(trt.sum())}, treated units: {int(grp.sum() // len(np.unique(year)))}")

out = {}
for outcome in (cfg["outcome"], "retprice"):
    y = dl.as_float(cols[outcome])
    res = dl.twfe(y, state, year, [trt], state)
    print(f"\n=== TWFE, outcome = {outcome} ===")
    print(f"  coefficient on treated: {res['coef']:.4f}")
    print(f"  SE (classical):        {res['se_classical']:.4f}")
    print(f"  SE (cluster by state, CR1, 39 clusters): {res['se_cluster']:.4f}")
    print(f"  t = {res['t_cluster']:.2f}, p = {res['p_cluster']:.4f}")
    print(f"  NOTE: only 1 treated unit -> clustered SE is not reliable; "
          f"inference below uses the placebo test (05_placebo.py)")
    out[outcome] = {k: res[k] for k in ("coef", "se_classical", "se_cluster", "t_cluster", "p_cluster", "n", "rank", "clusters")}

    # 2x2 difference of means cross-check
    pre = year < TSTART
    d1 = y[grp & pre].mean() - y[~grp & pre].mean()
    d2 = y[grp & ~pre].mean() - y[~grp & ~pre].mean()
    dd = d2 - d1
    print(f"  2x2 cross-check: treated-control gap pre = {d1:.4f}, post = {d2:.4f}, "
          f"DiD = {dd:.4f}")
    out[outcome]["did_2x2"] = float(dd)
    out[outcome]["gap_pre"] = float(d1)
    out[outcome]["gap_post"] = float(d2)

with open("results/agent_run5/main_estimate.json", "w") as f:
    json.dump(out, f, indent=2)
print("\nwrote results/agent_run5/main_estimate.json")
