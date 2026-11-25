"""02_trends.py — Raw mean outcome over time, treated vs control (step 4),
plus the plan.md mechanism check on retprice.

Reads results/agent/did_config.json. Writes results/agent/raw_trends.png,
results/agent/raw_trends.csv, results/agent/mechanism_retprice.csv.
"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "results" / "agent" / "did_config.json").read_text())

UNIT, TIME, OUT = CFG["unit"], CFG["time"], CFG["outcome"]
TSTART = CFG["treatment_start"]
TREAT0 = CFG["treated_units"][0]

df = pd.read_csv(ROOT / CFG["data_path"])
df["treat_"] = (df[UNIT] == TREAT0) & (df[TIME] >= TSTART)
df["grp"] = df[UNIT].map(lambda s: "California (treated)" if s == TREAT0
                         else "Control states (mean)")

agg = df.groupby([TIME, "grp"], as_index=False)[OUT].mean()
piv = agg.pivot(index=TIME, columns="grp", values=OUT)
piv["gap"] = piv["California (treated)"] - piv["Control states (mean)"]
piv.round(3).to_csv(ROOT / "results" / "agent" / "raw_trends.csv")

fig, axes = plt.subplots(2, 1, figsize=(9, 8), sharex=True)
ax = axes[0]
for col, style in [("California (treated)", "o-"), ("Control states (mean)", "s--")]:
    ax.plot(piv.index, piv[col], style, label=col)
ax.axvline(TSTART - 0.5, color="red", ls=":", label=f"Treatment start ({TSTART})")
ax.set_ylabel(f"{OUT} (packs/person/year)")
ax.legend()
ax.set_title(f"Raw mean {OUT} by year: California vs mean of 38 control states")

ax = axes[1]
mpiv = df.pivot_table(index=TIME, columns="grp", values=CFG["mechanism_outcome"], aggfunc="mean")
gap_p = mpiv["California (treated)"] - mpiv["Control states (mean)"]
ax.plot(gap_p.index, gap_p.values, "d-")
ax.axvline(TSTART - 0.5, color="red", ls=":")
ax.set_ylabel(f"{CFG['mechanism_outcome']} gap\n(California - control mean)")
ax.set_xlabel("year")
ax.set_title("Mechanism check: price gap, California minus control mean")

fig.tight_layout()
fig.savefig(ROOT / "results" / "agent" / "raw_trends.png", dpi=150)
print("Saved results/agent/raw_trends.png, raw_trends.csv")

gap_p.to_frame("price_gap").round(3).to_csv(ROOT / "results" / "agent" / "mechanism_retprice.csv")
print("Mean price gap 1980-1988:", round(gap_p.loc[1980:1988].mean(), 2),
      "| mean price gap 1989-2000:", round(gap_p.loc[1989:].mean(), 2))
print("Price gap 1988:", round(gap_p.loc[1988], 2), "| 1989:", round(gap_p.loc[1989], 2))
