"""05: inference for the main estimate.

30 treated counties, 45 clusters -> standard errors clustered by county are
usable here; the aggregate CS estimate is reported with a county-level
cluster bootstrap (999 draws, seed 20261125) as well as the clustered SE of
the TWFE cross-check.
"""
import json

import numpy as np
import pandas as pd

OUT = "results/county_jobs"
cfg = json.load(open(f"{OUT}/did_config.json"))

boot = pd.read_csv(f"{OUT}/bootstrap_main_att.csv")["att"].values
main = pd.read_csv(f"{OUT}/main_estimates.csv")
att = float(main.loc[main["estimator"].str.startswith("CS ATT (cohort"), "estimate"].iloc[0])
tw = main.loc[main["estimator"].str.startswith("TWFE")].iloc[0]

se = float(np.std(boot, ddof=1))
lo, hi = np.quantile(boot, [0.025, 0.975])
print(f"[clusters] 45 counties, 30 treated (10 per cohort), 15 never treated")
print(f"[CS main ATT] {att:+.3f}  bootstrap SE {se:.3f}  "
      f"95% percentile CI [{lo:+.3f}, {hi:+.3f}]  draws={len(boot)}")
print(f"[CS main ATT] t = {att/se:.2f}")
print(f"[TWFE] {float(tw['estimate']):+.3f}  cluster SE {float(tw['cluster_se']):.3f}  "
      f"t = {float(tw['estimate'])/float(tw['cluster_se']):.2f}")

pd.DataFrame([{"estimator": "CS ATT (cohort-size weighted, post)",
               "estimate": att, "boot_se": se, "ci_lo": lo, "ci_hi": hi,
               "n_boot": len(boot), "seed": 20261125}]).to_csv(
    f"{OUT}/inference_main.csv", index=False)
print(f"[saved] {OUT}/inference_main.csv")
