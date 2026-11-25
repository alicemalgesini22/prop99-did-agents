"""Step 8: Robustness — DiD with a California-specific linear pre-trend.

Primary method (plan.md test 4, "fitted on the pre-period"):
  1. Pre-period (1970-1988 only): fit OLS of the treated-vs-control-mean gap
     on a linear time trend.
  2. Extrapolate that trend through the post period as the counterfactual gap.
  3. Trend-adjusted effect = mean post-period gap - mean extrapolated gap.

Secondary reference (DIFFERENT estimator, trend fitted on ALL periods):
  TWFE with an added treated-unit x linear time term. Reported only for
  comparison; it does NOT fit the trend on the pre-period alone.

Reads results/workflow/did_config.json; no column names are hard-coded.
Outputs: results/workflow/08_robustness.txt, 08_robustness.csv, 08_robustness.png
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[2]
CFG_PATH = ROOT / "results" / "workflow" / "did_config.json"
OUT_TXT = ROOT / "results" / "workflow" / "08_robustness.txt"
OUT_CSV = ROOT / "results" / "workflow" / "08_robustness.csv"
OUT_PNG = ROOT / "results" / "workflow" / "08_robustness.png"

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
is_treated = df[UNIT].isin(treated_ids)
post = df[TIME] >= start

means = (df.assign(treated=is_treated)
           .groupby([TIME, "treated"])[OUTCOME].mean().unstack("treated")
           .rename(columns={False: "control_mean", True: "treated_mean"}))
means["gap"] = means.treated_mean - means.control_mean
pre_years = sorted(y for y in means.index if y < start)
post_years = sorted(y for y in means.index if y >= start)

# --- 1. fit linear trend of the gap on pre-period only ---
X_pre = np.column_stack([np.ones(len(pre_years)), np.array(pre_years, float)])
y_pre = means.loc[pre_years, "gap"].to_numpy()
beta = np.linalg.lstsq(X_pre, y_pre, rcond=None)[0]
intercept, slope = beta
resid_var = np.sum((y_pre - X_pre @ beta) ** 2) / (len(pre_years) - 2)
cov = resid_var * np.linalg.inv(X_pre.T @ X_pre)
slope_se = float(np.sqrt(cov[1, 1]))

say("Pre-period gap trend (fitted on 1970-1988 ONLY):")
say(f"  gap_t = {intercept:.3f} + {slope:.4f} * year   (slope SE {slope_se:.4f})")
say(f"  i.e. the treated-vs-control gap widened by {abs(slope):.3f} packs/year before treatment "
    f"(California fell further behind the controls)")
say("")

# --- 2-3. extrapolate, compute trend-adjusted effect ---
extrapolated = {y: intercept + slope * y for y in means.index}
res = means.copy()
res["extrapolated_gap"] = pd.Series(extrapolated)
res["effect_vs_trend"] = res.gap - res.extrapolated_gap
pre_eff = res.loc[pre_years, "effect_vs_trend"]
post_eff = res.loc[post_years, "effect_vs_trend"]
trend_adjusted = post_eff.mean()
raw_gap = res.loc[post_years, "gap"].mean()
say("Post period (1989-2000):")
say(f"  mean raw gap                : {raw_gap:.3f}")
say(f"  mean extrapolated gap       : {res.loc[post_years, 'extrapolated_gap'].mean():.3f}")
say(f"  TREND-ADJUSTED EFFECT       : {trend_adjusted:.3f}  "
    f"(per-year effects {post_eff.min():.2f} to {post_eff.max():.2f})")
say("")
say("Pre period (1970-1988) same measure (should be ~0 by construction):")
say(f"  mean pre effect vs trend    : {pre_eff.mean():.3f}")
say(f"  pre effects range           : {pre_eff.min():.2f} to {pre_eff.max():.2f}")
say("")

# --- secondary TWFE variant: treated x linear time on ALL periods (comparison only) ---
d = df.copy()
d["treat_post"] = (is_treated & post).astype(int)
d["treated_time"] = is_treated.astype(int) * d[TIME]
fit2 = smf.ols(f"{OUTCOME} ~ treat_post + treated_time + C({UNIT}) + C({TIME})",
               data=d).fit()
say("Secondary (different estimator; trend fitted on ALL periods, not pre-only):")
say(f"  TWFE + treated x linear time: treat_post {fit2.params['treat_post']:.3f}, "
    f"trend coef {fit2.params['treated_time']:+.4f}")

say("")
say("Comparison with unadjusted TWFE estimate: -27.349 (05_main_estimate.txt)")
say(f"  trend-adjusted: {trend_adjusted:.3f} "
    f"(change from TWFE: {trend_adjusted - (-27.349):+.3f})")

res.round(3).to_csv(OUT_CSV)

fig, ax = plt.subplots(figsize=(8.5, 5))
ax.plot(res.index, res.gap, marker="o", color="tab:red", label="gap: treated - control mean")
ax.plot(res.index, res.extrapolated_gap, linestyle="--", color="black",
        label=f"linear trend fitted on pre-period only (slope {slope:.3f}/yr)")
ax.axvline(start - 0.5, color="grey", linewidth=1)
ax.set_xlabel(TIME)
ax.set_ylabel(f"{OUTCOME} gap (packs/person/year)")
ax.set_title("Treated-vs-control gap vs pre-period linear trend extrapolation")
ax.legend()
fig.tight_layout()
fig.savefig(OUT_PNG, dpi=150)

OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\nSaved {OUT_TXT}, {OUT_CSV}, {OUT_PNG}")
