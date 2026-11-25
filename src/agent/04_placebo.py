"""04_placebo.py — Inference with 1 treated unit: in-space placebo test (step 7).

Assigns the 1989 treatment to each of the 38 control states in turn,
re-estimates the TWFE DiD, and ranks California's estimate among the 39.

Reads results/agent/did_config.json. Writes results/agent/placebo_test.txt,
results/agent/placebo_estimates.csv, results/agent/placebo_hist.png.
"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import statsmodels.formula.api as smf

ROOT = pathlib.Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "results" / "agent" / "did_config.json").read_text())

UNIT, TIME, OUT = CFG["unit"], CFG["time"], CFG["outcome"]
TSTART = CFG["treatment_start"]
TREAT0 = CFG["treated_units"][0]

out_lines = []
def say(x=""):
    print(x)
    out_lines.append(str(x))

df = pd.read_csv(ROOT / CFG["data_path"])
post = (df[TIME] >= TSTART).astype(int)

rows = []
for s in sorted(df[UNIT].unique()):
    df["plc"] = ((df[UNIT] == s) & (post == 1)).astype(int)
    m = smf.ols(f"{OUT} ~ plc + C({UNIT}) + C({TIME})", data=df).fit()
    rows.append({"unit": s, "estimate": m.params["plc"]})
tab = pd.DataFrame(rows)
tab.to_csv(ROOT / "results" / "agent" / "placebo_estimates.csv", index=False)

real = tab.loc[tab.unit == TREAT0, "estimate"].iloc[0]
plc = tab.loc[tab.unit != TREAT0, "estimate"]
# rank among ALL 39 (most negative = rank 1)
rank = int((tab["estimate"] < real).sum()) + 1
n_units = len(tab)
say("=== Step 7: in-space placebo test ===")
say(f"Placebo treatment = (unit == s) & (year >= {TSTART}) for each of the "
    f"{n_units - 1} control states; TWFE {OUT} ~ plc + C(state) + C(year).")
say(f"California (real) estimate: {real:.4f}")
say(f"Placebo estimates: min {plc.min():.3f}, max {plc.max():.3f}, "
    f"mean {plc.mean():.3f}")
say(f"California's rank among all {n_units} (1 = most negative): {rank}")
say(f"Placebo p-value = rank / {n_units} = {rank / n_units:.4f}")
say("Interpretation: p < 0.05 means California's estimated effect is more "
    "negative than the 95th percentile of the placebo distribution.")

fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(plc, bins=12, color="lightsteelblue", edgecolor="grey")
ax.axvline(real, color="red", lw=2, label=f"California (real) = {real:.1f}, rank {rank}/{n_units}")
ax.set_xlabel(f"TWFE {OUT} coefficient")
ax.set_ylabel("number of placebo (or real) units")
ax.set_title("Placebo distribution: 1989 treatment assigned to each state")
ax.legend()
fig.tight_layout()
fig.savefig(ROOT / "results" / "agent" / "placebo_hist.png", dpi=150)
say("\nSaved results/agent/placebo_estimates.csv, placebo_hist.png, placebo_test.txt")
(ROOT / "results" / "agent" / "placebo_test.txt").write_text("\n".join(out_lines) + "\n")
