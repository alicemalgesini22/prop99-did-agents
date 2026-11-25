"""Step 3: design checks. How many treated units, is timing staggered, how many clusters,
which inference, and is there a pre-treatment differential trend (the main threat)?

Run: uv run python src/school_tutoring/03_design_checks.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from didlib import load_config, load_panel, save_json  # noqa: E402

cfg = load_config()
df = load_panel(cfg)
UNIT, TIME = cfg["unit"], cfg["time"]
START = cfg["treatment_start"]

out = {}

# ---- treated units ------------------------------------------------------------------
treated = df.loc[df["_treated"] == 1, "_unit"].nunique()
control = df.loc[df["_treated"] == 0, "_unit"].nunique()
print(f"treated units: {treated}")
print(f"control units: {control}")
print(f"clusters available (by {UNIT}): {df['_unit'].nunique()}")
print(f"few-treated rule (<5): {treated < 5} -> "
      f"{'placebo inference' if treated < 5 else 'clustered SE by unit is usable'}")

# ---- timing -------------------------------------------------------------------------
# The flag is constant within unit, so observed timing is uniform by construction.
# What the data can show is whether outcomes break at the documented date.
print(f"\ndistinct documented treatment starts: 1 ({TIME} = {START})")
print("staggered timing: NO (single common start date). With a single start date and a "
      "balanced panel, two-way FE is the group-time average treatment effect and the "
      "staggered-adoption (Goodman-Bacon / Callaway-Sant'Anna) bias does not arise.")
print(f"pre periods: {int((df['_time'] < START).sum() / df['_unit'].nunique())} per unit, "
      f"post periods: {int((df['_time'] >= START).sum() / df['_unit'].nunique())} per unit")

# ---- pre-treatment differential trend -------------------------------------------------
# Regress y on unit FE, time FE and treated x (year - first pre year) using pre years only.
pre = df[df["_time"] < START].copy()
pre["_t"] = pre["_time"] - pre["_time"].min()
m_pre = smf.ols("_y ~ C(_unit) + C(_time) + _treated:_t", data=pre).fit(
    cov_type="cluster", cov_kwds={"groups": pre["_unit"]})
b_pre = float(m_pre.params["_treated:_t"])
se_pre = float(m_pre.bse["_treated:_t"])
p_pre = float(m_pre.pvalues["_treated:_t"])
print(f"\npre-period (years < {START}) treated x linear-trend coefficient: "
      f"{b_pre:.3f} points/year (cluster SE {se_pre:.3f}, p={p_pre:.3f})")
print(f"  rows used: {len(pre)} (pre-treatment years only)")

# group mean levels before treatment, and mean within-school slope before treatment
lvl = pre.groupby("_treated")["_y"].mean()
slopes = (pre.groupby(["_unit", "_treated"])
             .apply(lambda d: np.polyfit(d["_time"], d["_y"], 1)[0], include_groups=False)
             .rename("slope").reset_index())
sl = slopes.groupby("_treated")["slope"].agg(["mean", "std", "count"])
print("\npre-period mean level by group:")
print(lvl.rename(index={0: "control", 1: "treated"}).to_string())
print("\npre-period within-school linear slope (points/year) by group:")
print(sl.rename(index={0: "control", 1: "treated"}).round(3).to_string())

# ---- inference choice ----------------------------------------------------------------
print(f"\ninference: {treated} treated units and {df['_unit'].nunique()} clusters "
      f"-> standard errors clustered by {UNIT} (primary).")
print("secondary, not required by the plan: randomisation inference that re-assigns the "
      "20 treated labels across the 60 schools (reported in 07_inference.py).")

out.update({
    "treated_units": int(treated),
    "control_units": int(control),
    "clusters": int(df["_unit"].nunique()),
    "few_treated_rule_triggered": bool(treated < 5),
    "staggered_timing": False,
    "distinct_treatment_starts": 1,
    "treatment_start": int(START),
    "pre_periods_per_unit": int((df["_time"] < START).sum() / df["_unit"].nunique()),
    "post_periods_per_unit": int((df["_time"] >= START).sum() / df["_unit"].nunique()),
    "pre_trend_test": {"coef_points_per_year": b_pre, "cluster_se": se_pre,
                       "p_value": p_pre, "rows": int(len(pre)),
                       "spec": "y ~ unit FE + year FE + treated x (year-2012), pre years only"},
    "pre_mean_level": {"control": float(lvl.get(0)), "treated": float(lvl.get(1))},
    "pre_mean_within_slope": {
        "control": float(sl.loc[0, "mean"]), "control_sd": float(sl.loc[0, "std"]),
        "treated": float(sl.loc[1, "mean"]), "treated_sd": float(sl.loc[1, "std"])},
    "inference_primary": f"cluster by {UNIT}",
    "inference_secondary": "randomisation inference over treated labels",
})
save_json(out, "design_checks.json")
