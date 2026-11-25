"""Step 7: inference by placebo. Assign the treatment to each unit in turn, re-estimate TWFE.

With a single treated unit, cluster-robust standard errors are not reliable, so the
placebo test is the inference that counts (plan.md test 3).

Two variants are reported, because the choice of placebo control pool matters:
  (A) the other 38 units as controls, with the treated unit left in the pool
      (this is what plan.md test 3 literally describes: "assign the treatment in
      1989 to each of the 38 control states in turn", all 39 units estimated);
  (B) the treated unit dropped from the pool for every placebo run, so each
      placebo regression is estimated on 38 units.
"""

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
post = p["post"]
units = np.unique(unit)
treated_unit = float(cfg["treated_units"][0])


def placebo_estimates(exclude: float | None):
    """TWFE DiD coefficient for every unit in turn, treated = (unit == u) & post."""
    rows = []
    for u in units:
        if exclude is not None and u == exclude:
            continue
        m = np.ones(len(y), dtype=bool) if exclude is None else (unit != exclude)
        X = np.column_stack([np.ones((int(m.sum()), 1)), ((unit == u) & post)[m].astype(float).reshape(-1, 1),
                             dc.dummies(unit[m]), dc.dummies(time[m])])
        fit = dc.ols(y[m], X)
        rows.append({"unit": int(u), "coef": float(fit["params"][1]),
                     "is_treated_unit": bool(u == treated_unit), "n": int(m.sum())})
    return rows


def ca_estimate():
    """The treated unit's own estimate (all 39 units, treated = treated unit x post)."""
    X = np.column_stack([np.ones((len(y), 1)), p["treated"].reshape(-1, 1),
                         dc.dummies(unit), dc.dummies(time)])
    fit = dc.ols(y, X)
    return {"unit": int(treated_unit), "coef": float(fit["params"][1]),
            "is_treated_unit": True, "n": int(len(y))}


def summarise(rows, label, true_row_override=None):
    if true_row_override is not None:
        rows = rows + [true_row_override]
    coefs = np.array([r["coef"] for r in rows])
    idx = [i for i, r in enumerate(rows) if r["is_treated_unit"]][0]
    order = np.argsort(coefs)
    rank = int(np.where(order == idx)[0][0]) + 1
    n = len(rows)
    true_coef = float(coefs[idx])
    print(f"\n[{label}] rows per regression: {rows[0]['n']}")
    print(f"  treated unit {int(treated_unit)}: estimate {true_coef:+.3f}")
    print(f"  rank {rank} of {n} (1 = most negative); placebo p = {rank}/{n} = {rank / n:.4f}")
    print(f"  placebo mean {coefs.mean():+.3f}, sd {coefs.std(ddof=1):.3f}")
    print("  5 most negative: " + ", ".join(f"unit {rows[i]['unit']}={coefs[i]:+.2f}" for i in order[:5]))
    return {"label": label, "rows": rows, "true_coef": true_coef, "rank": rank,
            "n_units": n, "p_value": rank / n, "placebo_sd": float(coefs.std(ddof=1)),
            "placebo_mean": float(coefs.mean()), "rows_per_regression": rows[0]["n"]}


all_pool = summarise(placebo_estimates(None), "A: treated unit kept in the placebo pool")
ca_out = summarise(placebo_estimates(treated_unit), "B: treated unit dropped from the pool",
                   true_row_override=ca_estimate())

# ---- plot variant A
rows = all_pool["rows"]
coefs = np.array([r["coef"] for r in rows])
mask_ctrl = ~np.array([r["is_treated_unit"] for r in rows])
fig, ax = plt.subplots(figsize=(9, 5))
ax.hist(coefs[mask_ctrl], bins=14, color="#95a5a6", edgecolor="white",
        label=f"placebo estimates ({int(mask_ctrl.sum())} control units)")
ax.axvline(all_pool["true_coef"], color="#c0392b", lw=2,
           label=(f"treated unit {int(treated_unit)}: {all_pool['true_coef']:+.1f} "
                  f"(rank {all_pool['rank']} of {all_pool['n_units']}, p={all_pool['p_value']:.3f})"))
ax.set_xlabel("placebo two-way fixed effects DiD estimate (packs per person per year)")
ax.set_ylabel("number of units")
ax.set_title("Placebo distribution: treating each unit in turn as 'treated' from 1989")
ax.legend(frameon=False, fontsize=9)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
out = dc.RESULTS / "05_placebo.png"
fig.savefig(out, dpi=150)
print("\nwrote", out.relative_to(dc.REPO))

dc.save_json({"variant_A_pool_includes_treated": all_pool, "variant_B_treated_dropped": ca_out},
             "05_placebo.json")
dc.save_csv(rows, "05_placebo_variantA.csv")
dc.save_csv(ca_out["rows"], "05_placebo_variantB.csv")
