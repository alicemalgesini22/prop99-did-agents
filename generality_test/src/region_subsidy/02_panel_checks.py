"""02 - Panel checks: rows, units, periods, duplicates, balance, missing values."""
from __future__ import annotations

import pandas as pd

from didlib import RESULTS, load_config, read_panel, save_json

cfg = load_config()
df = read_panel(cfg)
unit, time, outcome = cfg["unit"], cfg["time"], cfg["outcome"]

checks: dict = {}
checks["n_rows"] = int(len(df))
checks["n_units"] = int(df[unit].nunique())
checks["n_periods"] = int(df[time].nunique())
checks["unit_range"] = [int(df[unit].min()), int(df[unit].max())]
checks["period_values"] = [int(v) for v in sorted(df[time].unique())]
checks["period_gaps"] = [p for p in range(int(df[time].min()), int(df[time].max()) + 1)
                         if p not in set(df[time])]

# duplicates
dup = df.duplicated([unit, time], keep=False)
print(f"rows with duplicated (unit, time) keys: {int(dup.sum())}")
df = df.loc[~df.duplicated([unit, time], keep="first")].copy()
print(f"rows after dropping duplicate keys: {len(df)}")

# balance
counts = df.groupby(unit)[time].nunique()
checks["rows_per_unit_min_max"] = [int(counts.min()), int(counts.max())]
checks["balanced"] = bool(counts.nunique() == 1 and counts.iloc[0] == checks["n_periods"])
print(f"balanced panel: {checks['balanced']} (each unit has {int(counts.iloc[0])} periods)")

# missing values
missing = df[df[outcome].isna()]
checks["n_missing_outcome"] = int(len(missing))
checks["missing_outcome_periods"] = sorted(int(v) for v in missing[time].unique())
checks["missing_outcome_units"] = sorted(int(v) for v in missing[unit].unique())
print(f"missing {outcome}: {checks['n_missing_outcome']} rows; "
      f"periods {checks['missing_outcome_periods']}; units {checks['missing_outcome_units']}")

# missing unit/time keys themselves
checks["n_missing_unit_or_time"] = int(df[[unit, time]].isna().any(axis=1).sum())
print(f"missing {unit}/{time}: {checks['n_missing_unit_or_time']} rows")

# treatment flag integrity
checks["group_flag_missing"] = int(df[cfg["group_flag_column"]].isna().sum())
checks["group_flag_constant_within_unit"] = bool(
    (df.groupby(unit)[cfg["group_flag_column"]].nunique() == 1).all()
)
print(f"group flag constant within unit: {checks['group_flag_constant_within_unit']}")

# outcome sanity
checks["outcome_min_max"] = [float(df[outcome].min()), float(df[outcome].max())]
checks["outcome_mean_sd"] = [float(df[outcome].mean()), float(df[outcome].std())]

save_json(checks, "panel_checks.json")
with open(RESULTS / "panel_used.csv", "w", encoding="utf-8") as fh:
    df.to_csv(fh, index=False)
print(f"rows used downstream: {len(df)} -> results/region_subsidy/panel_used.csv")
print(pd.Series(checks).to_string())
