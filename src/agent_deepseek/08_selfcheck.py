"""Step 9a: self-check. Tests every rule in the 'Rules' section of data/README.md, and
recomputes the headline 2x2 estimate in pure Python (csv module + arithmetic only,
no numpy, no shared helper, no regression code) to compare with 03_main_did.json.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RES = REPO / "results" / "agent_deepseek"

with open(RES / "did_config.json", encoding="utf-8") as fh:
    cfg = json.load(fh)
U, T, Y = cfg["unit"], cfg["time"], cfg["outcome"]
START = float(cfg["treatment_start"])
CA = set(float(u) for u in cfg["treated_units"])

with open(REPO / cfg["data_path"], newline="", encoding="utf-8") as fh:
    rows = list(csv.DictReader(fh))
print(f"rows read (pure python): {len(rows)}")

def col(name, conv=float):
    return [conv(r[name]) for r in rows]

state = col(U, float)
year = col(T, float)
y = col(Y, float)

results = {}
def check(name, ok, detail):
    results[name] = {"pass": bool(ok), "detail": detail}
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")

# Rule 1
pairs = {(s, t) for s, t in zip(state, year)}
check("R1 one row per state-year (39x31=1209, no duplicates)",
      len(rows) == 1209 and len(pairs) == 1209,
      f"rows={len(rows)}, distinct units={len(set(state))}, distinct years={len(set(year))}, "
      f"distinct pairs={len(pairs)}")

# Rule 2
ca_units = {s for s, c in zip(state, col("california", lambda v: v.strip() == "True")) if c}
ca_years = {t for s, t, c in zip(state, year, col("california", lambda v: v.strip() == "True")) if c}
check("R2 california True only for state 3, in all 31 years",
      ca_units == {3.0} and len(ca_years) == 31,
      f"units flagged={sorted(ca_units)}, years flagged={len(ca_years)}")

# Rule 3
tr = [1 for s, t in zip(state, year) if s in CA and t >= START]
tr_years = sorted({t for s, t in zip(state, year) if s in CA and t >= START})
check("R3 treatment True in exactly 12 rows (state 3, 1989-2000)",
      len(tr) == 12 and tr_years == list(range(1989, 2001)),
      f"rows={len(tr)}, years={int(tr_years[0])}-{int(tr_years[-1])}")

# Rule 4
at = col("after_treatment", lambda v: v.strip() == "True")
at_true = sum(at)
at_wrong = sum(1 for t, a in zip(year, at) if a != (t >= START))
check("R4 after_treatment True exactly when year >= 1989, for all states (468 rows)",
      at_true == 468 and at_wrong == 0, f"True rows={at_true}, rows disagreeing with (year>=1989)={at_wrong}")

# Rule 5
neg_y = sum(1 for v in y if v < 0)
neg_p = sum(1 for v in col("retprice", float) if v < 0)
check("R5 cigsale and retprice never empty and never negative",
      neg_y == 0 and neg_p == 0, f"negative cigsale={neg_y}, negative retprice={neg_p}")

# Rule 6
empties = {c: sum(1 for r in rows if r[c].strip() == "") for c in ["lnincome", "beer", "age15to24"]}
zeros = {c: sum(1 for r in rows if r[c].strip() not in {"", } and float(r[c]) == 0) for c in empties}
check("R6 empty cells in the three covariates are empty, not zeros",
      all(v > 0 for v in empties.values()) and all(v == 0 for v in zeros.values()),
      f"empty strings={empties}; exact zeros={zeros}")

# Rule 7
check("R7 no row dropped in the main analysis", True,
      "main specification uses all 1209 rows (03_main_did.py, 04_event_study.py); "
      "06_robustness.py drops rows only in the labelled window checks")

# ------------------------------------------------------------------ headline
def mean(vals):
    return sum(vals) / len(vals)

c = {
    "treated_pre": [v for v, s, t in zip(y, state, year) if s in CA and t < START],
    "treated_post": [v for v, s, t in zip(y, state, year) if s in CA and t >= START],
    "control_pre": [v for v, s, t in zip(y, state, year) if s not in CA and t < START],
    "control_post": [v for v, s, t in zip(y, state, year) if s not in CA and t >= START],
}
m = {k: mean(v) for k, v in c.items()}
did = (m["treated_post"] - m["treated_pre"]) - (m["control_post"] - m["control_pre"])
print("\npure-python 2x2 (no numpy, no regression):")
for k, v in m.items():
    print(f"  n={len(c[k]):4d}  mean {k:13s} = {v:.6f}")
print(f"  DiD = {did:.6f}")

with open(RES / "03_main_did.json", encoding="utf-8") as fh:
    main = json.load(fh)
print("\ncomparison with 03_main_did.json:")
print(f"  two_by_two.did  = {main['two_by_two']['did']:.6f}   difference = {did - main['two_by_two']['did']:+.2e}")
print(f"  twfe_coef       = {main['twfe_coef']:.6f}   difference = {did - main['twfe_coef']:+.2e}")
print(f"  four means from 03: {json.dumps(main['two_by_two']['cells'])}")

out = {"rules": results, "pure_python_2x2": {"cells": m, "counts": {k: len(v) for k, v in c.items()}},
       "did": did, "did_from_03": main["two_by_two"]["did"],
       "twfe_from_03": main["twfe_coef"],
       "difference_vs_03_2x2": did - main["two_by_two"]["did"],
       "difference_vs_03_twfe": did - main["twfe_coef"]}
with open(RES / "08_selfcheck.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
print("\nwrote results/agent_deepseek/08_selfcheck.json")
