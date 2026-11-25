"""Step 4: raw trends. Mean outcome over time, treated vs control, line at treatment start."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import did_common as dc

cfg = dc.load_config()
p = dc.load_panel(cfg)
unit, time, y = p["unit"], p["time"], p["y"]
t0 = float(cfg["treatment_start"])

years = np.unique(time)
m_treated = np.array([y[(unit == cfg["treated_units"][0]) & (time == t)].mean() for t in years])
m_control = np.array([y[p["in_group"] == False][time[p["in_group"] == False] == t].mean() for t in years])  # noqa: E712

fig, ax = plt.subplots(figsize=(9, 5.2))
ax.plot(years, m_treated, marker="o", ms=3.5, lw=2, color="#c0392b",
        label=f"treated unit {int(cfg['treated_units'][0])} (California)")
ax.plot(years, m_control, marker="s", ms=3, lw=2, color="#2c3e50",
        label=f"mean of {int(len(np.unique(unit)) - len(cfg['treated_units']))} control units")
ax.axvline(t0, color="grey", ls="--", lw=1.2)
ax.text(t0 + 0.2, ax.get_ylim()[1] * 0.97, f"treatment starts {int(t0)}", va="top", fontsize=9, color="dimgrey")
ax.set_xlabel("year")
ax.set_ylabel(f"{cfg['outcome']} (packs per person per year)")
ax.set_title("Raw means: per-capita cigarette sales, treated vs controls")
ax.legend(frameon=False, loc="lower left")
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
out = dc.RESULTS / "02_raw_trends.png"
fig.savefig(out, dpi=150)
print("wrote", out.relative_to(dc.REPO))

gap = m_treated - m_control
print("\nyear  treated  control   gap")
for t, a, b, g in zip(years, m_treated, m_control, gap):
    print(f"{int(t)}  {a:7.2f}  {b:7.2f}  {g:+7.2f}")
# simple pre-trend slope of the gap, 1970-1988, as a diagnostic
pre = years < t0
slope_gap = np.polyfit(years[pre], gap[pre], 1)[0]
print(f"\npre-{int(t0)} linear slope of the treated-minus-control gap: {slope_gap:+.4f} packs/year")
dc.save_json({"years": years.tolist(), "treated_mean": m_treated.tolist(),
              "control_mean": m_control.tolist(), "gap": gap.tolist(),
              "pre_gap_slope": float(slope_gap)}, "02_raw_trends.json")
