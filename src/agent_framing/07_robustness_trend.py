"""Step 8: robustness to a California-specific linear pre-trend (plan.md test 4).

(A) two-step (the plan's wording): on the pre-1989 rows only, OLS of the
    outcome on [California x t] + unit FE + year FE (t = year - 1988) gives
    theta, California's differential slope fitted on the pre-period. Remove
    that trend from California in ALL years and re-run the main TWFE on the
    adjusted outcome.

(B) one-step variant: full-sample TWFE with an extra California x t
    regressor (theta estimated from all periods, i.e. NOT restricted to the
    pre-period).

Writes results/agent_framing/07_robustness.txt / .json
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
grp = didlib.treated_units_mask(cols, cfg)
treat = didlib.treated_post(cols, cfg)
cluster = unit
t = year - cfg["reference_period"]  # 0 at the reference year
N = len(y)

rows = []
def say(s=""):
    rows.append(s)
    print(s)

say("Robustness: California-specific linear pre-trend (agent_framing run)")
say("rows used in every regression below: 1209, except the pre-period fit:")
say("")

# main beta for comparison
res_main = didlib.twfe(unit, year, y, treat, cluster, ref_year=cfg["reference_period"])
beta_main = res_main["beta"]
say(f"main TWFE beta (no trend adjustment) = {beta_main:.4f}")
say("")

# ---- (A) two-step: theta fitted on pre-period rows only
pre = year < cfg["treatment_start"]
say(f"pre-period fit: rows used {int(pre.sum())} of {N} "
    f"({int(pre.sum()) // len(np.unique(unit))} years x 39 states; "
    f"dropped {N - int(pre.sum())} post-1988 rows because plan.md fits the trend on the pre-period only)")
unitD_p, yearD_p, _, _ = didlib.fe_dummies(unit[pre], year[pre], ref_year=int(year[pre].min()))
X_pre = np.column_stack([np.ones(int(pre.sum())), grp[pre].astype(float) * t[pre], unitD_p, yearD_p])
b_pre, u_pre, XtX_inv_pre, rank_pre = didlib.ols(y[pre], X_pre)
assert rank_pre == X_pre.shape[1], "pre-period trend design not full rank"
theta_pre = float(b_pre[1])
se_theta_pre = float(np.sqrt(didlib.vcov_classical(X_pre, u_pre, XtX_inv_pre)[1, 1]))

y_adj = y - theta_pre * t * grp  # remove CA's pre-fitted differential trend in all years
res_adj = didlib.twfe(unit, year, y_adj, treat, cluster, ref_year=cfg["reference_period"])
beta_2step = res_adj["beta"]
say("")
say("(A) two-step, theta fitted on pre-1989 rows only:")
say(f"    theta (CA differential slope, pre)  = {theta_pre:.4f} "
    f"(classical SE {se_theta_pre:.4f}) packs/person/year per year")
say(f"    beta after removing CA pre-trend    = {beta_2step:.4f} (cluster SE {res_adj['se_cluster']:.4f})")
say(f"    change vs main                      = {beta_2step - beta_main:.4f}")
say("")

# ---- (B) one-step variant
unitD, yearD, _, _ = didlib.fe_dummies(unit, year, ref_year=cfg["reference_period"])
X_one = np.column_stack([np.ones(N), treat.astype(float), grp.astype(float) * t, unitD, yearD])
b_one, u_one, XtX_inv_one, rank_one = didlib.ols(y, X_one)
assert rank_one == X_one.shape[1], "one-step trend design not full rank"
theta_one = float(b_one[2])
se_theta_one = float(np.sqrt(didlib.vcov_cluster(X_one, u_one, XtX_inv_one, cluster)[2, 2]))
beta_1step = float(b_one[1])
say("(B) one-step, California x t regressor estimated on all periods:")
say(f"    theta (CA differential slope)       = {theta_one:.4f} (cluster SE {se_theta_one:.4f})")
say(f"    beta(treated_post)                  = {beta_1step:.4f} "
    f"(cluster SE {float(np.sqrt(didlib.vcov_cluster(X_one, u_one, XtX_inv_one, cluster)[1, 1])):.4f})")
say(f"    change vs main                      = {beta_1step - beta_main:.4f}")

with open(os.path.join(didlib.RESULTS_DIR, "07_robustness.json"), "w", encoding="utf-8") as f:
    json.dump({
        "beta_main": beta_main,
        "two_step_pre_fitted": {
            "theta": theta_pre, "se_theta_classical": se_theta_pre,
            "beta": beta_2step, "se_cluster": res_adj["se_cluster"],
            "change_vs_main": beta_2step - beta_main,
            "pre_rows_used": int(pre.sum()),
        },
        "one_step_all_periods": {
            "theta": theta_one, "se_theta_cluster": se_theta_one,
            "beta": beta_1step, "change_vs_main": beta_1step - beta_main,
        },
    }, f, indent=2)
didlib.save_text("07_robustness.txt", rows)
print("\nwrote 07_robustness.txt / .json in", didlib.RESULTS_DIR)
