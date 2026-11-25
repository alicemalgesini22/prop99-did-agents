"""04 - Raw trends: mean outcome by period for treated and control regions."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from didlib import (RESULTS, add_treatment_columns, load_config, read_panel)

cfg = load_config()
df = add_treatment_columns(read_panel(cfg), cfg)
unit, time, outcome = cfg["unit"], cfg["time"], cfg["outcome"]
start = cfg["treatment_start"]

trend = (df.groupby(["treated", time], observed=True)[outcome]
           .agg(["mean", "std", "count"]).reset_index())
trend["group"] = trend["treated"].map({1: "treated", 0: "control"})
trend["se"] = trend["std"] / trend["count"] ** 0.5
trend = trend.rename(columns={"mean": "mean_outcome", "std": "sd_outcome", "count": "n_units"})
trend[["group", time, "mean_outcome", "se", "n_units"]].to_csv(RESULTS / "raw_trends.csv", index=False)
print(f"rows written to raw_trends.csv: {len(trend)} ({trend['group'].nunique()} groups x "
      f"{trend[time].nunique()} periods)")

fig, ax = plt.subplots(figsize=(9, 5))
for g, sub in trend.groupby("group"):
    sub = sub.sort_values(time)
    ax.plot(sub[time], sub["mean_outcome"], marker="o", ms=3, label=g)
ax.axvline(start, color="black", ls="--", lw=1.2, label=f"treatment start (q{start})")
ax.set_xlabel("quarter")
ax.set_ylabel(f"mean {outcome} (million euro)")
ax.set_title("Raw trends: mean private investment, treated vs control regions")
ax.legend()
fig.tight_layout()
fig.savefig(RESULTS / "raw_trends.png", dpi=150)
print(f"saved raw_trends.png ({len(trend)} plotted points)")

pre = trend.pivot(index=time, columns="group", values="mean_outcome")
pre = pre.loc[pre.index < start]
gap_pre_start = float(pre["treated"].iloc[0] - pre["control"].iloc[0])
gap_pre_end = float(pre["treated"].iloc[-1] - pre["control"].iloc[-1])
print(f"treated-control mean gap: q{pre.index[0]} = {gap_pre_start:.3f}, "
      f"q{pre.index[-1]} = {gap_pre_end:.3f} (change {gap_pre_end - gap_pre_start:+.3f})")
