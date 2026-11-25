"""Step 5: main TWFE estimate for the agent_framing run.

Main specification (plan.md test 1): cigsale ~ treated + unit FE + year FE,
all 1209 rows, no covariates. Cross-checks:
  (a) exact two-way within transform (valid because the panel is balanced),
  (b) the simple 2x2 difference of means.

Writes results/agent_framing/04_main_estimate.txt / .json
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
treat = didlib.treated_post(cols, cfg)
cluster = unit

rows = []
def say(s=""):
    rows.append(s)
    print(s)

say("Main estimate (agent_framing run)")
say(f"specification: {cfg['outcome']} ~ treated_post + unit FE + year FE")
say(f"treatment: {cfg['treatment_rule']} ({int(treat.sum())} treated rows)")
say(f"rows used: {len(y)} (all; no filters, no covariates)")
say("")

res = didlib.twfe(unit, year, y, treat, cluster, ref_year=cfg["reference_period"])
say(f"TWFE beta (treated x post)          = {res['beta']:.4f} packs/person/year")
say(f"  classical SE                      = {res['se_classical']:.4f}")
say(f"  HC1 robust SE                     = {res['se_hc1']:.4f}")
say(f"  cluster-by-state SE (38+1 groups) = {res['se_cluster']:.4f}")
say("  NOTE: only 1 treated unit, so the cluster SE leans on the 38 control")
say("  states for the residual variance; it does NOT capture treated-unit")
say("  uncertainty. Inference therefore relies on the placebo test (step 7).")
say("")

# cross-check (a): exact two-way within transform (balanced panel).
# On a balanced panel, sequential demeaning y -> y - unit mean ->
# (that) - year mean equals y - ybar_i - ybar_t + ybar, because the second
# step subtracts ybar_t - ybar (i.e. adds the grand mean back). No third step.
yi = y - np.array([y[unit == u].mean() for u in unit])
yi = yi - np.array([yi[year == t].mean() for t in year])
ti = treat.astype(float) - np.array([treat[unit == u].mean() for u in unit])
ti = ti - np.array([ti[year == t].mean() for t in year])
beta_within = float((yi @ ti) / (ti @ ti))
say(f"cross-check (a): two-way within transform beta = {beta_within:.6f} "
    f"(differs from dummy OLS by {abs(beta_within - res['beta']):.2e})")
say("")

# cross-check (b): simple 2x2 difference of means
grp = didlib.treated_units_mask(cols, cfg)
pre = year < cfg["treatment_start"]
d_treat = y[grp & ~pre].mean() - y[grp & pre].mean()
d_ctrl = y[~grp & ~pre].mean() - y[~grp & pre].mean()
did_2x2 = d_treat - d_ctrl
say("cross-check (b): simple 2x2 difference of means")
say(f"  treated (California) change, post - pre = {d_treat:.4f}")
say(f"  control mean change, post - pre         = {d_ctrl:.4f}")
say(f"  2x2 DiD (unweighted means)              = {did_2x2:.4f}")
say(f"  difference vs TWFE beta                 = {did_2x2 - res['beta']:.4f}")
say("  (the 2x2 weights all years equally; TWFE weights years by within-unit")
say("   variance of the treatment timing, so a small difference is expected)")
say("")

with open(os.path.join(didlib.RESULTS_DIR, "04_main_estimate.json"), "w", encoding="utf-8") as f:
    json.dump({
        "twfe": res,
        "within_transform_beta": beta_within,
        "twobytwo": {
            "treated_change": float(d_treat), "control_change": float(d_ctrl),
            "did": float(did_2x2),
        },
    }, f, indent=2)
didlib.save_text("04_main_estimate.txt", rows)
print("\nwrote 04_main_estimate.txt / .json in", didlib.RESULTS_DIR)
