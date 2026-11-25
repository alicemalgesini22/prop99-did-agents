"""04 - Raw trends: mean outcome by group and period, with a line at treatment start."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import didlib as L

cfg = L.load_config()
OUT = Path("results") / L.RUN_DIR
unit, time, outcome = cfg["unit"], cfg["time"], cfg["outcome"]
start = cfg["treatment_start"]

df = L.add_treatment_columns(L.read_panel(cfg), cfg)
print("rows:", len(df))

trend = (df.groupby(["treated", time], observed=True)[outcome]
           .agg(["mean", "std", "count"]).reset_index()
           .rename(columns={"mean": "mean_outcome", "std": "sd_outcome", "count": "n_units"}))
trend["group"] = trend["treated"].map({1: "treated", 0: "control"})
trend["se"] = trend["sd_outcome"] / trend["n_units"] ** 0.5
trend.to_csv(OUT / "raw_trends.csv", index=False)
print(trend.to_string(index=False))

fig, ax = plt.subplots(figsize=(8, 4.8))
for g, sub in trend.groupby("group"):
    sub = sub.sort_values(time)
    ax.plot(sub[time], sub["mean_outcome"], marker="o", label=g)
    ax.fill_between(sub[time], sub["mean_outcome"] - 1.96 * sub["se"],
                    sub["mean_outcome"] + 1.96 * sub["se"], alpha=0.15)
ax.axvline(start, color="black", linestyle="--", linewidth=1)
ax.text(start + 0.08, ax.get_ylim()[1], "treatment start", va="top", fontsize=8)
ax.set_xlabel(time)
ax.set_ylabel(outcome)
ax.set_title("Mean reading score by group (shaded: 95% CI of the mean)")
ax.legend(title="group")
fig.tight_layout()
fig.savefig(OUT / "raw_trends.png", dpi=150)
print("wrote", OUT / "raw_trends.png", "and raw_trends.csv")

gap = (trend.pivot(index=time, columns="group", values="mean_outcome"))
gap["treated_minus_control"] = gap["treated"] - gap["control"]
gap.reset_index().to_csv(OUT / "raw_trends_gap.csv", index=False)
print(gap.round(2).to_string())
with open(OUT / "raw_trends_meta.json", "w", encoding="utf-8") as fh:
    json.dump({"treatment_start": start, "units_treated": int(df.loc[df.treated == 1, unit].nunique()),
               "units_control": int(df.loc[df.treated == 0, unit].nunique()),
               "rows": int(len(df))}, fh, indent=2)
