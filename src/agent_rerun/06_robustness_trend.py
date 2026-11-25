"""Step 8: robustness to a California-specific linear pre-trend (agent_rerun run).

Two implementations of plan.md test 4 ('the same DiD with a California-specific
linear time trend fitted on the pre-period'):

(A) two-step: on the pre-1989 rows only, OLS of cigsale on
    [California x t] + unit FE + year FE  (t = year - 1988) gives theta, the
    California-specific slope differential fitted on the pre-period. Remove
    that trend from California in ALL years (cigsale_adj = cigsale - theta*t
    for California, 0 for controls) and re-run the main TWFE on the adjusted
    outcome.

(B) one-step: full-sample TWFE with an extra California x t regressor
    (theta estimated from all periods, i.e. trend not restricted to pre-period).

Writes results/agent_rerun/06_robustness.json and 06_robustness.txt
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
t = year - cfg["reference_year_event_study"]  # 0 at 1988
N = len(y)

unitD, yearD, unit_levels, year_levels = didlib.fe_dummies(unit, year, ref_year=int(year.min()))

# ---- main beta for comparison (same as 03)
X0 = np.column_stack([np.ones(N), treat.astype(float), unitD, yearD])
b0, _, _ = didlib.ols(y, X0)
beta_main = float(b0[1])

# ---- (A) two-step
pre = year < cfg["treatment_start"]
# rebuild FE dummies on the pre-sample: slicing the full-sample year dummies
# would leave all-zero columns for 1989..2000
unitD_p, yearD_p, _, _ = didlib.fe_dummies(unit[pre], year[pre], ref_year=int(year[pre].min()))
X_pre = np.column_stack([np.ones(pre.sum()), is_treated_group[pre].astype(float) * t[pre],
                         unitD_p, yearD_p])
b_pre, u_pre, XtX_inv_pre = didlib.ols(y[pre], X_pre)
theta_pre = float(b_pre[1])
se_theta_pre = float(np.sqrt(didlib.vcov_classical(X_pre, u_pre, XtX_inv_pre)[1, 1]))

y_adj = y - theta_pre * t * is_treated_group  # remove CA's own pre-fitted linear trend in all years
X_adj = np.column_stack([np.ones(N), treat.astype(float), unitD, yearD])
b_adj, u_adj, inv_adj = didlib.ols(y_adj, X_adj)
beta_2step = float(b_adj[1])
se_2step = float(np.sqrt(didlib.vcov_cluster(X_adj, u_adj, inv_adj, unit)[1, 1]))

# ---- (B) one-step
X_one = np.column_stack([np.ones(N), treat.astype(float), is_treated_group.astype(float) * t, unitD, yearD])
b_one, u_one, inv_one = didlib.ols(y, X_one)
theta_one = float(b_one[2])
se_theta_one = float(np.sqrt(didlib.vcov_cluster(X_one, u_one, inv_one, unit)[2, 2]))
beta_1step = float(b_one[1])
se_1step = float(np.sqrt(didlib.vcov_cluster(X_one, u_one, inv_one, unit)[1, 1]))

res = {
    "beta_main": beta_main,
    "two_step": {
        "theta_ca_slope_diff_pre_fitted": theta_pre,
        "se_theta_classical": se_theta_pre,
        "beta_after_detrending": beta_2step,
        "se_beta_cluster_by_unit": se_2step,
        "change_vs_main": beta_2step - beta_main,
    },
    "one_step": {
        "theta_ca_slope_diff_all_periods": theta_one,
        "se_theta_cluster_by_unit": se_theta_one,
        "beta_with_ca_trend_regressor": beta_1step,
        "se_beta_cluster_by_unit": se_1step,
        "change_vs_main": beta_1step - beta_main,
    },
}
out_json = os.path.join(didlib.RESULTS_DIR, "06_robustness.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2)

lines = []
lines.append("Robustness: California-specific linear pre-trend (agent_rerun)")
lines.append(f"main beta (no trend adjustment)              = {beta_main: .4f}")
lines.append("")
lines.append(f"(A) two-step, theta fitted on pre-1989 rows:")
lines.append(f"    theta (CA slope differential, pre)       = {theta_pre: .4f} (classical SE {se_theta_pre:.4f}) packs/person/year per year")
lines.append(f"    beta after removing CA pre-trend         = {beta_2step: .4f} (cluster SE {se_2step:.4f})")
lines.append(f"    change vs main                           = {beta_2step - beta_main: .4f}")
lines.append("")
lines.append(f"(B) one-step, California x t regressor, all periods:")
lines.append(f"    theta (CA slope differential)            = {theta_one: .4f} (cluster SE {se_theta_one:.4f})")
lines.append(f"    beta(treated_post)                       = {beta_1step: .4f} (cluster SE {se_1step:.4f})")
lines.append(f"    change vs main                           = {beta_1step - beta_main: .4f}")
out_txt = os.path.join(didlib.RESULTS_DIR, "06_robustness.txt")
with open(out_txt, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines))
print(f"\nwrote {out_json}\nwrote {out_txt}")
