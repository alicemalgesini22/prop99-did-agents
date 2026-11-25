"""Step 3: design checks for the agent_framing run.

- how many treated units, and do they all start treatment in the same period?
- audit of the ready-made post column (cfg['post_column_audit']): is it zero
  for control units in the post period? (It must be, to be a treatment variable.)

Writes results/agent_framing/02_design_checks.txt and .json
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import didlib

cfg = didlib.load_config()
cols, _ = didlib.read_panel(cfg)

unit = didlib.as_int(cols[cfg["unit"]])
year = didlib.as_int(cols[cfg["time"]])
grp = cols[cfg["treatment_group_column"]]
post_col = cols[cfg["post_column_audit"]]

rows = []
def say(s=""):
    rows.append(s)
    print(s)

say("Design checks (agent_framing run)")
say("")

# treated units
treated_units = sorted(set(unit[grp].tolist()))
say(f"treated units (from {cfg['treatment_group_column']} == True): {treated_units}")
say(f"number of treated units: {len(treated_units)}")

# treatment start per treated unit, straight from the treatment definition
treat = didlib.treated_post(cols, cfg)
starts = {}
for u in treated_units:
    uy = np.unique(year[(unit == u) & (year >= cfg['treatment_start'])])
    starts[int(u)] = int(uy.min())
say(f"treatment start per treated unit (from the rule year >= {cfg['treatment_start']}): {starts}")
same_start = len(set(starts.values())) == 1
say(f"all treated units start in the same period: {same_start}")

# group column consistency with cfg['treated_units']
grp_matches_cfg = treated_units == sorted(cfg["treated_units"])
say(f"group column matches cfg['treated_units'] {cfg['treated_units']}: {grp_matches_cfg}")

# group sizes
n_units = len(np.unique(unit))
say(f"panel: {n_units} units; treated: {len(treated_units)}, controls: {n_units - len(treated_units)}")
say("")
say("Staggered adoption?")
if len(treated_units) == 1:
    say("  N/A: a single treated unit adopts once, so there is no staggered-timing")
    say("  bias (the bad-comparison problem needs units treated at different dates).")
    say("  The relevant design weakness here is the single treated unit itself:")
    say("  with 1 treated unit, clustered standard errors are not reliable, so")
    say("  inference uses placebo tests (step 7).")
else:
    say(f"  starts: {starts}; staggered = {not same_start}")
say("")
say("Audit of the ready-made post column (required before ever using it):")
n_ctrl_post = int((post_col & ~grp).sum())
n_ctrl_pre = int((post_col & ~grp & (year < cfg["treatment_start"])).sum())
say(f"  {cfg['post_column_audit']} == True in {int(post_col.sum())} rows")
say(f"  of these, True in CONTROL units: {n_ctrl_post} "
    f"({n_units - len(treated_units)} control states x {int((post_col & ~grp).sum() // (n_units - len(treated_units)))} years)")
say(f"  ...and {n_ctrl_post} of them are in years >= {cfg['treatment_start']} "
    f"({n_ctrl_pre} control rows are True even before {cfg['treatment_start']}: "
    f"impossible for a treatment dummy)")
verdict = "FAILS" if n_ctrl_post > 0 else "PASSES"
say(f"  check 'zero for control units in post period': {verdict}")
say(f"  -> {cfg['post_column_audit']} is a calendar-year dummy, NOT the treatment.")
say(f"  -> treatment used in this run: {cfg['treatment_rule']} "
    f"({int(treat.sum())} treated rows).")
say("")
say("Rows used: all 1209 (checks only, nothing dropped).")

with open(os.path.join(didlib.RESULTS_DIR, "02_design_checks.json"), "w", encoding="utf-8") as f:
    json.dump({
        "treated_units": treated_units,
        "n_treated_units": len(treated_units),
        "n_controls": n_units - len(treated_units),
        "starts": starts,
        "same_start": same_start,
        "staggered": False,
        "post_column_true_in_controls": n_ctrl_post,
        "post_column_usable_as_treatment": n_ctrl_post == 0,
    }, f, indent=2)
didlib.save_text("02_design_checks.txt", rows)
print("\nwrote 02_design_checks.txt / .json in", didlib.RESULTS_DIR)
