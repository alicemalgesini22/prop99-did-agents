"""02: raw trends of the mean outcome by cohort and for never-treated counties."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

OUT = "results/county_jobs"
cfg = json.load(open(f"{OUT}/did_config.json"))
df = pd.read_csv(f"{OUT}/panel_analysis.csv")
unit, time, y = cfg["unit"], cfg["time"], cfg["outcome"]

df["group"] = df["program_start"].fillna(0).astype(int).astype(str).replace({"0": "never treated"})

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
ax = axes[0]
for g, sub in df.groupby("group"):
    m = sub.groupby(time)[y].mean()
    lab = f"cohort {g}" if g != "never treated" else g
    ax.plot(m.index, m.values, marker="o", ms=3, label=lab)
    if g != "never treated":
        ax.axvline(int(g), color=ax.lines[-1].get_color(), ls=":", lw=1)
ax.set_title("Mean employment rate by cohort (dotted = own treatment start)")
ax.set_xlabel(time); ax.set_ylabel(y); ax.legend(fontsize=8)

ax = axes[1]
df["treated_any"] = (df["program_start"].notna()).map({True: "treated (all cohorts)", False: "never treated"})
for g, sub in df.groupby("treated_any"):
    m = sub.groupby(time)[y].mean()
    ax.plot(m.index, m.values, marker="o", ms=3, label=g)
for g in cfg["treatment_start"]["note"].split("cohorts ")[1].split(";")[0].split(","):
    ax.axvline(int(g), color="grey", ls=":", lw=1)
ax.set_title("Treated vs never treated (dotted = the three cohort start years)")
ax.set_xlabel(time); ax.set_ylabel(y); ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(f"{OUT}/raw_trends.png", dpi=150)
print(f"[saved] {OUT}/raw_trends.png")

tab = df.pivot_table(index=time, columns="group", values=y, aggfunc="mean").round(2)
print(tab.to_string())
tab.to_csv(f"{OUT}/raw_trends_means.csv")
