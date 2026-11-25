"""02 - Panel checks: rows, units, periods, duplicates, balance, missing values."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import didlib as L

cfg = L.load_config()
OUT = Path("results") / L.RUN_DIR
unit, time, outcome = cfg["unit"], cfg["time"], cfg["outcome"]

df = pd.read_csv(cfg["data_path"])
print(f"[read] rows={len(df)}  (reason: raw file as provided)")
print(f"columns={list(df.columns)}")

# type fixes only; no rows dropped
df[unit] = pd.to_numeric(df[unit]).astype(int)
df[time] = pd.to_numeric(df[time]).astype(int)
df[outcome] = pd.to_numeric(df[outcome], errors="coerce")
print(f"[after dtype conversion] rows={len(df)}  (reason: none dropped, types only)")

report: dict = {}
report["rows_raw"] = int(len(df))
report["n_units"] = int(df[unit].nunique())
report["n_periods"] = int(df[time].nunique())
report["period_min"] = int(df[time].min())
report["period_max"] = int(df[time].max())
report["periods"] = sorted(int(x) for x in df[time].unique())

# duplicates on (unit, time)
dups = df[df.duplicated(subset=[unit, time], keep=False)]
report["duplicate_unit_time_rows"] = int(len(dups))
print(f"[duplicates] rows in duplicated (unit,time) cells: {len(dups)}")
if len(dups):
    print(dups.sort_values([unit, time]).to_string())

# uniqueness check
df = df.drop_duplicates(subset=[unit, time], keep="first")
print(f"[after dropping duplicate cells] rows={len(df)}  (reason: keep first row per (unit,period))")
report["rows_after_dedup"] = int(len(df))

# balance: full grid
units = df[unit].unique()
periods = df[time].unique()
full = pd.MultiIndex.from_product([units, periods], names=[unit, time])
present = pd.MultiIndex.from_frame(df[[unit, time]])
missing_cells = full.difference(present)
report["n_expected_cells"] = int(len(full))
report["n_missing_cells"] = int(len(missing_cells))
report["missing_cells"] = [[int(u), int(t)] for u, t in missing_cells]
report["balanced"] = bool(len(missing_cells) == 0)
report["rows_per_unit"] = {str(int(v)): int(c) for v, c in df[unit].value_counts().sort_index().items()}
print(f"[balance] expected cells={len(full)}, missing cells={len(missing_cells)}, balanced={len(missing_cells)==0}")
if len(missing_cells):
    print("  missing (unit, period):", report["missing_cells"])

# missing outcome, exact periods
miss_y = df[df[outcome].isna()]
report["n_missing_outcome"] = int(len(miss_y))
report["missing_outcome_cells"] = [[int(r[unit]), int(r[time])] for _, r in miss_y.iterrows()]
print(f"[missing outcome] rows={len(miss_y)}  exact (unit, period)={(report['missing_outcome_cells'])[:50]}")

# other missing values
for c in df.columns:
    if df[c].isna().any():
        print(f"[missing] {c}: {int(df[c].isna().sum())} rows")
report["missing_by_column"] = {c: int(df[c].isna().sum()) for c in df.columns}

df.to_csv(OUT / "panel_used.csv", index=False)
with open(OUT / "panel_checks.json", "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2)
print("\nrows used in analysis:", len(df))
print("wrote", OUT / "panel_checks.json")
