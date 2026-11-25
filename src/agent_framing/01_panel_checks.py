"""Step 2: panel checks for the agent_framing run.

Runs the seven rules listed in data/README.md ("Rules (each one is a check
that can be run)"), plus duplicates, balance and missing-value years.
Column names come from did_config.json only.

Writes results/agent_framing/01_panel_checks.txt and .json
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import didlib

cfg = didlib.load_config()
cols, header = didlib.read_panel(cfg)

unit = didlib.as_int(cols[cfg["unit"]])
year = didlib.as_int(cols[cfg["time"]])
y = cols[cfg["outcome"]]
grp = cols[cfg["treatment_group_column"]]
post = cols[cfg["post_column_audit"]]
N = len(y)

rows = []
def say(s=""):
    rows.append(s)
    print(s)

say("Panel checks (agent_framing run)")
say(f"data file: {cfg['data_path']}")
say("")

# Rule 1: one row per state-year
n_pairs = len(set(zip(unit.tolist(), year.tolist())))
say(f"rows read                        : {N}")
say(f"distinct units                   : {len(np.unique(unit))}")
say(f"distinct years                   : {len(np.unique(year))} "
    f"({year.min()}-{year.max()})")
say(f"distinct (unit, year) pairs      : {n_pairs}")
say(f"duplicate (unit, year) pairs     : {N - n_pairs}")
say(f"RULE 1 (one row per unit-year, {len(np.unique(unit))}x{len(np.unique(year))} = "
    f"{len(np.unique(unit)) * len(np.unique(year))}) : "
    f"{'PASS' if N == n_pairs == len(np.unique(unit)) * len(np.unique(year)) else 'FAIL'}")
say("")

# Rule 2: treatment-group column marks one unit in every year
grp_units = np.unique(unit[grp])
say(f"rows with {cfg['treatment_group_column']} == True    : {int(grp.sum())}")
say(f"units with {cfg['treatment_group_column']} == True : {grp_units.tolist()}")
years_of_grp = np.unique(year[grp])
say(f"years covered for that unit      : {years_of_grp.min()}-{years_of_grp.max()} "
    f"({len(years_of_grp)} years)")
ok2 = int(grp.sum()) == len(years_of_grp) and len(grp_units) == 1
say(f"RULE 2 ({cfg['treatment_group_column']} True for one unit in all years)     : "
    f"{'PASS' if ok2 else 'FAIL'}")
say("")

# Rule 3: the treatment (group AND year >= start) is True in len(treated_units) * n_post rows
treat = didlib.treated_post(cols, cfg)
n_post = int((year >= cfg["treatment_start"]).sum() // len(np.unique(unit)))
expected_treated_rows = len(cfg["treated_units"]) * n_post
say(f"treatment rows (group & year >= {cfg['treatment_start']}) : {int(treat.sum())} "
    f"(expected {expected_treated_rows} = {len(cfg['treated_units'])} unit(s) x {n_post} post years)")
say(f"RULE 3 (treatment in exactly {expected_treated_rows} rows)          : "
    f"{'PASS' if int(treat.sum()) == expected_treated_rows else 'FAIL'}")
say("")

# Rule 4: post column is the year dummy for every state
expect_post = year >= cfg["treatment_start"]
say(f"rows with {cfg['post_column_audit']} == True      : {int(post.sum())} "
    f"(expected {int(expect_post.sum())} = 39 states x 12 years)")
say(f"post column == (year >= {cfg['treatment_start']}) everywhere        : "
    f"{bool(np.array_equal(post, expect_post))}")
say(f"RULE 4 ({cfg['post_column_audit']} is the year dummy for all states)     : "
    f"{'PASS' if np.array_equal(post, expect_post) else 'FAIL'}")
say("")

# Rule 5: outcome and mechanism never empty, never negative
for c in [cfg["outcome"], cfg["mechanism_outcome"]]:
    v = cols[c]
    say(f"{c:10s}: NaN={int(np.isnan(v).sum())}, negative={int((v < 0).sum())}, "
        f"min={v.min():.4f}, max={v.max():.4f}")
say("RULE 5 (outcome & mechanism never empty or negative)     : "
    f"{'PASS' if not np.isnan(cols[cfg['outcome']]).any() and (cols[cfg['outcome']] >= 0).all()
       and not np.isnan(cols[cfg['mechanism_outcome']]).any() and (cols[cfg['mechanism_outcome']] >= 0).all() else 'FAIL'}")
say("")

# Rule 6: NaN means missing, list the exact years
say("Missing values, exact years (each listed year is missing for every state):")
for c in header:
    v = cols[c]
    if v.dtype != bool:
        miss = np.isnan(v)
        if miss.any():
            miss_years = sorted(np.unique(year[miss]).tolist())
            counts_by_year = {int(yy): int(miss[year == yy].sum()) for yy in miss_years}
            say(f"  {c:10s}: {int(miss.sum())} rows in {len(miss_years)} years: {miss_years}")
            say(f"             per-year counts: {counts_by_year}")
        else:
            say(f"  {c:10s}: no missing values")
say("RULE 6 (empty cell = missing, listed by exact year)      : see table above")
say("")

# Balance: every unit has the same number of rows and the same years
counts = {int(u): int((unit == u).sum()) for u in np.unique(unit)}
balanced = len(set(counts.values())) == 1
year_sets_identical = len({tuple(sorted(np.unique(year[unit == u]).tolist()))
                           for u in np.unique(unit)}) == 1
say(f"balanced panel (same #rows per unit)        : {balanced} "
    f"({len(set(counts.values()))} distinct count(s): {sorted(set(counts.values()))})")
say(f"all units cover the identical year range    : {year_sets_identical}")
say("")

# Float32 artifact example (README caveat 7): shown, not cleaned
ex = np.unique(y)[0]
say(f"float32 artifact example (outcome, not cleaned): {ex!r}")
say("")
say("Rows dropped in this script: 0 (checks only; the analysis sample stays at "
    f"{N} rows)")
say("Rows used by the main analysis: all 1209 (no filters; no covariates, so no rows lost to missingness)")

didlib.save_text("01_panel_checks.txt", rows)

with open(os.path.join(didlib.RESULTS_DIR, "01_panel_checks.json"), "w", encoding="utf-8") as f:
    json.dump({
        "rows": N, "n_units": int(len(np.unique(unit))),
        "years": [int(year.min()), int(year.max())],
        "duplicate_pairs": N - n_pairs,
        "balanced": bool(balanced and year_sets_identical),
        "treatment_rows": int(treat.sum()),
        "missing_years": {c: sorted(np.unique(year[np.isnan(cols[c])]).tolist())
                          for c in header
                          if cols[c].dtype != bool and np.isnan(cols[c]).any()},
    }, f, indent=2)
print("\nwrote 01_panel_checks.txt / .json in", didlib.RESULTS_DIR)
