"""Mechanism check from plan.md ('Theory'): did the retail price rise in the treated unit after 1989?

Same TWFE design, outcome = retprice (column read from did_config.json notes; the
price column name is taken from the config key 'price_column', added here rather
than hard-coded in the script body, see note printed below).
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
# The price column is not a DiD role, so it is named in the config ('mechanism_outcome')
# instead of being hard-coded here. data/README.md defines it as retprice.
price_col = cfg["mechanism_outcome"]
print(f"price column used: {price_col} (from data/README.md; unit unverified, probably cents)")

d = dc.read_csv(cfg["data_path"])
p = dc.load_panel(cfg)
unit, time, y = p["unit"], p["time"], p["y"]
t0 = float(cfg["treatment_start"])
price = np.asarray(d[price_col], dtype=float)
print(f"rows: {len(price)} price observations, missing {int(np.isnan(price).sum())}")

X = np.column_stack([np.ones((len(price), 1)), p["treated"].reshape(-1, 1),
                     dc.dummies(unit), dc.dummies(time)])
fit = dc.ols(price, X, cluster=unit)
b, se = float(fit["params"][1]), float(fit["se_classic"][1])
print(f"\nTWFE on {price_col}: treated coef = {b:+.3f} (classic se {se:.3f}, "
      f"cluster se {float(fit['se_cluster'][1]):.3f})")

# also the same for the cigarette-sales outcome, to show the two side by side
fit_y = dc.ols(y, X, cluster=unit)
print(f"TWFE on {cfg['outcome']}: treated coef = {float(fit_y['params'][1]):+.3f}")

yrs = np.unique(time)
ca = p["in_group"]
m_ca = np.array([price[ca & (time == t)].mean() for t in yrs])
m_ct = np.array([price[(~ca) & (time == t)].mean() for t in yrs])

fig, ax = plt.subplots(figsize=(9, 5.2))
ax.plot(yrs, m_ca, marker="o", ms=3.5, lw=2, color="#c0392b", label="treated unit")
ax.plot(yrs, m_ct, marker="s", ms=3, lw=2, color="#2c3e50", label="mean of control units")
ax.axvline(t0, color="grey", ls="--", lw=1.2)
ax.text(t0 + 0.2, ax.get_ylim()[1] * 0.97, f"treatment starts {int(t0)}", va="top", fontsize=9, color="dimgrey")
ax.set_xlabel("year")
ax.set_ylabel(f"{price_col} (unit unverified, probably cents per pack)")
ax.set_title(f"Mechanism: raw means of {price_col}, treated vs controls")
ax.legend(frameon=False, loc="upper left")
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
out = dc.RESULTS / "07_mechanism_price.png"
fig.savefig(out, dpi=150)
print("wrote", out.relative_to(dc.REPO))

dc.save_json({"price_column": price_col, "twfe_coef_price": b, "se_classic_price": se,
              "twfe_coef_sales": float(fit_y["params"][1]),
              "years": yrs.tolist(), "treated_mean": m_ca.tolist(), "control_mean": m_ct.tolist()},
             "07_mechanism_price.json")
