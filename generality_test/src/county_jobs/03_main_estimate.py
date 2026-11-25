"""03: main estimate.

Main specification: staggered adoption, so the main estimate is the
Callaway-Sant'Anna group-time ATT (never-treated counties as controls),
aggregated over post-treatment cells with cohort-size weights.
Also reported: TWFE (treated x post + county FE + year FE, cluster by county)
and the simple 2x2 difference of means per cohort, as cross-checks.
"""
import json
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, "src/county_jobs")
from importlib import import_module

u = import_module("00_cs_utils")

OUT = "results/county_jobs"
cfg = json.load(open(f"{OUT}/did_config.json"))
unit, time, y = cfg["unit"], cfg["time"], cfg["outcome"]
tcol = cfg["treatment_start"]["column"]

df = pd.read_csv(f"{OUT}/panel_analysis.csv")
print(f"[rows] panel: {len(df)}")
Y = u.wide(df, unit, time, y)
group_of = u.group_map(df, unit, tcol)
never = list(group_of[group_of.isna()].index)
groups = sorted(int(g) for g in group_of.dropna().unique())
periods = list(Y.columns)
ns = {g: int((group_of == g).sum()) for g in groups}
print(f"[design] units={len(Y)} periods={len(periods)} cohorts={groups} "
      f"never-treated={len(never)} cohort sizes={ns}")

# ---------------- Callaway-Sant'Anna, never-treated controls ---------------
cells = u.all_cells(Y, group_of, groups, never, periods)
pts = {k: v[0] for k, v in cells.items()}
att = u.agg_overall_pts(pts, groups, ns, post_only=True)
print("\n[CS] cohort-specific ATT (mean over post periods):")
for g in groups:
    ts = [t for (gg, t) in pts if gg == g and t >= g]
    print(f"   cohort {g}: {np.mean([pts[(g, t)] for t in ts]):+.3f}  ({len(ts)} post periods)")
post_cells = [v[0] for k, v in cells.items() if k[1] >= k[0]]
print(f"[CS] main ATT (cohort-size weighted, post periods) = {att:+.3f}")
print(f"[CS] unweighted mean over all {len(post_cells)} post cells = "
      f"{np.mean(post_cells):+.3f}")

# ---------------- TWFE ----------------------------------------------------
df["D"] = ((df["treated"] == 1) & (df["post"] == 1)).astype(int)
twfe = smf.ols(f"{y} ~ D + C({unit}) + C({time})", data=df).fit(
    cov_type="cluster", cov_kwds={"groups": df[unit]})
b, se = twfe.params["D"], twfe.bse["D"]
print(f"\n[TWFE] treated x post = {b:+.3f}  cluster SE = {se:.3f}  "
      f"95% CI [{b-1.96*se:+.3f}, {b+1.96*se:+.3f}]  N={int(twfe.nobs)}")

# ---------------- simple 2x2 per cohort -----------------------------------
rows = []
for g in groups:
    pre, post = [t for t in periods if t < g], [t for t in periods if t >= g]
    gi = df[df[tcol] == g]
    ni = df[df[tcol].isna()]
    est = ((gi[gi[time].isin(post)][y].mean() - gi[gi[time].isin(pre)][y].mean())
           - (ni[ni[time].isin(post)][y].mean() - ni[ni[time].isin(pre)][y].mean()))
    rows.append({"cohort": g, "n_pre_years": len(pre), "n_post_years": len(post),
                 "two_by_two": est})
    print(f"[2x2] cohort {g} vs never-treated: {est:+.3f} "
          f"(pre {pre[0]}-{pre[-1]}, post {post[0]}-{post[-1]})")
two = pd.DataFrame(rows)
print(f"[2x2] mean over cohorts = {two['two_by_two'].mean():+.3f}")

res = pd.DataFrame([{"estimator": "CS ATT (cohort-size weighted, post)",
                     "estimate": att},
                    {"estimator": "CS ATT (unweighted mean of post cells)",
                     "estimate": float(np.mean(post_cells))},
                    {"estimator": "TWFE treated x post", "estimate": b,
                     "cluster_se": se}])
res.to_csv(f"{OUT}/main_estimates.csv", index=False)
two.to_csv(f"{OUT}/two_by_two.csv", index=False)
pd.DataFrame([{"cohort": k[0], "year": k[1], "att": v[0], "se": v[1]}
              for k, v in cells.items()]).to_csv(f"{OUT}/att_gt.csv", index=False)
print(f"\n[saved] {OUT}/main_estimates.csv, {OUT}/two_by_two.csv, {OUT}/att_gt.csv")
