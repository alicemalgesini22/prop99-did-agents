"""Step 2: panel checks. Row counts after every filter, duplicates, balance, missing values.

Run: uv run python src/firm_training/02_panel_checks.py
Writes results/firm_training/panel_checks.json
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import didlib  # noqa: E402

cfg = didlib.load_config()
df = didlib.load_panel(cfg)
report = {}

print(f"rows loaded (all rows, no filter yet): {len(df)}")

# ---- duplicates -----------------------------------------------------------------------
dups = df.duplicated(["_unit", "_time"], keep=False)
print(f"duplicate (unit, time) rows: {int(dups.sum())} -> dropped")
df = df[~dups].copy()
print(f"rows after dropping duplicates: {len(df)}")

# ---- missing outcome ------------------------------------------------------------------
miss_y = df["_y"].isna()
print(f"rows with missing outcome: {int(miss_y.sum())} -> dropped "
      f"(reason: outcome is the dependent variable)")
df = df[~miss_y].copy()
print(f"rows after dropping missing outcome: {len(df)}")

# ---- missing unit / time --------------------------------------------------------------
miss_key = df["_unit"].isna() | df["_time"].isna()
print(f"rows with missing unit or time: {int(miss_key.sum())} -> dropped")
df = df[~miss_key].copy()
print(f"rows after dropping missing keys: {len(df)}")

n_units = df["_unit"].nunique()
n_time = df["_time"].nunique()
print(f"\nunits: {n_units}, periods: {n_time}, "
      f"expected balanced rows: {n_units * n_time}, actual: {len(df)}")

# ---- balance --------------------------------------------------------------------------
counts = df.groupby("_unit")["_time"].agg(["count", "nunique", "min", "max"])
unbalanced = counts[(counts["count"] != n_time) | (counts["nunique"] != n_time)]
print(f"units without exactly {n_time} periods: {len(unbalanced)}")
if len(unbalanced):
    print(unbalanced.to_string())
report["unbalanced_units"] = unbalanced.index.tolist()

periods = sorted(df["_time"].unique())
gaps = [p for p in range(min(periods), max(periods) + 1) if p not in periods]
print(f"missing calendar periods between {min(periods)} and {max(periods)}: {gaps}")

# ---- missing values in every other column, exact periods ------------------------------
print("\nmissing values per column:")
raw_columns = list(pd.read_csv(didlib.ROOT / cfg["data_path"], nrows=0).columns)
for col in raw_columns:
    n_missing = int(df[col].isna().sum()) if col in df.columns else None
    if n_missing:
        miss = df.loc[df[col].isna(), ["_time", "_unit"]]
        per_period = miss.groupby("_time").size().to_dict()
        units_affected = sorted(miss["_unit"].unique().tolist())
        print(f"  {col}: {n_missing} missing rows; periods "
              f"{sorted(per_period)} with counts {per_period}; "
              f"{len(units_affected)} units affected")
        report[f"missing_{col}"] = {
            "n_missing": n_missing,
            "periods": sorted(per_period),
            "counts_by_period": {str(k): int(v) for k, v in per_period.items()},
            "units": units_affected,
        }
    else:
        print(f"  {col}: 0 missing")

# ---- group sizes ----------------------------------------------------------------------
per_unit = df.groupby("_unit")["_treated"].first()
print(f"\ntreated units: {int(per_unit.sum())}; control units: {int((1 - per_unit).sum())}")

report.update({
    "rows_raw": 2400,
    "rows_used": int(len(df)),
    "units": int(n_units),
    "periods": int(n_time),
    "balanced": bool(len(unbalanced) == 0),
    "n_treated": int(per_unit.sum()),
    "n_control": int((1 - per_unit).sum()),
    "calendar_gaps": gaps,
})
(didlib.RESULTS / "panel_checks.json").write_text(json.dumps(report, indent=2),
                                                  encoding="utf-8")
print(f"\nwrote {(didlib.RESULTS / 'panel_checks.json').relative_to(didlib.ROOT)}")
