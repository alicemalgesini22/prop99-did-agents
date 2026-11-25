"""08 - Robustness: trend-adjusted DiD.

The main threat visible in the data (event study, script 06) is that treated
regions were already on a steeper upward path before quarter 13. This script
adds linear trends for the treated regions and reports how much the DiD
coefficient moves:

  A. one linear trend for the treated group as a whole (treated x time)
  B. one linear trend per treated region (10 extra terms)

Both are estimated on all rows with region and quarter FE, as in the main model.
"""
from __future__ import annotations

import json

import pandas as pd
import numpy as np

from didlib import (RESULTS, add_treatment_columns, load_config, read_panel,
                    save_json, twfe)

cfg = load_config()
df = add_treatment_columns(read_panel(cfg), cfg)

main = twfe(df, cfg, cluster=cfg["cluster"], label="main_no_trends")

# A: treated-group linear trend
rob_a = twfe(df, cfg, extra_terms=["trend_treated"], cluster=cfg["cluster"],
             label="trend_treated_group")

# B: unit-specific linear trends for each treated region
treated_units = [int(u) for u in cfg["treated_units"]]
for u in treated_units:
    df[f"trend_u{u}"] = df["trend"] * (df[cfg["unit"]] == u).astype(int)
rob_b = twfe(df, cfg, extra_terms=[f"trend_u{u}" for u in treated_units],
             cluster=cfg["cluster"], label="trend_treated_unit_specific")

print(f"rows used: {len(df)} (unchanged in all three specifications)")
rows = []
for r in (main, rob_a, rob_b):
    pct = (r["coef"] - main["coef"]) / abs(main["coef"]) * 100
    print(f"{r['label']:32s} coef {r['coef']:8.4f}  SE {r['se']:6.4f}  "
          f"p {r['p']:.4f}  n {r['n_obs']}  change vs main {r['coef'] - main['coef']:+.4f} "
          f"({pct:+.1f}%)")
    rows.append({"spec": r["label"], "coef": r["coef"], "se": r["se"], "t": r["t"],
                 "p": r["p"], "ci_lo": r["ci_lo"], "ci_hi": r["ci_hi"],
                 "n_obs": r["n_obs"], "extra_terms": "; ".join(r["extra_terms"]) or "none",
                 "change_vs_main": r["coef"] - main["coef"],
                 "pct_change_vs_main": pct})

out = pd.DataFrame(rows)
out.to_csv(RESULTS / "robustness.csv", index=False)

# Descriptive context for the trend adjustment: per-region linear slope of the
# outcome over the pre-treatment quarters (q1-q12), computed from the same rows.
time_col, unit_col, outcome = cfg["time"], cfg["unit"], cfg["outcome"]
pre = df.loc[df[time_col] < cfg["treatment_start"]]
slopes = pre.groupby(unit_col).apply(
    lambda g: float(np.polyfit(g[time_col].to_numpy(float), g[outcome].to_numpy(float), 1)[0]),
    include_groups=False)
slopes_by_group = slopes.groupby(df.groupby(unit_col)["treated"].first())
slope_summary = {
    grp_name: {"n_units": int(s.count()), "mean_slope": float(s.mean()),
               "sd_slope": float(s.std()), "min": float(s.min()), "max": float(s.max())}
    for grp_name, s in slopes_by_group
}
print("\npre-treatment (q1-q12) per-region slope of investment on quarter:")
for k, v in slope_summary.items():
    print(f"  treated={k}: {v}")

save_json({
    "main": main,
    "trend_treated_group": rob_a,
    "trend_treated_unit_specific": rob_b,
    "change_group": rob_a["coef"] - main["coef"],
    "change_unit_specific": rob_b["coef"] - main["coef"],
    "pct_change_group": (rob_a["coef"] - main["coef"]) / abs(main["coef"]) * 100,
    "pct_change_unit_specific": (rob_b["coef"] - main["coef"]) / abs(main["coef"]) * 100,
    "pre_period_slope_descriptive": slope_summary,
}, "robustness.json")
print("\nwrote robustness.csv and robustness.json")
