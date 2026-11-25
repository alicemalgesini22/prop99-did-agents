"""01 - Specification.

Reads the data description's claims (README) and checks every role against the
data before writing results/school_support/did_config.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import didlib as L

DATA = "data/raw/school_tutoring.csv"
OUT = Path("results") / L.RUN_DIR
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA)
print("shape:", df.shape)
print("columns:", list(df.columns))
print(df.dtypes.to_string())
print()

# --- role checks -----------------------------------------------------------
# unit
for cand in ["school_id", "school", "unit_id", "id"]:
    if cand in df.columns:
        unit = cand
        break
else:
    raise SystemExit("no unit column found")
# time
for cand in ["year", "period", "date"]:
    if cand in df.columns:
        time = cand
        break
else:
    raise SystemExit("no time column found")
# outcome: numeric, never empty (README)
num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c not in (unit, time)]
print("candidate numeric outcome columns:", num_cols)
outcome = next((c for c in ["reading_score", "test_score", "score", "outcome"] if c in num_cols), None)
if outcome is None:
    raise SystemExit("no outcome column found")
assert outcome in num_cols

print("\nmissing per column:")
print(df.isna().sum().to_string())
print(f"\nunit: {unit}  -> {df[unit].nunique()} unique, range {df[unit].min()}-{df[unit].max()}")
print(f"time: {time}  -> {df[time].nunique()} unique, {df[time].min()}-{df[time].max()}")
print(f"outcome: {outcome} -> min {df[outcome].min():.2f}, max {df[outcome].max():.2f}, "
      f"mean {df[outcome].mean():.2f}, missing {df[outcome].isna().sum()}")

# treatment group flag: a boolean column that is constant within unit (a group flag,
# not a post indicator). Found from the data's dtypes rather than assumed by name.
bool_const = [c for c in df.columns
              if pd.api.types.is_bool_dtype(df[c]) and df.groupby(unit)[c].nunique().max() == 1]
print("\nboolean columns constant within unit:", bool_const)
flag_col = bool_const[0] if bool_const else next(
    (c for c in ["tutoring_school", "treated", "treatment"] if c in df.columns), None)
if flag_col is None:
    raise SystemExit("no treatment-group flag column found")
print(f"\n{flag_col} dtype={df[flag_col].dtype}, values={sorted(df[flag_col].unique().tolist())}")
n_flag_per_unit = df.groupby(unit)[flag_col].nunique()
print("units with a flag that varies within unit:", int((n_flag_per_unit > 1).sum()))
treated_units = sorted(df.loc[df[flag_col].astype(bool), unit].unique().tolist())
control_units = sorted(df.loc[~df[flag_col].astype(bool), unit].unique().tolist())
print(f"treated units ({len(treated_units)}): {treated_units}")
print(f"control units ({len(control_units)}): {control_units}")
print("overlap:", set(treated_units) & set(control_units))

# is there any column that could carry treatment timing?
print("\ncolumns that are constant within unit:",
      [c for c in df.columns if df.groupby(unit)[c].nunique().max() == 1])
print("all columns:", list(df.columns))
print("-> no adoption-date / staggered-timing column exists in the data.")
print("   treatment_start must therefore come from the data description "
      "('introduced ... from the 2017 school year'), not from a column. "
      "It is NOT verifiable inside the data.")

cfg = {
    "data_path": DATA,
    "unit": unit,
    "time": time,
    "outcome": outcome,
    "treated_rule": f"{flag_col} == True (constant within unit in every row)",
    "treated_flag_column": flag_col,
    "diagnostic_columns": {
        k: next((c for c in names if c in num_cols and c != outcome), None)
        for k, names in {"enrolment": ["students", "enrolment", "enrollment"]}.items()
    },
    "treated_units": treated_units,
    "control_units": control_units,
    "treatment_start": 2017,
    "treatment_start_source": (
        "data/README_school_tutoring.md: 'Some schools introduced a tutoring programme "
        "from the 2017 school year'. No timing column exists in the data."
    ),
    "controls": [],
    "cluster": unit,
    "post_definition": f"1[{time} >= 2017], built from treatment_start; no ready-made post column in data",
    "notes": [
        f"{flag_col} is constant within unit, so it is a group flag, not a post indicator; "
        "the interaction treated x post is constructed here.",
        "A ready-made after/post column would have to be zero for controls; none exists, "
        "so nothing is at risk of the post-column trap.",
    ],
}
with open(OUT / "did_config.json", "w", encoding="utf-8") as fh:
    json.dump(cfg, fh, indent=2)
print("\nwrote", OUT / "did_config.json")
print(json.dumps(cfg, indent=2)[:1200])
