"""Step 5: main TWFE estimate for the agent_rerun run.

outcome ~ treated x post + unit FE + time FE, all rows, no covariates.
Cross-check: simple 2x2 difference of means (post-pre treated minus post-pre control).
With one treatment cohort and a balanced panel the two must agree exactly.

Writes results/agent_rerun/03_main_estimate.json and 03_main_estimate.txt
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import didlib

cfg = didlib.load_config()
cols, _ = didlib.read_panel(cfg)

unit = didlib.as_int(cols[cfg["unit"]])
year = didlib.as_int(cols[cfg["time"]])
y = cols[cfg["outcome"]]
is_treated_group = cols[cfg["treatment_group_column"]]
treat = is_treated_group & (year >= cfg["treatment_start"])
N = len(y)

unitD, yearD, unit_levels, year_levels = didlib.fe_dummies(unit, year, ref_year=int(year.min()))
X = np.column_stack([np.ones(N), treat.astype(float), unitD, yearD])
names = ["const", "treated_post"] + [f"unit_{g}" for g in unit_levels] + [f"year_{t}" for t in year_levels]

b, u, XtX_inv = didlib.ols(y, X)
K = X.shape[1]
v_class = didlib.vcov_classical(X, u, XtX_inv)
v_hc1 = didlib.vcov_hc1(X, u, XtX_inv)
groups = unit  # cluster = unit (config: "cluster": "state")
v_cl = didlib.vcov_cluster(X, u, XtX_inv, groups)

i = names.index("treated_post")
beta = float(b[i])
se_class = float(np.sqrt(v_class[i, i]))
se_hc1 = float(np.sqrt(v_hc1[i, i]))
se_cl = float(np.sqrt(v_cl[i, i]))
n_clusters = len(np.unique(groups))

# --- 2x2 difference of means cross-check
unit_mean = {g: (y[(unit == g) & (year < cfg["treatment_start"])].mean(),
                 y[(unit == g) & (year >= cfg["treatment_start"])].mean()) for g in np.unique(unit)}
ca = cfg["treated_units"][0]
treated_units = np.unique(unit[treat])
did_2x2 = ((unit_mean[ca][1] - unit_mean[ca][0])
           - (np.mean([unit_mean[g][1] for g in np.unique(unit) if g not in treated_units])
              - np.mean([unit_mean[g][0] for g in np.unique(unit) if g not in treated_units])))

# (a two-way-demeaned replication is skipped: with one cohort and a balanced
# panel, TWFE is algebraically the 2x2, which is the cross-check above)

report = {
    "n_rows": N,
    "n_parameters": K,
    "n_treated_units": int(len(treated_units)),
    "n_clusters": n_clusters,
    "beta_treated_post": beta,
    "se_classical": se_class,
    "se_hc1": se_hc1,
    "se_cluster_by_unit": se_cl,
    "did_2x2_difference_of_means": float(did_2x2),
    "beta_minus_2x2": float(beta - did_2x2),
    "r_squared": float(1 - (u @ u) / ((y - y.mean()) @ (y - y.mean()))),
}
out_json = os.path.join(didlib.RESULTS_DIR, "03_main_estimate.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

lines = []
lines.append("Main TWFE estimate (agent_rerun)")
lines.append(f"specification: {cfg['outcome']} ~ treated_post + unit FE + year FE "
             f"(treatment = {cfg['treatment_definition']}, start {cfg['treatment_start']})")
lines.append(f"rows: {N} (all rows, no filter); parameters: {K}; treated units: {len(treated_units)}; "
             f"clusters: {n_clusters}")
lines.append("")
lines.append(f"beta(treated_post)          = {beta: .4f} packs/person/year")
lines.append(f"  SE classical              = {se_class:.4f}")
lines.append(f"  SE HC1 robust             = {se_hc1:.4f}")
lines.append(f"  SE clustered by unit      = {se_cl:.4f}   <- NOT reliable with 1 treated unit; "
             f"placebo test is the inference (see 05_placebo)")
lines.append("")
lines.append(f"2x2 difference of means     = {did_2x2: .4f}")
lines.append(f"TWFE beta - 2x2             = {beta - did_2x2: .2e} (must be ~0: single cohort, balanced panel)")
lines.append(f"R2                          = {report['r_squared']:.4f}")
out_txt = os.path.join(didlib.RESULTS_DIR, "03_main_estimate.txt")
with open(out_txt, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines))
print(f"\nwrote {out_json}\nwrote {out_txt}")
