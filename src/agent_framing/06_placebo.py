"""Step 7: placebo test for the agent_framing run (plan.md test 3).

With 1 treated unit, clustered SEs are not reliable, so: assign the 1989
treatment to each of the 38 control states in turn, re-estimate the same
TWFE, and compare California's actual estimate to the placebo distribution.
Rank 1 = most negative of 39; placebo p-value = rank / 39 (plan.md's rule).

Writes results/agent_framing/06_placebo.png / .csv / .txt / .json
"""
import csv
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import didlib

np.random.seed(42)  # fixed seed (AGENTS.md); this test is deterministic

cfg = didlib.load_config()
cols, _ = didlib.read_panel(cfg)

unit = didlib.as_int(cols[cfg["unit"]])
year = didlib.as_int(cols[cfg["time"]])
y = cols[cfg["outcome"]]
cluster = unit
control_units = sorted(set(unit.tolist()) - set(cfg["treated_units"]))

# true estimate
res_ca = didlib.twfe(unit, year, y, didlib.treated_post(cols, cfg), cluster,
                     ref_year=cfg["reference_period"])
beta_ca = res_ca["beta"]

# placebo estimates: same TWFE, treatment moved to each control state
placebo = []
for s in control_units:
    r = didlib.twfe(unit, year, y, didlib.treated_post(cols, cfg, [s]), cluster,
                    ref_year=cfg["reference_period"])
    placebo.append((int(s), r["beta"], r["se_cluster"]))

placebo_sorted = sorted(placebo, key=lambda x: x[1])
rank = 1 + sum(1 for _, b, _ in placebo if b < beta_ca)
p_value = rank / (len(placebo) + 1)

fig, ax = plt.subplots(figsize=(9, 5))
ax.hist([b for _, b, _ in placebo], bins=12, color="tab:blue", alpha=0.75,
        label="placebo estimates (38 control states)")
ax.axvline(beta_ca, color="tab:red", linewidth=2,
           label=f"California's estimate ({beta_ca:.2f}, rank {rank} of {len(placebo) + 1})")
ax.set_xlabel("TWFE beta (packs/person/year)")
ax.set_ylabel("Number of placebo units")
ax.set_title("Placebo test: treatment assigned to each control state in 1989")
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
png = os.path.join(didlib.RESULTS_DIR, "06_placebo.png")
fig.savefig(png, dpi=150)

with open(os.path.join(didlib.RESULTS_DIR, "06_placebo.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["state", "beta", "se_cluster", "is_california"])
    for s, b, se in sorted(placebo + [(cfg["treated_units"][0], beta_ca, res_ca["se_cluster"])],
                           key=lambda x: x[1]):
        w.writerow([s, f"{b:.4f}", f"{se:.4f}", s == cfg["treated_units"][0]])

lines = [
    "Placebo test (agent_framing): treatment in 1989 assigned to each control state in turn",
    f"rows used per regression: {len(y)} (all; no filters)",
    f"California's actual TWFE beta       = {beta_ca:.4f}",
    f"placebo betas: min {min(b for _, b, _ in placebo):.4f}, "
    f"max {max(b for _, b, _ in placebo):.4f}, "
    f"mean {np.mean([b for _, b, _ in placebo]):.4f}, "
    f"sd {np.std([b for _, b, _ in placebo], ddof=1):.4f}",
    "",
    "most negative 5 of the 39 estimates:",
] + [f"  state {s}: beta = {b: .4f}{'  <-- California (actual)' if s == cfg['treated_units'][0] else ''}"
     for s, b, _ in placebo_sorted[:5]] + [
    "",
    f"California's rank among the 39 (1 = most negative): {rank}",
    f"placebo p-value = rank / 39 = {p_value:.4f} "
    f"({'< 0.05' if p_value < 0.05 else '>= 0.05'})",
    "NOTE: this p-value treats all 39 units as exchangeable; it is the plan.md rule.",
    f"wrote {png}",
]
didlib.save_text("06_placebo.txt", lines)

with open(os.path.join(didlib.RESULTS_DIR, "06_placebo.json"), "w", encoding="utf-8") as f:
    json.dump({"beta_california": beta_ca, "rank": rank, "p_value": p_value,
               "placebos": [{"state": s, "beta": b, "se": se} for s, b, se in placebo]},
              f, indent=2)
print("\n".join(lines))
print(f"\nwrote 06_placebo.png / .csv / .txt / .json in {didlib.RESULTS_DIR}")
