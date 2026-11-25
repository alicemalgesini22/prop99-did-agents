"""Step 5: main estimate. Two-way fixed effects: outcome ~ treated x post + unit FE +
time FE, standard errors clustered by unit. Cross-check: simple 2x2 difference of means.

Run: uv run python src/school_tutoring/05_main_did.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from didlib import (fast_did_coef, load_config, load_panel, save_json,  # noqa: E402
                    twfe)

cfg = load_config()
df = load_panel(cfg)
print(f"rows used: {len(df)}")

# ---- main TWFE ----------------------------------------------------------------------
res = twfe(df, cov="cluster")
b = float(res.params["_did"])
se = float(res.bse["_did"])
ci = res.conf_int().loc["_did"].tolist()
p = float(res.pvalues["_did"])
print("\nTWFE: _y ~ _did + unit FE + time FE, cluster by unit")
print(f"  treated x post = {b:.4f} points (SE {se:.4f}, t={b / se:.3f}, "
      f"p={p:.4f}, 95% CI [{ci[0]:.4f}, {ci[1]:.4f}])")
print(f"  N={int(res.nobs)}, units={df['_unit'].nunique()}, periods={df['_time'].nunique()}")

# ---- exact double-demeaning cross-check ---------------------------------------------
b_fast = fast_did_coef(df["_y"], df["_did"], df["_unit"], df["_time"])
print(f"\ndouble-demeaning check of the same coefficient: {b_fast:.6f} "
      f"(difference {abs(b_fast - b):.2e})")

# ---- simple 2x2 difference of means --------------------------------------------------
cells = df.groupby(["_treated", "_post"])["_y"].mean().unstack()
print("\ncell means (rows: treated flag, columns: post flag):")
print(cells.round(3).to_string())
treat_delta = cells.loc[1, 1] - cells.loc[1, 0]
ctrl_delta = cells.loc[0, 1] - cells.loc[0, 0]
did_2x2 = treat_delta - ctrl_delta
print(f"\ntreated change post-pre: {treat_delta:+.3f}")
print(f"control change post-pre: {ctrl_delta:+.3f}")
print(f"2x2 difference of means (treated minus control change): {did_2x2:+.4f}")

# ---- within-unit variance check ------------------------------------------------------
print(f"\nshare of outcome variance between units: "
      f"{df.groupby('_unit')['_y'].mean().var() / df['_y'].var():.3f} "
      "(unit FE carry most of the variation)")

save_json({
    "spec": "y ~ treated*post + unit FE + time FE, all rows, no covariates",
    "coef": b, "se_cluster_unit": se, "t": b / se, "p_value": p,
    "ci95": [float(ci[0]), float(ci[1])],
    "n_obs": int(res.nobs), "n_units": int(df["_unit"].nunique()),
    "n_periods": int(df["_time"].nunique()),
    "cluster": cfg["cluster"], "n_clusters": int(df["_unit"].nunique()),
    "coef_double_demeaning_check": b_fast,
    "two_by_two": {
        "treated_change": float(treat_delta),
        "control_change": float(ctrl_delta),
        "did": float(did_2x2),
        "cell_means": {f"treated{int(i)}_post{int(j)}": float(cells.loc[i, j])
                       for i in cells.index for j in cells.columns},
    },
    "script": "src/school_tutoring/05_main_did.py",
}, "main_did.json")
