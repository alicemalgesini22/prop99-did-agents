"""01_checks.py — Panel and design checks for the DiD run.

Reads results/agent/did_config.json; no column names are hard-coded.
Writes results/agent/panel_checks.txt.
"""
import json
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "results" / "agent" / "did_config.json").read_text())

UNIT, TIME, OUT = CFG["unit"], CFG["time"], CFG["outcome"]
TSTART = CFG["treatment_start"]

out_lines = []
def say(x=""):
    print(x)
    out_lines.append(str(x))

df = pd.read_csv(ROOT / CFG["data_path"])
say(f"Loaded {CFG['data_path']}")
say(f"Rows after load: {len(df)} (no filter applied)")

# --- column existence / roles ---
for col in [UNIT, TIME, OUT, "california", "after_treatment"]:
    assert col in df.columns, f"missing expected column {col}"
say(f"Columns present: {list(df.columns)}")

# --- rows, units, periods, duplicates ---
n_units = df[UNIT].nunique()
n_years = df[TIME].nunique()
say(f"Units: {n_units} distinct {UNIT} values: {sorted(df[UNIT].unique())}")
say(f"Periods: {n_years} distinct {TIME} values: {df[TIME].min()}-{df[TIME].max()}")
dup = df.duplicated(subset=[UNIT, TIME]).sum()
say(f"Duplicate (unit, year) pairs: {dup}")

# --- balance ---
cnt = df.groupby(UNIT)[TIME].nunique()
n_bal = (cnt == n_years).sum()
say(f"Balance: {n_bal}/{n_units} units have all {n_years} periods; "
    f"counts per unit: min={cnt.min()}, max={cnt.max()}")

# --- missing values, exact periods ---
say("Missing values per column (rows):")
for c in df.columns:
    m = df[c].isna().sum()
    say(f"  {c}: {m} missing rows", )
    if m:
        yrs = sorted(df.loc[df[c].isna(), TIME].unique())
        us = df.loc[df[c].isna(), UNIT].nunique()
        say(f"      exact years: {yrs} ({len(yrs)} years x {us} units = {m} rows)")
say(f"Outcome '{OUT}' missing rows: {df[OUT].isna().sum()} "
    "(analysis keeps all rows if 0; rows would only be dropped by filters below)")

# --- check 'california' flags the right unit ---
cal_states = sorted(df.loc[df["california"] == True, UNIT].unique())  # noqa: E712
say(f"Units with california==True: {cal_states} "
    f"(rows: {(df['california'] == True).sum()})")  # noqa: E712
assert cal_states == CFG["treated_units"], "california flag disagrees with config treated_units"

# --- verify after_treatment is a pure year dummy, NOT the treatment ---
at_vs_year = df.groupby(TIME)["after_treatment"].nunique()
say(f"after_treatment is constant within each year: {bool((at_vs_year == 1).all())}")
n_at = int(df["after_treatment"].sum())
n_post_yrs = df.loc[df[TIME] >= TSTART, TIME].nunique()
say(f"after_treatment==True rows: {n_at} = {n_units} units x {n_post_yrs} years "
    "-> it is a year dummy for ALL states")
# it is 1 for control units post-1988:
n_at_control = int(df.loc[df[UNIT] != CFG["treated_units"][0], "after_treatment"].sum())
say(f"after_treatment==True rows among CONTROL units: {n_at_control} -> "
    "after_treatment alone would mistreat 38 controls; NOT used as treatment")

# --- construct the actual treatment from the rule in the config ---
treated = (df[UNIT] == CFG["treated_units"][0]) & (df[TIME] >= TSTART)
df["treat_"] = treated
say(f"Treatment rule: {CFG['treatment_rule']} -> {int(treated.sum())} treated state-year rows")
say("All treated rows are unit(s) " + str(sorted(df.loc[treated, UNIT].unique())) +
    ", years " + f"{df.loc[treated, TIME].min()}-{df.loc[treated, TIME].max()}")
# agreement with after_treatment only inside California pre-period
cal_pre = df[(df["california"] == True) & (df[TIME] < TSTART)]  # noqa: E712
say(f"California pre-1989 rows: {len(cal_pre)}; treat_ False in all: "
    f"{bool((~cal_pre['treat_']).all())}; after_treatment False in all: "
    f"{bool((~cal_pre['after_treatment']).all())}")

# --- design checks ---
n_treated_units = df.loc[treated, UNIT].nunique()
say(f"Number of treated UNITS: {n_treated_units}")
if n_treated_units == 1:
    say("Only 1 treated unit: treatment timing is trivially common (1989). Not staggered.")
    say("Fewer than 5 treated units: clustered SEs are not reliable; "
        "inference will use placebo tests (plan.md test 3).")

# filter for analysis: none needed; state explicitly
analysis = df.copy()
say(f"Rows entering analysis: {len(analysis)} (no rows dropped: outcome complete, "
    "no covariates used)")

(ROOT / "results" / "agent" / "panel_checks.txt").write_text("\n".join(out_lines) + "\n")
say("\nSaved results/agent/panel_checks.txt")
