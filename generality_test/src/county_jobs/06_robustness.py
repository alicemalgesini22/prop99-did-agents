"""06: robustness -- remove each cohort's linear differential pre-trend.

Main threat in the data: the raw cohort means drift apart at different rates
and the estimated effect keeps growing with years since treatment, so a
differential trend could be mistaken for an effect. For each cohort I fit a
linear trend to (cohort mean - never-treated mean) over the pre-treatment
years and subtract its extrapolation from ATT(g,t).
"""
import json
import sys
from importlib import import_module

import numpy as np
import pandas as pd

u = import_module("00_cs_utils")

OUT = "results/county_jobs"
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


def detrended(D, cohort, periods, groups, never_mask, ns):
    pts = {}
    for g in groups:
        gi = cohort == g
        pre = [t for t in periods if t < g]
        jpre = [periods.index(t) for t in pre]
        diff = np.array([D[gi, j].mean() - D[never_mask, j].mean() for j in range(len(periods))])
        slope, icpt = np.polyfit(pre, diff[jpre], 1)
        fit = icpt + slope * np.array(periods, dtype=float)
        base = periods.index(g - 1)
        for t in periods:
            if t == g - 1:
                continue
            j = periods.index(t)
            pts[(g, t)] = float((diff[j] - diff[base]) - (fit[j] - fit[base]))
    return pts


D = Y.values.astype(float)
cohort = group_of.loc[Y.index].values
never_mask = np.isnan(cohort)
pts = detrended(D, cohort, periods, groups, never_mask, ns)
att_dt = u.agg_overall_pts(pts, groups, ns)
print("[robustness] detrended ATT(g,t), cohort means:")
for g in groups:
    ts = [t for (gg, t) in pts if gg == g and t >= g]
    print(f"   cohort {g}: {np.mean([pts[(g, t)] for t in ts]):+.3f}")
print(f"[robustness] detrended overall ATT = {att_dt:+.3f}")

main = pd.read_csv(f"{OUT}/main_estimates.csv")
att = float(main.loc[main["estimator"].str.startswith("CS ATT (cohort"), "estimate"].iloc[0])
print(f"[robustness] main ATT = {att:+.3f}; change = {att_dt - att:+.3f} "
      f"({100*(att_dt-att)/att:+.0f}% of the main estimate)")

# bootstrap SE of the detrended estimate
draws, skipped = u.boot_indices(cohort, groups, never_mask, 999, 20261125)
boot = []
for b in draws:
    cb = cohort[b]
    p = detrended(D[b], cb, periods, groups, np.isnan(cb), {g: int((cb == g).sum()) for g in groups})
    boot.append(u.agg_overall_pts(p, groups, {g: int((cb == g).sum()) for g in groups}))
boot = np.array(boot)
print(f"[robustness] bootstrap SE {boot.std(ddof=1):.3f}, 95% CI "
      f"[{np.quantile(boot,0.025):+.3f}, {np.quantile(boot,0.975):+.3f}] "
      f"({len(boot)} draws, {skipped} skipped)")

pd.DataFrame([{"cohort": k[0], "year": k[1], "att_detrended": v}
              for k, v in pts.items()]).to_csv(f"{OUT}/robustness_detrended_cells.csv", index=False)
pd.DataFrame([{"estimator": "CS ATT detrended (cohort-size weighted, post)",
               "estimate": att_dt, "boot_se": float(boot.std(ddof=1)),
               "change_vs_main": att_dt - att,
               "pct_change": 100 * (att_dt - att) / att}]).to_csv(
    f"{OUT}/robustness_detrended.csv", index=False)
print(f"[saved] {OUT}/robustness_detrended.csv, {OUT}/robustness_detrended_cells.csv")
