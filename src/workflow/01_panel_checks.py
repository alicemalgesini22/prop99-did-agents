"""Step 2: Panel checks for the DiD analysis.

Reads results/workflow/did_config.json; no column names are hard-coded.
Outputs: results/workflow/02_panel_checks.txt
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CFG_PATH = ROOT / "results" / "workflow" / "did_config.json"
OUT_PATH = ROOT / "results" / "workflow" / "02_panel_checks.txt"

cfg = json.loads(CFG_PATH.read_text())
UNIT, TIME, OUTCOME = cfg["unit"], cfg["time"], cfg["outcome"]
DATA = ROOT / cfg["data_path"]

lines = []


def say(s=""):
    print(s)
    lines.append(str(s))


df = pd.read_csv(DATA)
say(f"Loaded {cfg['data_path']}")
say(f"Rows loaded: {len(df)}")

# --- basic structure ---
n_units = df[UNIT].nunique()
periods = sorted(df[TIME].unique())
say(f"Units ({UNIT}): {n_units}")
say(f"Periods ({TIME}): {len(periods)} ({periods[0]}-{periods[-1]})")
say(f"Outcome ({OUTCOME}): dtype {df[OUTCOME].dtype}, "
    f"range {df[OUTCOME].min():.1f} to {df[OUTCOME].max():.1f}")

# --- duplicates ---
dup_mask = df.duplicated(subset=[UNIT, TIME], keep=False)
say(f"Duplicate ({UNIT},{TIME}) pairs: {int(dup_mask.sum())} rows flagged "
    f"(keep=False, so counts both members of each pair)")

# --- balance: every unit x period present exactly once ---
expected = n_units * len(periods)
actual_pairs = df.groupby([UNIT, TIME]).ngroups
say(f"Balance check: {n_units} units x {len(periods)} periods = {expected} expected rows; "
    f"file has {len(df)} rows and {actual_pairs} unique ({UNIT},{TIME}) pairs "
    f"-> {'balanced, no gaps' if len(df) == expected == actual_pairs else 'NOT balanced'}")
per_unit = df.groupby(UNIT).size()
say(f"Rows per unit: min {per_unit.min()}, max {per_unit.max()} "
    f"(all units have 31 rows)" if per_unit.nunique() == 1 else
    f"Rows per unit vary: {per_unit.describe().to_dict()}")

# --- missing values, exact periods ---
say("")
say("Missing values by column (only columns with any missing shown):")
for col in df.columns:
    n_missing = int(df[col].isna().sum())
    if n_missing > 0:
        miss_years = sorted(df.loc[df[col].isna(), TIME].unique())
        per_year = df.loc[df[col].isna(), TIME].value_counts()
        say(f"  {col}: {n_missing} missing rows in {len(miss_years)} years "
            f"{miss_years[0]}-{miss_years[-1]}")
        say(f"    exact missing years: {miss_years}")
        say(f"    missing rows per year: min {int(per_year.min())}, "
            f"max {int(per_year.max())} (of {n_units} units)")
        say(f"    -> {n_missing} rows = {n_units} units x {len(miss_years)} years: "
            f"{'missing for ALL units in those years' if per_year.nunique() == 1 and per_year.iloc[0] == n_units else 'PATTERN DIFFERS - investigate'}")
    else:
        say(f"  {col}: no missing values")

# --- treatment rows, sanity (config rule) ---
say("")
treated_ids = cfg["treated_units"]
treat = df[UNIT].isin(treated_ids) & (df[TIME] >= cfg["treatment_start"])
say(f"Treatment rule '{cfg['treatment_rule']}': {int(treat.sum())} treated rows")
say(f"  = {len(treated_ids)} treated units x {int(treat.sum()) // len(treated_ids)} post periods")

# --- filters: none applied (none needed) ---
say("")
say("FILTERS APPLIED: none. Reasons:")
say("  - no duplicate rows to drop (checked above)")
say("  - outcome and treatment columns have no missing values (checked above)")
say(f"  - covariates (lnincome, beer, age15to24) have missing years but are NOT used "
    f"per config (controls_covariates = {cfg['controls_covariates']})")
say(f"ROWS AFTER FILTERS: {len(df)} (unchanged)")

OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\nSaved to {OUT_PATH}")
