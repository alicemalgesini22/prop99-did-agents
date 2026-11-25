"""Step 6: event study. One coefficient per period relative to treatment, 1988 as reference."""

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
unit, time, y, ing = p["unit"], p["time"], p["y"], p["in_group"]
t0 = float(cfg["treatment_start"])
ref_year = t0 - 1  # last pre-treatment period (1988)

years = np.unique(time)
rel = [int(t - t0) for t in years if t != ref_year]
lead_lag = np.column_stack([(ing & (time == t)).astype(float) for t in years if t != ref_year])
names = [f"rel_{r:+d}" for r in rel]

X = np.column_stack([np.ones((len(y), 1)), lead_lag, dc.dummies(unit), dc.dummies(time)])
nm = ["const"] + names + [f"unit_{i}" for i in range(dc.dummies(unit).shape[1])] + \
     [f"year_{i}" for i in range(dc.dummies(time).shape[1])]
fit = dc.ols(y, X, names=nm, cluster=unit)
ct = dc.coef_table(fit)
print(f"rows used: {len(y)}; reference period {int(ref_year)} omitted (rel -1); "
      f"{len(rel)} event-time coefficients; n = {fit['n']}, k = {fit['k']}, R2 = {fit['r2']:.4f}")

rows = []
print("\n rel_year  year  coef     se_cluster(unreliable)")
for r, t in zip(rel, [int(t) for t in years if t != ref_year]):
    c = ct[f"rel_{r:+d}"]
    print(f"  {r:+3d}    {t}  {c['coef']:+8.3f}  {c['se_cluster']:7.3f}")
    rows.append({"rel_year": r, "year": t, "coef": c["coef"],
                 "se_cluster": c["se_cluster"], "se_classic": c["se_classic"]})

pre = [r for r in rows if r["rel_year"] < -1]
post = [r for r in rows if r["rel_year"] > -1]
pre_vals = np.array([r["coef"] for r in pre])
print(f"\npre-period coefficients ({int(pre[0]['year'])}-{int(ref_year)}): mean {pre_vals.mean():+.3f}, "
      f"min {pre_vals.min():+.3f}, max {pre_vals.max():+.3f}")
print("pre-period path is NOT flat: it falls from a large positive level in 1970 towards 1988;")
# linear fit to the pre-period coefficients, to say rising / flat / falling
sl = np.polyfit([r["rel_year"] for r in pre], pre_vals, 1)[0]
print(f"linear slope of the pre-period coefficients over event time: {sl:+.4f} packs/year")
print(f"post-period coefficients ({int(post[0]['year'])}-{int(post[-1]['year'])}): "
      f"mean {np.mean([r['coef'] for r in post]):+.3f}")

fig, ax = plt.subplots(figsize=(9.5, 5.4))
x = np.array([r["rel_year"] for r in rows])
b = np.array([r["coef"] for r in rows])
s = np.array([r["se_cluster"] for r in rows])
ax.errorbar(x, b, yerr=1.96 * s, fmt="o", ms=4, lw=1.1, color="#c0392b",
            ecolor="#c0392b", elinewidth=1, capsize=2.5,
            label="estimate, 95% CI (clustered by state, unreliable: 1 treated unit)")
ax.axhline(0, color="grey", lw=0.9)
ax.axvline(-0.5, color="grey", ls="--", lw=1.2)
ax.text(-0.4, ax.get_ylim()[1] * 0.95, f"treatment starts {int(t0)}", fontsize=9, color="dimgrey", va="top")
ax.plot(0, 0, "o", ms=0, label=f"reference period {int(ref_year)} (normalised to 0)")
ax.set_xlabel("years relative to treatment start (1989)")
ax.set_ylabel(f"{cfg['outcome']} effect vs {int(ref_year)} (packs per person per year)")
ax.set_title("Event study: treated unit vs controls, two-way fixed effects")
ax.legend(frameon=False, fontsize=8.5, loc="lower left")
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
out = dc.RESULTS / "04_event_study.png"
fig.savefig(out, dpi=150)
print("wrote", out.relative_to(dc.REPO))

dc.save_json({"reference_year": int(ref_year), "coefs": rows, "pre_slope": float(sl),
              "n": fit["n"], "k": fit["k"], "r2": fit["r2"]}, "04_event_study.json")
dc.save_csv(rows, "04_event_study.csv")
