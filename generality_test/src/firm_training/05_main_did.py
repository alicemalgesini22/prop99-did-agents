"""Step 5: main estimate. Two-way FE DiD (unit and time FE), SEs clustered by unit,
plus the simple 2x2 difference of means as a cross-check.

Run: uv run python src/firm_training/05_main_did.py
Writes results/firm_training/main_did.json
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import didlib  # noqa: E402

cfg = didlib.load_config()
df = didlib.load_panel(cfg)
start = cfg["treatment_start"]

print(f"rows used: {len(df)} (all rows; no filter applied beyond the panel checks)")
print(f"treated units: {df.groupby('_unit')['_treated'].first().sum()}, "
      f"periods: {df['_time'].nunique()}")

# ---- main: TWFE, clustered by unit ----------------------------------------------------
res = didlib.twfe(df, cov="cluster")
b = res.params["_did"]
se = res.bse["_did"]
p = res.pvalues["_did"]
ci = res.conf_int().loc["_did"].tolist()
n_clusters = df["_unit"].nunique()

print("\n=== main TWFE: _y ~ did + unit FE + time FE, SEs clustered by unit ===")
print(f"coefficient on treated x post: {b:+.4f} thousand euro per month")
print(f"cluster-robust SE: {se:.4f}  t={b / se:.3f}  p={p:.4f}  "
      f"95% CI [{ci[0]:.4f}, {ci[1]:.4f}]")
print(f"N={int(res.nobs)}, params={int(res.df_model) + 1}, clusters={n_clusters}, "
      f"R2={res.rsquared:.4f}")

# ---- cross-check: fast double-demeaning must give the same coefficient ----------------
b_fast = didlib.fast_did_coef(df["_y"], df["_did"], df["_unit"], df["_time"])
print(f"\ncross-check, double-demeaning coefficient: {b_fast:+.6f} "
      f"(difference from OLS: {b_fast - b:+.2e})")
assert abs(b_fast - b) < 1e-8, "fast routine does not reproduce the OLS coefficient"

# ---- cross-check: simple 2x2 difference of means --------------------------------------
pre = df[df["_time"] < start]
post = df[df["_time"] >= start]
mt_pre = pre.loc[pre["_treated"] == 1, "_y"].mean()
mt_post = post.loc[post["_treated"] == 1, "_y"].mean()
mc_pre = pre.loc[pre["_treated"] == 0, "_y"].mean()
mc_post = post.loc[post["_treated"] == 0, "_y"].mean()
d2x2 = (mt_post - mt_pre) - (mc_post - mc_pre)
print("\n=== 2x2 difference of means (no FE) ===")
print(f"treated: {mt_pre:.3f} -> {mt_post:.3f}  (change {mt_post - mt_pre:+.3f})")
print(f"control: {mc_pre:.3f} -> {mc_post:.3f}  (change {mc_post - mc_pre:+.3f})")
print(f"DiD (2x2): {d2x2:+.4f}")
print(f"difference from TWFE estimate: {d2x2 - b:+.4f}")

# ---- sensitivity of the main estimate to the SE choice --------------------------------
res_iid = didlib.twfe(df, cov="iid")
print(f"\n(unclustered SE for reference: {res_iid.bse['_did']:.4f}; "
      f"clustering changes it by a factor {se / res_iid.bse['_did']:.2f})")

out = {
    "specification": "outcome ~ treated*post + unit FE + time FE, all rows, no covariates",
    "coef": float(b), "se_cluster_unit": float(se), "t": float(b / se),
    "p": float(p), "ci95": [float(ci[0]), float(ci[1])],
    "n_obs": int(res.nobs), "n_clusters": int(n_clusters),
    "r2": float(res.rsquared),
    "two_by_two": float(d2x2),
    "two_by_two_cells": {"treated_pre": float(mt_pre), "treated_post": float(mt_post),
                         "control_pre": float(mc_pre), "control_post": float(mc_post)},
    "se_unclustered": float(res_iid.bse["_did"]),
    "coef_fast_check": float(b_fast),
}
(didlib.RESULTS / "main_did.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"\nwrote {(didlib.RESULTS / 'main_did.json').relative_to(didlib.ROOT)}")
