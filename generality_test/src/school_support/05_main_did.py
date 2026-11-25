"""05 - Main estimate: TWFE (treated x post + unit FE + time FE), plus the 2x2 cross-check."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import didlib as L

cfg = L.load_config()
OUT = Path("results") / L.RUN_DIR
unit, time, outcome = cfg["unit"], cfg["time"], cfg["outcome"]

df = L.add_treatment_columns(L.read_panel(cfg), cfg)
print("rows:", len(df))

# cluster-robust by unit (primary; 20 treated / 40 control units)
main = L.twfe(df, cfg, cluster=cfg["cluster"], label="twfe_cluster_unit")
# same model with classical SEs, for reference only
main_iid = L.twfe(df, cfg, cluster=None, label="twfe_iid")

x2 = L.simple_2x2(df, cfg)

print("\nTWFE (cluster by unit):")
print(json.dumps(main, indent=2))
print("\n2x2 cell means:")
print(json.dumps(x2, indent=2))

# also verify the fast demeaning routine agrees with the formula estimate
fast = L.demean_twfe(
    df, cfg, cluster=cfg["cluster"],
    n_params=1 + 1 + (df[unit].nunique() - 1) + (df[time].nunique() - 1))
print("\ndemeaning cross-check:", fast)

out = {"twfe_cluster_unit": main, "twfe_iid": main_iid, "two_by_two": x2,
       "demeaning_check": fast,
       "interpretation_note": (
           f"Estimate is the change in the treated-control gap in {outcome} after "
           f"{cfg['treatment_start']}, "
           "in test points. Positive = gap narrowed / treated gained relative to control.")}
with open(OUT / "main_did.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
print("\nwrote", OUT / "main_did.json")
print(f"\nHEADLINE: {main['coef']:.3f} points, SE {main['se']:.3f}, "
      f"95% CI [{main['ci_lo']:.3f}, {main['ci_hi']:.3f}], p={main['p']:.4f}")
print(f"2x2 cross-check: {x2['did_2x2']:.3f} points")
