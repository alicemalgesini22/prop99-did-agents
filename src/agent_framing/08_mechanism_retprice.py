"""Mechanism check (plan.md 'Theory'): did California's retail price rise
relative to the control states after 1989? Same TWFE design as the main
estimate, with cfg['mechanism_outcome'] (retprice) as the outcome.

Writes results/agent_framing/08_mechanism_retprice.txt / .json
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
y = cols[cfg["mechanism_outcome"]]
treat = didlib.treated_post(cols, cfg)
cluster = unit
grp = didlib.treated_units_mask(cols, cfg)
pre = year < cfg["treatment_start"]

rows = []
def say(s=""):
    rows.append(s)
    print(s)

say(f"Mechanism check (agent_framing): {cfg['mechanism_outcome']} ~ treated_post + unit FE + year FE")
say(f"rows used: {len(y)} (all; {cfg['mechanism_outcome']} has no missing values)")
say("")
res = didlib.twfe(unit, year, y, treat, cluster, ref_year=cfg["reference_period"])
say(f"TWFE beta on {cfg['mechanism_outcome']}                = {res['beta']:.4f}")
say(f"  cluster-by-state SE                  = {res['se_cluster']:.4f}")
say(f"  classical SE                         = {res['se_classical']:.4f}")
say(f"  (unit of {cfg['mechanism_outcome']}: price per pack; unit possibly cents - "
    "marked unverified in data/README.md)")
say("")

d_treat = y[grp & ~pre].mean() - y[grp & pre].mean()
d_ctrl = y[~grp & ~pre].mean() - y[~grp & pre].mean()
say(f"2x2 cross-check: treated change {d_treat:.4f}, control change {d_ctrl:.4f}, "
    f"2x2 DiD {d_treat - d_ctrl:.4f}")

with open(os.path.join(didlib.RESULTS_DIR, "08_mechanism_retprice.json"), "w", encoding="utf-8") as f:
    json.dump({"twfe": res, "twobytwo": {
        "treated_change": float(d_treat), "control_change": float(d_ctrl),
        "did": float(d_treat - d_ctrl)}}, f, indent=2)
didlib.save_text("08_mechanism_retprice.txt", rows)
print("\nwrote 08_mechanism_retprice.txt / .json in", didlib.RESULTS_DIR)
