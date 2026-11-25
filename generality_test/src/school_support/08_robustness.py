"""08 - Robustness.

Threats found in the data (see 03/06):
  * timing is not verifiable (no adoption-date column), and a phase-in would bias a
    single 2017 break;
  * differential trend: treated schools start ~10 points lower and grow slightly
    differently in levels, so a treated-specific trend is the key alternative;
  * 2020-2021 are unusual years for schools (COVID-era disruption) and may be noise.
Checks: treated-group linear trend, unit-specific linear trends for treated units,
later/earlier start dates, and dropping 2020-2021.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

import didlib as L

cfg = L.load_config()
OUT = Path("results") / L.RUN_DIR
unit, time, outcome = cfg["unit"], cfg["time"], cfg["outcome"]
start = cfg["treatment_start"]

df = L.add_treatment_columns(L.read_panel(cfg), cfg)
print("rows:", len(df))
rows = []

# baseline
base = L.twfe(df, cfg, cluster=cfg["cluster"], label="baseline_2017")
rows.append(base)
print(f"baseline: {base['coef']:.3f} (SE {base['se']:.3f})")

# ---- (1) treated-group-specific linear trend ------------------------------
d1 = df.assign(trend=df[time] - (start - 1), treat_trend=df["treated"] * (df[time] - (start - 1)))
r1 = L.twfe(d1, cfg, extra_terms=["treat_trend"], cluster=cfg["cluster"],
            label="treated_group_linear_trend")
rows.append(r1)
print(f"treated-group linear trend: {r1['coef']:.3f} (SE {r1['se']:.3f}) "
      f"[trend coef {r1.get('x','')}]")
m1 = smf.ols(f"{outcome} ~ treat_post + treat_trend + C({unit}) + C({time})", data=d1).fit(
    cov_type="cluster", cov_kwds={"groups": d1[unit]})
print(f"   trend coefficient itself: {m1.params['treat_trend']:.3f} "
      f"(SE {m1.bse['treat_trend']:.3f}, p={m1.pvalues['treat_trend']:.3f})")
r1["trend_coef"] = float(m1.params["treat_trend"])
r1["trend_se"] = float(m1.bse["treat_trend"])
r1["trend_p"] = float(m1.pvalues["treat_trend"])

# ---- (2) unit-specific linear trends for the treated units ---------------
d2 = df.copy()
trend_cols = []
for u in cfg["treated_units"]:
    c = f"trend_u{u}"
    d2[c] = ((d2[unit] == u).astype(int) * (d2[time] - (start - 1)))
    trend_cols.append(c)
print(f"\nunit-specific trends added: {len(trend_cols)} terms (absorb a lot of the post contrast)")
r2 = L.twfe(d2, cfg, extra_terms=trend_cols, cluster=cfg["cluster"],
            label="treated_unit_specific_trends")
rows.append(r2)
print(f"treated unit-specific linear trends: {r2['coef']:.3f} (SE {r2['se']:.3f}), "
      f"n_obs={r2['n_obs']}")

# provenance for the claim that the two trend specs give an identical coefficient:
# the models are genuinely different (more parameters, lower RSS) but the residualised
# treatment indicator is unchanged.
m2 = smf.ols(f"{outcome} ~ treat_post + " + " + ".join(trend_cols)
             + f" + C({unit}) + C({time})", data=d2).fit()
trend_diag = {
    "group_trend": {"rank": int(np.linalg.matrix_rank(m1.model.exog)), "ssr": float(m1.ssr),
                    "df_resid": float(m1.df_resid), "coef": float(r1["coef"])},
    "unit_trends": {"rank": int(np.linalg.matrix_rank(m2.model.exog)), "ssr": float(m2.ssr),
                    "df_resid": float(m2.df_resid), "coef": float(r2["coef"])},
    "rank_difference": int(np.linalg.matrix_rank(m2.model.exog) - np.linalg.matrix_rank(m1.model.exog)),
    "coef_identical": bool(np.isclose(r1["coef"], r2["coef"], atol=1e-10)),
    "note": ("with one common start date the per-school treated trends are orthogonal to the "
             "pooled post contrast, so they change the SE but not the coefficient"),
}
print(f"trend-spec comparison: rank {trend_diag['group_trend']['rank']} vs "
      f"{trend_diag['unit_trends']['rank']}, SSR {trend_diag['group_trend']['ssr']:.1f} vs "
      f"{trend_diag['unit_trends']['ssr']:.1f}, coef identical={trend_diag['coef_identical']}")

# ---- (3) different assumed start dates -----------------------------------
for s in [2018, 2019]:
    d3 = df.copy()
    d3["treat_post"] = d3["treated"] * (d3[time] >= s).astype(int)
    r = L.twfe(d3, cfg, cluster=cfg["cluster"], label=f"start_{s}")
    rows.append(r)
    print(f"start {s}: {r['coef']:.3f} (SE {r['se']:.3f})")

# ---- (4) drop 2020-2021 --------------------------------------------------
d4 = df[df[time] <= 2019].copy()
print(f"[drop 2020-2021] rows={len(d4)} of {len(df)} (reason: COVID-era years, sensitivity)")
r4 = L.twfe(d4, cfg, cluster=cfg["cluster"], label="drop_2020_2021")
rows.append(r4)
print(f"drop 2020-2021: {r4['coef']:.3f} (SE {r4['se']:.3f})")

# ---- (5) drop the 2017 phase-in year ------------------------------------
d5 = df[df[time] != 2017].copy()
print(f"[drop 2017] rows={len(d5)} of {len(df)} (reason: first treatment year may be partial)")
r5 = L.twfe(d5, cfg, cluster=cfg["cluster"], label="drop_2017")
rows.append(r5)
print(f"drop 2017: {r5['coef']:.3f} (SE {r5['se']:.3f})")

# ---- (6) leave-one-treated-unit-out -------------------------------------
loo = []
for u in cfg["treated_units"]:
    d = df[df[unit] != u]
    r = L.twfe(d, cfg, cluster=cfg["cluster"], label=f"drop_treated_{u}")
    loo.append({"dropped_unit": int(u), "coef": r["coef"], "se": r["se"], "n_obs": r["n_obs"]})
loo_df = pd.DataFrame(loo)
loo_df.to_csv(OUT / "robustness_leave_one_out.csv", index=False)
print(f"\nleave-one-treated-unit-out: coef range [{loo_df['coef'].min():.3f}, "
      f"{loo_df['coef'].max():.3f}] across {len(loo_df)} drops")

tab = pd.DataFrame(rows)
tab["change_vs_baseline"] = tab["coef"] - base["coef"]
tab.to_csv(OUT / "robustness.csv", index=False)
with open(OUT / "robustness.json", "w", encoding="utf-8") as fh:
    json.dump({"specs": rows, "leave_one_out": loo, "trend_spec_comparison": trend_diag,
               "note": "all cluster-robust by school; controls: none"}, fh, indent=2)
print("\nwrote robustness.csv / robustness.json / robustness_leave_one_out.csv")
print(tab[["label", "coef", "se", "p", "n_obs", "change_vs_baseline"]].round(3).to_string(index=False))
