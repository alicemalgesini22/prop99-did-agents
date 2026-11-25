"""05 - Main estimate: TWFE with region and quarter FE, plus the simple 2x2 check."""
from __future__ import annotations

import json

from didlib import (RESULTS, add_treatment_columns, load_config, read_panel,
                    save_json, simple_2x2, twfe)

cfg = load_config()
df = add_treatment_columns(read_panel(cfg), cfg)
print(f"rows entering the main estimate: {len(df)} (all rows, no covariates)")

main_cluster = twfe(df, cfg, cluster=cfg["cluster"], label="main_twfe_cluster_unit")
print(json.dumps(main_cluster, indent=2))
print(f"\nTWFE coefficient: {main_cluster['coef']:.4f} (SE {main_cluster['se']:.4f}, "
      f"t {main_cluster['t']:.2f}, p {main_cluster['p']:.4f}), "
      f"95% CI [{main_cluster['ci_lo']:.4f}, {main_cluster['ci_hi']:.4f}]")

main_ols = twfe(df, cfg, cluster=None, label="main_twfe_homoskedastic")
cells = simple_2x2(df, cfg)
print("\n2x2 cell means:")
for k, v in cells.items():
    print(f"  {k}: {v}")

out = {"main_twfe_cluster_unit": main_cluster, "main_twfe_homoskedastic": main_ols,
       "simple_2x2": cells}
save_json(out, "main_did.json")

rows = [
    {"estimate": "twfe_region_quarter_fe_cluster_unit", "coef": main_cluster["coef"],
     "se": main_cluster["se"], "p": main_cluster["p"],
     "ci_lo": main_cluster["ci_lo"], "ci_hi": main_cluster["ci_hi"],
     "n_obs": main_cluster["n_obs"], "se_type": main_cluster["cluster"]},
    {"estimate": "simple_2x2_difference_of_means", "coef": cells["did_2x2"],
     "se": None, "p": None, "ci_lo": None, "ci_hi": None,
     "n_obs": int(len(df)), "se_type": "none"},
]
import pandas as pd
pd.DataFrame(rows).to_csv(RESULTS / "main_estimates.csv", index=False)
print("\nwrote main_did.json and main_estimates.csv")
