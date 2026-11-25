"""03 - Design checks: treated count, treatment timing, group comparability."""
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

rep: dict = {}
treated_units = df.loc[df["treated"] == 1, unit].unique()
control_units = df.loc[df["treated"] == 0, unit].unique()
rep["n_treated_units"] = int(len(treated_units))
rep["n_control_units"] = int(len(control_units))
rep["share_treated"] = float(len(treated_units) / df[unit].nunique())
print(f"treated units: {len(treated_units)}, control units: {len(control_units)}")

# treatment timing: no adoption-date column exists, so state what is and is not checkable
rep["timing_column_exists"] = False
rep["treatment_start"] = start
rep["timing_source"] = cfg["treatment_start_source"]
rep["staggered"] = "not detectable: no adoption-date column; single start assumed from README"
print(f"treatment start used: {start} (source: README; no timing column in data)")

# observations per group per period (balanced check by group)
per = df.groupby(["treated", time], observed=True).size().unstack(time)
print("\nunits observed per group-period (should equal group sizes):")
print(per.to_string())
rep["units_per_group_period_ok"] = bool(
    (per.loc[1] == len(treated_units)).all() and (per.loc[0] == len(control_units)).all()
)

# pre-period balance: level difference
pre = df[df[time] < start]
post = df[df[time] >= start]
rep["pre_mean_treated"] = float(pre.loc[pre["treated"] == 1, outcome].mean())
rep["pre_mean_control"] = float(pre.loc[pre["treated"] == 0, outcome].mean())
rep["pre_level_gap"] = rep["pre_mean_treated"] - rep["pre_mean_control"]
rep["post_mean_treated"] = float(post.loc[post["treated"] == 1, outcome].mean())
rep["post_mean_control"] = float(post.loc[post["treated"] == 0, outcome].mean())
print(f"\npre-period mean: treated {rep['pre_mean_treated']:.2f}, control {rep['pre_mean_control']:.2f}, "
      f"gap {rep['pre_level_gap']:.2f}")
print(f"post-period mean: treated {rep['post_mean_treated']:.2f}, control {rep['post_mean_control']:.2f}")

# pre-trend test: treated x linear time, unit FE + year FE, pre-period only
pre = pre.copy()
pre["trend"] = pre[time] - start
pre["treat_trend"] = pre["treated"] * pre["trend"]
m = smf.ols(f"{outcome} ~ treat_trend + C({unit}) + C({time})", data=pre).fit(
    cov_type="cluster", cov_kwds={"groups": pre[unit]})
rep["pretrend_test"] = {
    "coef_treated_x_trend": float(m.params["treat_trend"]),
    "se": float(m.bse["treat_trend"]),
    "p": float(m.pvalues["treat_trend"]),
    "n_obs": int(m.nobs),
    "sample": f"periods {int(pre[time].min())}-{int(pre[time].max())} only",
    "cluster": unit,
}
print(f"\npre-trend test (treated x year, pre-period only): "
      f"{rep['pretrend_test']['coef_treated_x_trend']:.3f} "
      f"(SE {rep['pretrend_test']['se']:.3f}, p={rep['pretrend_test']['p']:.3f})")

# differential change in enrolment? (diagnostic only; enrolment is NOT a control)
enr = cfg["diagnostic_columns"]["enrolment"]
pre_s = df[df[time] < start].groupby("treated", observed=True)[enr].mean()
post_s = df[df[time] >= start].groupby("treated", observed=True)[enr].mean()
rep["students_did_diagnostic"] = float((post_s[1] - pre_s[1]) - (post_s[0] - pre_s[0]))
rep["enrolment_column"] = enr
rep["enrolment_mean_overall"] = float(df[enr].mean())
rep["enrolment_min"] = float(df[enr].min())
rep["enrolment_max"] = float(df[enr].max())
print(f"diagnostic, not a control: DiD in mean {enr} = {rep['students_did_diagnostic']:.1f} "
      f"(overall mean {rep['enrolment_mean_overall']:.0f}, range "
      f"{rep['enrolment_min']:.0f}-{rep['enrolment_max']:.0f})")

# within-group outcome dispersion (relevant for power)
rep["sd_within_unit"] = float(
    df.assign(dm=df[outcome] - df.groupby(unit)[outcome].transform("mean"))["dm"].std()
)
print(f"within-unit SD of outcome: {rep['sd_within_unit']:.2f}")

rep["few_treated_units_note"] = (
    f"{len(treated_units)} treated units is above the ~5 threshold, so cluster-robust SEs "
    "by unit are the primary inference, but 20 clusters is still modest; a placebo/"
    "randomisation-inference test over units is reported as a cross-check."
)
with open(OUT / "design_checks.json", "w", encoding="utf-8") as fh:
    json.dump(rep, fh, indent=2)
print("\nwrote", OUT / "design_checks.json")
