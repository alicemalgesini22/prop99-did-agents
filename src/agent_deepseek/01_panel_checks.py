"""Step 1-3: specification check, panel checks, design checks.

Reads did_config.json, verifies every role against the data, and prints the
panel/design checks. Writes results/agent_deepseek/panel_checks.json.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import did_common as dc

cfg = dc.load_config()
d = dc.read_csv(cfg["data_path"])
panel = dc.load_panel(cfg)
unit, time, y = panel["unit"], panel["time"], panel["y"]

U, T, Y = cfg["unit"], cfg["time"], cfg["outcome"]
checks: dict = {}
print(f"config: {cfg['data_path']}  unit={U}  time={T}  outcome={Y}")
print(f"treated_units={cfg['treated_units']}  treatment_start={cfg['treatment_start']}  "
      f"cluster={cfg['cluster']}  controls={cfg['controls']}")

# ---------------------------------------------------------------- panel checks
n_rows = len(unit)
print(f"\n[panel] rows read: {n_rows}")
checks["rows_read"] = n_rows

units = np.unique(unit)
times = np.unique(time)
print(f"[panel] units: {len(units)} ({units.min():.0f}-{units.max():.0f})")
print(f"[panel] periods: {len(times)} ({times.min():.0f}-{times.max():.0f})")
checks["n_units"] = int(len(units))
checks["n_periods"] = int(len(times))
checks["period_min"] = float(times.min())
checks["period_max"] = float(times.max())

pairs = list(zip(unit.astype(int).tolist(), time.astype(int).tolist()))
dup_pairs = [k for k, v in Counter(pairs).items() if v > 1]
print(f"[panel] duplicate ({U},{T}) pairs: {len(dup_pairs)}")
checks["duplicate_pairs"] = len(dup_pairs)

counts = Counter(unit.astype(int).tolist())
unbalanced = {u: c for u, c in counts.items() if c != len(times)}
print(f"[panel] balanced: {not unbalanced} (units with != {len(times)} rows: {unbalanced or 'none'})")
checks["balanced"] = not unbalanced
checks["rows_per_unit"] = {int(u): int(c) for u, c in sorted(counts.items())}

# missing values, exact periods, per column
missing: dict[str, dict] = {}
for col, vals in d.items():
    if not isinstance(vals[0], float):
        continue
    miss = [i for i, v in enumerate(vals) if np.isnan(v)]
    if not miss:
        continue
    yrs = sorted({int(time[i]) for i in miss})
    n_units_affected = len({int(unit[i]) for i in miss})
    print(f"[missing] {col}: {len(miss)} rows, years {yrs}, "
          f"all {n_units_affected} units in those years")
    missing[col] = {"rows": len(miss), "years": yrs, "n_units_affected": n_units_affected}
checks["missing"] = missing
print(f"[missing] {Y}: {int(np.isnan(y).sum())} missing rows")

# --------------------------------------------------------------- design checks
treated_units = sorted({float(u) for u in cfg["treated_units"]})
print(f"\n[design] treated units in config: {len(treated_units)} -> {[int(u) for u in treated_units]}")
checks["n_treated_units"] = len(treated_units)

# does the boolean 'california' column define exactly these units?
if "california" in d:
    ca_units = sorted({int(u) for u, f in zip(unit, d["california"]) if f})
    print(f"[design] units flagged by the 'california' column: {ca_units}")
    checks["units_flagged_california"] = ca_units
    assert ca_units == [int(u) for u in treated_units], "config treated_units != california column"

# after_treatment must NOT be the treatment: count its Trues and its over-coverage
if "after_treatment" in d:
    at = np.array(d["after_treatment"], dtype=bool)
    at_years = sorted({int(t) for t, f in zip(time, at) if f})
    in_group = np.isin(unit, treated_units)
    n_at_true = int(at.sum())
    n_at_true_control = int((at & ~in_group).sum())
    same_as_year_dummy = bool(np.all(at == (time >= float(cfg["treatment_start"]))))
    print(f"[design] 'after_treatment' True rows: {n_at_true}; of those non-treated-unit rows: "
          f"{n_at_true_control}; equals (year >= {cfg['treatment_start']}) for every row: {same_as_year_dummy}")
    print(f"[design] 'after_treatment' years: {at_years[0]}-{at_years[-1]}")
    checks["after_treatment"] = {
        "true_rows": n_at_true, "true_rows_outside_treated_unit": n_at_true_control,
        "is_pure_year_dummy": same_as_year_dummy, "years": [at_years[0], at_years[-1]],
    }
    # Confirmed: it is a pure calendar-year dummy, True for 456 control rows too,
    # so using it as the treatment would be wrong. This is why it is not in the config.
    assert same_as_year_dummy and n_at_true_control > 0, "unexpected after_treatment column"

# treatment timing: first treated period per treated unit
in_group = np.isin(unit, treated_units)
first_post: dict[int, int] = {}
for u in treated_units:
    ts = time[(unit == u) & (time >= float(cfg["treatment_start"]))]
    ts_all = time[unit == u]
    first_post[int(u)] = int(ts.min()) if len(ts) else -1
    print(f"[design] unit {int(u)}: years {int(ts_all.min())}-{int(ts_all.max())}, first post period "
          f"{first_post[int(u)]}, rows post = {int(((unit == u) & (time >= cfg['treatment_start'])).sum())}")
starts = set(first_post.values())
print(f"[design] treatment timing staggered across treated units: {len(starts) > 1}")
checks["treated_first_period"] = first_post
checks["staggered"] = len(starts) > 1
if len(treated_units) < 5:
    print(f"[design] only {len(treated_units)} treated unit(s): cluster-robust SEs are NOT reliable; "
          f"inference will use the placebo test (step 7).")
    checks["few_treated_warning"] = True

# how many rows are treated, pre/post split
post = time >= float(cfg["treatment_start"])
print(f"\n[rows] all rows used in the main spec: {n_rows} (no filter, no drop)")
print(f"[rows] pre period: rows {int((~post).sum())} ({int(len(np.unique(time[~post])))} years); "
      f"post period: rows {int(post.sum())} ({int(len(np.unique(time[post])))} years)")
print(f"[rows] treated state-year rows (in group & post): {int(panel['treated'].sum())}")
checks["rows_pre"] = int((~post).sum())
checks["rows_post"] = int(post.sum())
checks["rows_treated"] = int(panel["treated"].sum())
checks["rows_used_main_spec"] = n_rows

p = dc.save_json(checks, "panel_checks.json")
print(f"\nwrote {p.relative_to(dc.REPO)}")
