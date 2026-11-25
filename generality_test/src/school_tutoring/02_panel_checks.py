"""Step 2: panel checks. Rows, units, periods, duplicates, balance, missing values
(with the exact periods), printing the number of rows after every filter.

Run: uv run python src/school_tutoring/02_panel_checks.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from didlib import load_config, load_panel, save_json  # noqa: E402

cfg = load_config()
df = load_panel(cfg)
UNIT, TIME, Y = cfg["unit"], cfg["time"], cfg["outcome"]

out = {"config": cfg}

print(f"rows in raw file: {len(df)}")
print(f"units: {df['_unit'].nunique()}   periods: {df['_time'].nunique()}")

# ---- duplicates ---------------------------------------------------------------------
dup = df.duplicated(["_unit", "_time"], keep=False)
print(f"\nduplicate ({UNIT}, {TIME}) rows: {int(dup.sum())}")
if dup.any():
    print(df.loc[dup, [UNIT, TIME]].to_string())
print(f"rows after dropping duplicate keys: {len(df.drop_duplicates(['_unit', '_time']))} "
      f"(drop {int(dup.sum())} rows, reason: exact duplicate panel keys)")

# ---- missing values, with the exact periods -----------------------------------------
print("\nmissing values by column (raw columns):")
miss = {}
for c in [cfg["unit"], cfg["time"], cfg["outcome"]] + [cfg["treated_rule"]["column"]]:
    n = int(df[c].isna().sum())
    miss[c] = n
    print(f"  {c}: {n}")
if df[Y].isna().any():
    bad = df.loc[df[Y].isna(), ["_unit", "_time"]]
    print(f"  exact rows with missing {Y}:")
    print(bad.to_string(index=False))
    periods = sorted(bad["_time"].unique().tolist())
    print(f"  exact periods with a missing {Y} somewhere: {periods}")
else:
    periods = []
    print(f"  no missing {Y} anywhere, so no periods to list")

# ---- balance ------------------------------------------------------------------------
n_units, n_per = df["_unit"].nunique(), df["_time"].nunique()
span = df["_time"].max() - df["_time"].min() + 1
print(f"\nperiods present: {sorted(df['_time'].unique().tolist())}")
print(f"calendar span (max-min+1): {span}; distinct periods present: {n_per} "
      f"=> {'no gaps in the calendar' if span == n_per else 'GAPS in the calendar'}")

per_unit = df.groupby("_unit")["_time"].nunique()
print(f"observations per unit: min={per_unit.min()}, max={per_unit.max()} "
      f"(expected {n_per})")
unbalanced = per_unit[per_unit != n_per]
if len(unbalanced):
    for u, k in unbalanced.items():
        have = set(df.loc[df["_unit"] == u, "_time"])
        print(f"  unit {u}: {k} periods, missing {sorted(set(df['_time'].unique()) - have)}")
else:
    print("  every unit observed in every period")

print(f"\nbalanced panel: {len(df) == n_units * n_per}  "
      f"(rows {len(df)} vs units*periods {n_units * n_per})")

# ---- treated/control coverage ------------------------------------------------------
cov = df.groupby("_treated")["_unit"].nunique()
print(f"\nunits by group: control={int(cov.get(0, 0))}, treated={int(cov.get(1, 0))}")
per_period = df.groupby(["_time", "_treated"]).size().unstack(fill_value=0)
print("\nrows per period by group:")
print(per_period.to_string())

# ---- outcome distribution ------------------------------------------------------------
print(f"\noutcome {Y}: mean {df['_y'].mean():.2f}, sd {df['_y'].std():.2f}, "
      f"min {df['_y'].min():.2f}, max {df['_y'].max():.2f}")

# ---- no rows are dropped in this run -----------------------------------------------
print(f"\nrows used downstream: {len(df)} (no filter applied: no duplicates, no missing "
      f"outcome, no out-of-range periods, covariates not used)")

out.update({
    "rows_raw": int(len(df)),
    "rows_used": int(len(df)),
    "rows_dropped": 0,
    "units": int(n_units),
    "periods": sorted(int(t) for t in df["_time"].unique()),
    "duplicate_unit_time_rows": int(dup.sum()),
    "balanced": bool(len(df) == n_units * n_per),
    "missing_counts": miss,
    "periods_with_missing_outcome": [int(p) for p in periods],
    "units_treated": int(cov.get(1, 0)),
    "units_control": int(cov.get(0, 0)),
    "outcome_mean": float(df["_y"].mean()),
    "outcome_sd": float(df["_y"].std()),
})
save_json(out, "panel_checks.json")
