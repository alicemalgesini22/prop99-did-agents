"""04: event study (Callaway-Sant'Anna), reference period e = -1.

Saves event-study coefficients, cluster-bootstrap SEs (county resampling,
seed fixed), the bootstrap draws, and the plot.
"""
import json
import sys
from importlib import import_module

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

u = import_module("00_cs_utils")

OUT = "results/county_jobs"
SEED, NBOOT = 20261125, 999
cfg = json.load(open(f"{OUT}/did_config.json"))
unit, time, y = cfg["unit"], cfg["time"], cfg["outcome"]
tcol = cfg["treatment_start"]["column"]

df = pd.read_csv(f"{OUT}/panel_analysis.csv")
Y = u.wide(df, unit, time, y)
group_of = u.group_map(df, unit, tcol)
never = list(group_of[group_of.isna()].index)
groups = sorted(int(g) for g in group_of.dropna().unique())
periods = list(Y.columns)
ns = {g: int((group_of == g).sum()) for g in groups}
es = list(range(min(t - g for g in groups for t in periods), max(t - g for g in groups for t in periods) + 1))

cells = u.all_cells(Y, group_of, groups, never, periods)
pts = {k: v[0] for k, v in cells.items()}
ev = u.agg_event_pts(pts, groups, ns, es)

# ---- bootstrap -----------------------------------------------------------
D = Y.values.astype(float)
cohort = group_of.loc[Y.index].values
never_mask = np.isnan(cohort)
draws, skipped = u.boot_indices(cohort, groups, never_mask, NBOOT, SEED)
print(f"[boot] {len(draws)} usable draws, {skipped} skipped (a cohort or the "
      f"control group disappeared), seed={SEED}")

boot_ev, boot_att = [], []
for b in draws:
    cb = cohort[b]
    p = u.cells_np(D[b], cb, periods, groups, np.isnan(cb))
    boot_ev.append(u.agg_event_pts(p, groups, {g: (cb == g).sum() for g in groups}, es))
    boot_att.append(u.agg_overall_pts(p, groups, {g: int((cb == g).sum()) for g in groups}))
boot_ev = pd.DataFrame(boot_ev)
boot_att = np.array(boot_att)
boot_ev.to_csv(f"{OUT}/bootstrap_event_study.csv", index=False)
pd.DataFrame({"att": boot_att}).to_csv(f"{OUT}/bootstrap_main_att.csv", index=False)

rows = []
for e in es:
    contrib = [g for g in groups if (g, g + e) in pts]
    se = float(boot_ev[e].std(ddof=1))
    rows.append({"event_time": e, "att": ev[e], "boot_se": se,
                 "ci_lo": float(boot_ev[e].quantile(0.025)),
                 "ci_hi": float(boot_ev[e].quantile(0.975)),
                 "n_cohorts": len(contrib), "cohorts": ",".join(map(str, contrib))})
evdf = pd.DataFrame(rows)
evdf.to_csv(f"{OUT}/event_study.csv", index=False)
print(evdf.round(3).to_string(index=False))

# ---- joint test on pre-treatment coefficients e = -4..-2 (all 3 cohorts) --
pre = [-4, -3, -2]
V = boot_ev[pre].cov().values
bvec = np.array([ev[e] for e in pre])
W = float(bvec @ np.linalg.pinv(V) @ bvec)
from scipy.stats import chi2  # noqa: E402
print(f"\n[pre-trend] joint Wald on e=-4,-3,-2: W={W:.2f}, df={len(pre)}, "
      f"p={chi2.sf(W, len(pre)):.4f}")

# ---- plot ----------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 5))
ax.axhline(0, color="black", lw=0.8)
ax.axvline(-0.5, color="grey", ls=":", lw=1)
ax.errorbar(evdf["event_time"], evdf["att"],
            yerr=[evdf["att"] - evdf["ci_lo"], evdf["ci_hi"] - evdf["att"]],
            fmt="o-", ms=4, lw=1, capsize=3)
ax.set_xlabel("years relative to treatment start (reference e = -1)")
ax.set_ylabel("ATT (percentage points)")
ax.set_title("Event study: Callaway-Sant'Anna ATT(g,t), never-treated controls\n"
             "bars = 95% cluster-bootstrap CI (999 draws, seed 20261125)")
fig.tight_layout()
fig.savefig(f"{OUT}/event_study.png", dpi=150)
print(f"[saved] {OUT}/event_study.csv, {OUT}/event_study.png")
