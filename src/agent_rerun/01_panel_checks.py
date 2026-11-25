"""Step 2 (and config-role checks of step 1): panel checks for the agent_rerun run.

Reads did_config.json and data/raw/california_tobacco.csv.
No rows are filtered at any point; every check prints the row count.
Writes results/agent_rerun/01_panel_checks.txt
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import didlib

cfg = didlib.load_config()
cols, header = didlib.read_panel(cfg)
N = len(cols[cfg["unit"]])

lines = []


def say(msg=""):
    print(msg)
    lines.append(msg)


say(f"data file: {cfg['data_path']}")
say(f"columns in file: {header}")
say(f"rows read: {N}  (no filter applied)")

unit = didlib.as_int(cols[cfg["unit"]])
year = didlib.as_int(cols[cfg["time"]])
y = cols[cfg["outcome"]]
cali = cols[cfg["treatment_group_column"]]
after = cols["after_treatment"]
treat = cali & (year >= cfg["treatment_start"])

# --- structure
units = np.unique(unit)
years = np.unique(year)
say(f"\n[structure]")
say(f"distinct units: {len(units)}  (IDs {units.min()}..{units.max()})")
say(f"distinct periods: {len(years)}  ({years.min()}..{years.max()})")

dup_keys, dup_counts = np.unique(np.stack([unit, year], axis=1), axis=0, return_counts=True)
n_dup = int((dup_counts > 1).sum())
say(f"duplicate (unit, year) pairs: {n_dup}")

rows_per_unit = np.array([(unit == g).sum() for g in units])
balanced = bool(np.all(rows_per_unit == len(years)))
say(f"balanced panel: {balanced}  (rows per unit: min {rows_per_unit.min()}, max {rows_per_unit.max()}; "
    f"expected {len(years)} each; {len(units)} x {len(years)} = {len(units) * len(years)})")
say(f"rows after structure checks: {N} (nothing dropped)")

# --- missing values, exact periods
say(f"\n[missing values] (exact periods computed from the file)")
for name in header:
    col = cols[name]
    if col.dtype == bool:
        miss = 0
    elif col.dtype == object:
        miss = sum(1 for v in col if str(v).strip() == "")
    else:
        miss = int(np.isnan(col).sum())
    if miss:
        miss_years = sorted(set(year[np.isnan(col)].tolist()))
        say(f"  {name}: {miss} missing rows; years missing (for all units): {miss_years}")
    else:
        say(f"  {name}: 0 missing rows")
say(f"rows after missing-value checks: {N} (nothing dropped; missing cells only matter for covariates, which are not used)")

# --- config roles against the data
say(f"\n[config role checks]")
say(f"outcome '{cfg['outcome']}': dtype float, range {np.nanmin(y):.1f}..{np.nanmax(y):.1f}, "
    f"never negative: {bool(np.nanmin(y) >= 0)}")
neg_mech = np.nanmin(cols[cfg["mechanism"]])
say(f"mechanism '{cfg['mechanism']}': range {neg_mech:.1f}..{np.nanmax(cols[cfg['mechanism']]):.1f}, "
    f"never negative: {bool(neg_mech >= 0)}")

cali_states = np.unique(unit[cali])
say(f"'{cfg['treatment_group_column']}' is True for state(s) {cali_states.tolist()}, "
    f"rows {int(cali.sum())} (expected: 1 state x {len(years)} years = {len(years)})")

after_years = np.unique(year[after])
say(f"'after_treatment' is True for years {after_years.min()}..{after_years.max()}, rows {int(after.sum())} "
    f"= {len(units)} states x {int(after_years.max() - after_years.min() + 1)} years")

# the decisive treatment check: after_treatment must NOT be used as the treatment
treat_if_after = after & ~cali
say(f"if 'after_treatment' were used as the treatment: {int(treat_if_after.sum())} treated rows "
    f"belong to CONTROL units -> it is a year dummy, rejected as treatment")

tr_rows = np.unique(np.stack([unit[treat], year[treat]], axis=1), axis=0)
say(f"treatment = {cfg['treatment_group_column']} AND year >= {cfg['treatment_start']}: "
    f"{int(treat.sum())} treated rows (expected 12), all in state {sorted(set(unit[treat].tolist()))}, "
    f"years {tr_rows[:, 1].min()}..{tr_rows[:, 1].max()}")

treated_units = np.unique(unit[treat])
control_units = np.array([g for g in units if g not in treated_units])
say(f"treated units: {len(treated_units)} -> {treated_units.tolist()}")
say(f"control units: {len(control_units)} (IDs {control_units.min()}..{control_units.max()})")
say(f"treatment True in any control-unit row: {int((treat & ~cali).sum())} (must be 0)")

tr_start = {int(g): int(year[(unit == g) & treat].min()) for g in treated_units}
say(f"treatment start per treated unit: {tr_start}  -> single common start: {len(set(tr_start.values())) == 1}")

# cigsale sanity per group-period
say(f"\n[outcome means] {cfg['outcome']} by group and period (packs/person/year)")
ca_pre = cali & (year < cfg["treatment_start"])
ca_post = treat
co = ~cali
co_pre = co & (year < cfg["treatment_start"])
co_post = co & (year >= cfg["treatment_start"])
for label, m in [("California pre  (1970-1988)", ca_pre), ("California post (1989-2000)", ca_post),
                 ("Controls  pre  (1970-1988)", co_pre), ("Controls  post (1989-2000)", co_post)]:
    say(f"  {label}: n={int(m.sum())}, mean={y[m].mean():.2f}, sd={y[m].std(ddof=1):.2f}")

say(f"\nrows at end of script: {N} (no filter, merge or drop was applied anywhere)")

out_path = os.path.join(didlib.RESULTS_DIR, "01_panel_checks.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"\nwrote {out_path}")

# machine-readable tail for the summary
summary = {
    "n_rows": N,
    "n_units": int(len(units)),
    "n_periods": int(len(years)),
    "balanced": balanced,
    "n_treated_units": int(len(treated_units)),
    "treated_units": treated_units.tolist(),
    "n_control_units": int(len(control_units)),
    "treatment_rows": int(treat.sum()),
    "single_common_treatment_start": bool(len(set(tr_start.values())) == 1),
}
with open(os.path.join(didlib.RESULTS_DIR, "01_panel_checks.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
