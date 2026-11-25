"""Step 4: Raw trends — mean outcome over time, treated vs control.

Reads results/workflow/did_config.json; no column names are hard-coded.
Outputs: results/workflow/04_raw_trends.png (+ .csv with the plotted values)
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CFG_PATH = ROOT / "results" / "workflow" / "did_config.json"
OUT_PNG = ROOT / "results" / "workflow" / "04_raw_trends.png"
OUT_CSV = ROOT / "results" / "workflow" / "04_raw_trends.csv"

cfg = json.loads(CFG_PATH.read_text())
UNIT, TIME, OUTCOME = cfg["unit"], cfg["time"], cfg["outcome"]
DATA = ROOT / cfg["data_path"]

df = pd.read_csv(DATA)
treated_ids = cfg["treated_units"]
start = cfg["treatment_start"]

df = df.assign(is_treated=df[UNIT].isin(treated_ids))
means = (df.groupby([TIME, "is_treated"])[OUTCOME]
           .mean()
           .unstack("is_treated")
           .rename(columns={False: "control", True: "treated"}))
means.to_csv(OUT_CSV)

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(means.index, means["treated"], marker="o", color="tab:red",
        label=f"treated (unit {treated_ids})")
ax.plot(means.index, means["control"], marker="s", color="tab:blue",
        label=f"control (n={df[UNIT].nunique() - len(treated_ids)} units, mean)")
ax.axvline(start, color="black", linestyle="--", linewidth=1,
           label=f"treatment start ({start})")
ax.set_xlabel(TIME)
ax.set_ylabel(f"mean {OUTCOME} (packs/person/year)")
ax.set_title(f"Mean {OUTCOME} over time: treated vs control units")
ax.legend()
fig.tight_layout()
fig.savefig(OUT_PNG, dpi=150)

print(f"Treated mean 1988: {means.loc[1988, 'treated']:.2f}; "
      f"control mean 1988: {means.loc[1988, 'control']:.2f}")
print(f"Saved {OUT_PNG} and {OUT_CSV}")
