"""Step 5: Main two-way fixed effects DiD estimate + 2x2 cross-check.

Reads results/workflow/did_config.json; no column names are hard-coded.
Outputs: results/workflow/05_main_estimate.txt
"""
import json
from pathlib import Path

import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[2]
CFG_PATH = ROOT / "results" / "workflow" / "did_config.json"
OUT_PATH = ROOT / "results" / "workflow" / "05_main_estimate.txt"

cfg = json.loads(CFG_PATH.read_text())
UNIT, TIME, OUTCOME = cfg["unit"], cfg["time"], cfg["outcome"]
DATA = ROOT / cfg["data_path"]

lines = []


def say(s=""):
    print(s)
    lines.append(str(s))


df = pd.read_csv(DATA)
treated_ids = cfg["treated_units"]
start = cfg["treatment_start"]

# treatment indicator: treated unit AND post period (NEVER the raw after_treatment column)
df = df.assign(
    is_treated=df[UNIT].isin(treated_ids),
    post=df[TIME] >= start,
)
df["treat_post"] = (df.is_treated & df.post).astype(int)

n_rows = len(df)
say(f"Rows used: {n_rows} (no filters: outcome complete, panel balanced)")

# --- TWFE: outcome ~ treat_post + unit FE + time FE ---
formula = f"{OUTCOME} ~ treat_post + C({UNIT}) + C({TIME})"
fit = smf.ols(formula, data=df).fit()
# cluster-robust SE by unit for reference (unreliable with 1 treated unit - see step 3)
fit_c = smf.ols(formula, data=df).fit(cov_type="cluster",
                                      cov_kwds={"groups": df[UNIT]})
b = fit.params["treat_post"]
se = fit.bse["treat_post"]
b_c, se_c = fit_c.params["treat_post"], fit_c.bse["treat_post"]
say("")
say(f"TWFE: {formula}")
say(f"  treat_post coefficient : {b:.3f}")
say(f"  classical SE           : {se:.3f}  (p = {fit.pvalues['treat_post']:.4f})")
say(f"  cluster-by-{UNIT} SE   : {se_c:.3f}  (p = {fit_c.pvalues['treat_post']:.4f})")
say("  NOTE: cluster SEs are UNRELIABLE here (only 1 treated unit, 39 clusters,")
say("  treatment varies in 1 cluster). Inference uses placebo tests (step 7).")
say(f"  R-squared: {fit.rsquared:.4f}, N = {int(fit.nobs)}")

# --- 2x2 difference of means cross-check ---
ca = df[df.is_treated]
co = df[~df.is_treated]
pre, post = ~df.post, df.post
y_ca_pre = ca.loc[pre, OUTCOME].mean()
y_ca_post = ca.loc[post, OUTCOME].mean()
y_co_pre = co.loc[pre, OUTCOME].mean()
y_co_post = co.loc[post, OUTCOME].mean()
did = (y_ca_post - y_ca_pre) - (y_co_post - y_co_pre)
say("")
say("2x2 difference of means (cross-check):")
say(f"  treated : pre {y_ca_pre:.3f} -> post {y_ca_post:.3f} (change {y_ca_post - y_ca_pre:+.3f})")
say(f"  control : pre {y_co_pre:.3f} -> post {y_co_post:.3f} (change {y_co_post - y_co_pre:+.3f})")
say(f"  DiD     : {did:.3f}")

# --- share of TWFE effect explained by unweighted-vs-regression weighting ---
say("")
say(f"Agreement check: TWFE {b:.3f} vs simple 2x2 DiD {did:.3f} "
    f"(difference {b - did:+.3f}). TWFE weights units and periods by their")
say("outcomes' variance; with an unbalanced-by-value panel these can differ.")

OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\nSaved to {OUT_PATH}")
