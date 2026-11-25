"""Step 3: Design checks — treated-unit count and treatment timing.

Reads results/workflow/did_config.json; no column names are hard-coded.
Outputs: results/workflow/03_design_checks.txt
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CFG_PATH = ROOT / "results" / "workflow" / "did_config.json"
OUT_PATH = ROOT / "results" / "workflow" / "03_design_checks.txt"

cfg = json.loads(CFG_PATH.read_text())
UNIT, TIME, OUTCOME = cfg["unit"], cfg["time"], cfg["outcome"]
DATA = ROOT / cfg["data_path"]

lines = []


def say(s=""):
    print(s)
    lines.append(str(s))


df = pd.read_csv(DATA)
treated_ids = cfg["treated_units"]

# --- count treated units ---
n_treated = len(treated_ids)
say(f"Treated units ({UNIT}): {n_treated} -> {treated_ids}")

# --- timing: first treated period per treated unit ---
treat = df[UNIT].isin(treated_ids) & (df[TIME] >= cfg["treatment_start"])
starts = df.loc[treat].groupby(UNIT)[TIME].min()
say(f"Treatment start per treated unit: {starts.to_dict()}")
n_distinct_starts = starts.nunique()
say(f"Distinct treatment start periods: {n_distinct_starts}")

if n_distinct_starts > 1:
    say("")
    say("WARNING: STAGGERED treatment timing detected.")
    say("Plain two-way fixed effects can be biased with staggered adoption")
    say("(-forbidden-comparison problem). STOPPING for human decision.")
else:
    say("Timing is common (all treated units start in "
        f"{cfg['treatment_start']}): plain TWFE is applicable.")

# --- inference implications ---
say("")
if n_treated < 5:
    say(f"Only {n_treated} treated unit(s): clustered standard errors are NOT")
    say("reliable (cluster-robust SEs need many clusters, and there is no")
    say("within-treatment-group variation to exploit).")
    say("-> Inference will use PLACEBO TESTS (procedure step 7): assign the")
    say("   treatment to each control unit in turn, re-estimate, and report")
    say("   the treated unit's rank; placebo p-value = rank / number of units.")
else:
    say(f"{n_treated} treated units: standard errors clustered by {cfg['cluster']}.")

OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\nSaved to {OUT_PATH}")
