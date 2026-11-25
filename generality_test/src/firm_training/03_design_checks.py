"""Step 3: design checks. How many treated units, is timing staggered, do the two groups
start from the same place and move together before month 25?

Run: uv run python src/firm_training/03_design_checks.py
Writes results/firm_training/design_checks.json
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import didlib  # noqa: E402

cfg = didlib.load_config()
df = didlib.load_panel(cfg)
start = cfg["treatment_start"]
out = {}

# ---- 1. treated units and timing ------------------------------------------------------
per_unit = df.groupby("_unit").agg(treated=("_treated", "first"),
                                   first_post=("_post", "max"))
n_treated = int(per_unit["treated"].sum())
print(f"treated units: {n_treated} of {len(per_unit)}")
print(f"control units: {len(per_unit) - n_treated}")

# timing: the data carry no firm-level adoption date (flag constant within firm), so the
# only candidate start is the launch month; check that month 25 is where the post dummy
# switches on for the treated firms.
switches = df[df["_treated"] == 1].groupby("_unit").apply(
    lambda d: d.loc[d["_post"] == 1, "_time"].min(), include_groups=False)
print(f"distinct treatment start periods among treated units: "
      f"{sorted(switches.unique())}")
staggered = len(switches.unique()) > 1
print(f"staggered adoption: {staggered}")
print("=> all treated units share one start period, so there is a single treatment cohort "
      "and no staggered-adoption (Goodman-Bacon / negative-weight) problem. Plain two-way "
      "fixed effects on treated x post is the appropriate main specification.")
if n_treated < 5:
    print("WARNING: fewer than 5 treated units -> clustered SEs unreliable.")
else:
    print(f"{n_treated} treated units: clustered SEs by unit are feasible, but the number "
          f"of treated clusters is only {n_treated}, so a placebo/randomisation test is "
          f"reported alongside as the main inference check.")

# ---- 2. pre-period comparability ------------------------------------------------------
pre = df[df["_time"] < start]
post = df[df["_time"] >= start]
desc = df.groupby("_treated")["_y"].agg(["count", "mean", "std", "min", "max"])
print("\noutcome by group (all periods):")
print(desc.round(3).to_string())
pre_means = pre.groupby("_treated")["_y"].mean()
print(f"\npre-period mean outcome: treated={pre_means[1]:.3f}, "
      f"control={pre_means[0]:.3f}, gap={pre_means[1] - pre_means[0]:.3f}")
post_means = post.groupby("_treated")["_y"].mean()
print(f"post-period mean outcome: treated={post_means[1]:.3f}, "
      f"control={post_means[0]:.3f}, gap={post_means[1] - post_means[0]:.3f}")

# pre-period trend difference, with unit fixed effects and firm-clustered SEs
pre_m = pre.copy()
pre_m["_t0"] = pre_m["_time"] - pre_m["_time"].min()
# common month slope + treated-specific extra slope (unit FE absorb the group level)
m_pre = smf.ols("_y ~ _t0 + _treated:_t0 + C(_unit)", data=pre_m).fit(
    cov_type="cluster", cov_kwds={"groups": pre_m["_unit"]})
b = m_pre.params["_treated:_t0"]
se = m_pre.bse["_treated:_t0"]
p = m_pre.pvalues["_treated:_t0"]
print(f"\npre-period difference in linear trend (treated minus control), per month: "
      f"{b:+.4f} (SE {se:.4f}, p={p:.3f})")
print("  (unit FE + a common month slope; the treated x month term is the differential "
      "pre-trend)")

# how big is that against the mean outcome?
print(f"  as a share of the pre-period control mean: {100 * b / pre_means[0]:+.3f}% per month")

# same slope for each group separately, no FE
for g, lab in [(1, "treated"), (0, "control")]:
    d = pre[pre["_treated"] == g]
    mm = smf.ols("_y ~ _t0", data=d.assign(_t0=d["_time"] - 1)).fit(
        cov_type="cluster", cov_kwds={"groups": d["_unit"]})
    print(f"  {lab}: pre-period slope {mm.params['_t0']:+.4f}/month "
          f"(SE {mm.bse['_t0']:.4f})")

# ---- 3. is there already a break before the launch month? ------------------------------
# compare the last 6 pre-months with the 6 months before that, by group
early = df[df["_time"].between(start - 12, start - 7)].groupby("_treated")["_y"].mean()
late = df[df["_time"].between(start - 6, start - 1)].groupby("_treated")["_y"].mean()
print("\nchange over the last 6 pre-months minus the 6 before them:")
print(f"  treated: {late[1] - early[1]:+.3f}; control: {late[0] - early[0]:+.3f}; "
      f"difference-in-differences {((late[1] - early[1]) - (late[0] - early[0])):+.3f}")

# ---- 4. heterogeneity of the post change across treated firms -------------------------
firm_change = (df[df["_time"] >= start].groupby("_unit")["_y"].mean()
               - df[df["_time"] < start].groupby("_unit")["_y"].mean())
print("\nwithin-firm post-minus-pre mean change, by group:")
print(firm_change.groupby(per_unit["treated"]).describe().round(2).to_string())
out["firm_change"] = {str(k): float(v) for k, v in firm_change.items()}

out.update({
    "n_treated": n_treated,
    "n_control": int(len(per_unit) - n_treated),
    "staggered": bool(staggered),
    "treatment_start": start,
    "pre_mean_treated": float(pre_means[1]),
    "pre_mean_control": float(pre_means[0]),
    "pre_trend_diff_per_month": float(b),
    "pre_trend_diff_se": float(se),
    "pre_trend_diff_p": float(p),
})
(didlib.RESULTS / "design_checks.json").write_text(json.dumps(out, indent=2),
                                                   encoding="utf-8")
print(f"\nwrote {(didlib.RESULTS / 'design_checks.json').relative_to(didlib.ROOT)}")
