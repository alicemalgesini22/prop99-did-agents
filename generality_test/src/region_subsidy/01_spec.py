"""01 - Specification: decide the roles of the columns and write did_config.json.

Roles come from data/README_region_subsidy.md and are checked against the raw
data before anything is estimated. Nothing here estimates a treatment effect.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from didlib import save_json

DATA = "data/raw/region_subsidy.csv"
README = "data/README_region_subsidy.md"

# Names as given in the data description (README table).
UNIT, TIME, OUTCOME, GROUP_FLAG = "region_id", "quarter", "investment", "subsidy_region"
TREATMENT_START = 13  # README: "Some regions received an investment subsidy from quarter 13"

df = pd.read_csv(DATA)
print(f"rows: {len(df)}, columns: {list(df.columns)}")

# --- check each role against the data ------------------------------------
checks = {}
checks["unit_candidates"] = [c for c in df.columns if df[c].nunique() == 30]
checks["time_candidates"] = [c for c in df.columns if df[c].nunique() == 24]
checks["group_flag_values"] = sorted(map(str, df[GROUP_FLAG].dropna().unique()))
checks["group_flag_is_bool"] = str(df[GROUP_FLAG].dtype) == "bool"
checks["group_flag_constant_within_unit"] = bool(
    (df.groupby(UNIT)[GROUP_FLAG].nunique() == 1).all()
)
checks["one_row_per_unit_time"] = bool(
    not df.duplicated([UNIT, TIME]).any()
)
checks["outcome_numeric"] = bool(pd.api.types.is_numeric_dtype(df[OUTCOME]))
checks["outcome_missing"] = int(df[OUTCOME].isna().sum())
checks["time_values"] = sorted(int(v) for v in df[TIME].unique())
checks["time_gaps"] = bool(
    sorted(df[TIME].unique()) == list(range(df[TIME].min(), df[TIME].max() + 1))
)
# A ready-made "post"/"after" column must not be trusted or even present here.
checks["columns_resembling_post"] = [
    c for c in df.columns if any(k in c.lower() for k in ("post", "after", "treat_time", "first_treat"))
]

treated_units = sorted(int(u) for u in df.loc[df[GROUP_FLAG], UNIT].unique())
control_units = sorted(int(u) for u in df.loc[~df[GROUP_FLAG], UNIT].unique())
checks["n_treated_units"] = len(treated_units)
checks["n_control_units"] = len(control_units)
checks["treated_units"] = treated_units
checks["control_units_excluded_from_spec"] = True

# The data carry no treatment-date column, so the start period is the README's
# "from quarter 13". Sanity check: quarter 13 is inside the observed range and
# leaves at least two pre and two post periods for every unit.
checks["treatment_start_inside_panel"] = int(df[TIME].min()) < TREATMENT_START <= int(df[TIME].max())
checks["pre_periods_per_unit"] = len([q for q in checks["time_values"] if q < TREATMENT_START])
checks["post_periods_per_unit"] = len([q for q in checks["time_values"] if q >= TREATMENT_START])
checks["same_start_for_all_treated"] = True  # by construction: only one start date exists in the data

cfg = {
    "data_path": DATA,
    "data_description": README,
    "unit": UNIT,
    "time": TIME,
    "outcome": OUTCOME,
    "outcome_units": "million euro",
    "group_flag_column": GROUP_FLAG,
    "treated_rule": f"{GROUP_FLAG} == True",
    "treated_units": treated_units,
    "treatment_start": TREATMENT_START,
    "treatment_start_source": "README_region_subsidy.md: 'received an investment subsidy from quarter 13'",
    "controls": [],
    "cluster": UNIT,
    "n_units": int(df[UNIT].nunique()),
    "n_periods": int(df[TIME].nunique()),
    "design": "two-way fixed effects DiD, region and quarter FE, all rows, no covariates, "
              "uniform treatment timing (single start quarter)",
    "roles_justification": {
        "unit": "region_id takes values 1-30 and is constant across quarters; README calls it the region identifier",
        "time": "quarter takes values 1-24 with no gaps; README calls it the period",
        "outcome": "investment, million euro, float, never empty; README question is about private investment",
        "treatment": "subsidy_region is the only treatment-related column; it is boolean, constant within region, "
                     "and splits 10 treated from 20 control regions",
        "timing": "no treatment-date column exists in the data; the start quarter comes from the README text, "
                  "which fixes a single start quarter for all treated regions",
        "controls": "plan asks for no covariates",
    },
    "checks": checks,
}

save_json(cfg, "did_config.json")
save_json(checks, "spec_checks.json")
print(json.dumps({k: cfg[k] for k in ("unit", "time", "outcome", "treated_units",
                                      "treatment_start", "cluster")}, indent=2, default=str))
print("wrote results/region_subsidy/did_config.json")
