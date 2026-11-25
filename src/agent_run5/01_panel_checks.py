"""Panel checks for the agent_run5 DiD run (step 2 of the procedure).

Prints row counts after every filter with the reason; checks rows, units,
periods, duplicates, balance, missing values (exact years), and the treatment
rules from data/README.md. Column names come from results/agent_run5/did_config.json.
"""
import didlib as dl
import numpy as np

cfg = dl.load_config()
DATA, UNIT, TIME, OUT = cfg["data_path"], cfg["unit"], cfg["time"], cfg["outcome"]
GRP, AFTER, TSTART = cfg["treatment_group_col"], cfg["time_indicator_col"], cfg["treatment_start"]

cols, n_raw = dl.read_panel(DATA)
print("=== Raw file ===")
print(f"rows read: {n_raw} (no filter applied yet)")

state = dl.as_int(cols[UNIT])
year = dl.as_int(cols[TIME])
y = dl.as_float(cols[OUT])
grp = dl.as_bool(cols[GRP])
after = dl.as_bool(cols[AFTER])

units = np_units = np.unique(state)
years = np.unique(year)
print(f"units: {len(units)} (range {units.min()}-{units.max()})")
print(f"years: {len(years)} ({years.min()}-{years.max()})")

dup = len(state) - len(set(zip(state.tolist(), year.tolist())))
print(f"duplicate (unit, year) pairs: {dup} -> filter drops {dup} rows")
if dup:
    keep = np.array([1] * len(state), dtype=bool)
    seen = set()
    for i, (s, t) in enumerate(zip(state.tolist(), year.tolist())):
        if (s, t) in seen:
            keep[i] = False
        seen.add((s, t))
    state, year, y, grp, after = (a[keep] for a in (state, year, y, grp, after))
    print(f"rows after dropping duplicates: {len(state)}")

sizes = {int(u): int((state == u).sum()) for u in units}
balanced = all(v == len(years) for v in sizes.values())
print(f"balanced panel: {balanced} (every unit has min {min(sizes.values())}, max {max(sizes.values())} rows)")

print("\n=== Missing values (exact years, computed from the file) ===")
for name in sorted(cols):
    if name in (UNIT, TIME, GRP, AFTER):
        continue
    v = dl.as_float(cols[name])
    nmiss = int(np.isnan(v).sum())
    if nmiss:
        miss_years = sorted(set(int(t) for t, m in zip(year, np.isnan(v)) if m))
        print(f"{name}: {nmiss} missing rows; missing years: {miss_years}")
    else:
        print(f"{name}: 0 missing rows; none")

print("\n=== Treatment rules ===")
print(f"{GRP} True: {int(grp.sum())} rows, in states {sorted(set(int(s) for s, g in zip(state, grp) if g))}")
print(f"{AFTER} True: {int(after.sum())} rows (expected 39x12=468); "
      f"{len(set(int(s) for s, a in zip(state, after) if a))} states, years {year[after].min()}-{year[after].max()}")
print(f"{AFTER} True among CONTROL states: {int((after & ~grp).sum())} rows "
      f"-> {AFTER} alone is NOT the treatment (it is 1 for controls)")
trt = grp & (year >= TSTART)
print(f"treatment ({GRP} & year>={TSTART}): {int(trt.sum())} rows "
      f"(expected 1 x {years.max() - TSTART + 1} = {years.max() - TSTART + 1})")
print(f"treatment True exactly where {GRP} & {AFTER}: {bool((trt == (grp & after)).all())}")
print(f"pre-{TSTART} {GRP} rows with treatment True: {int((trt & (year < TSTART)).sum())} (expected 0)")

print(f"\n{OUT}: missing {int(np.isnan(y).sum())}, negative {int((y < 0).sum())}, "
      f"range {np.nanmin(y):.1f}-{np.nanmax(y):.1f}")

treated_units = sorted(set(int(s) for s, g in zip(state, grp) if g))
print(f"\nRows used in DiD: {len(state)} (all rows kept; no covariates -> no drops)")
print(f"treated units: {treated_units} (count {len(treated_units)})")
print(f"control units: {len(units) - len(treated_units)}")
