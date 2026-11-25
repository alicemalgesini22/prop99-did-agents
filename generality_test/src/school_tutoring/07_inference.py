"""Step 7: inference. 20 treated units and 60 clusters, so standard errors clustered by
school are the primary inference. As a secondary check, randomisation inference that
re-assigns the 20 treated labels across the 60 schools.

Run: uv run python src/school_tutoring/07_inference.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from didlib import (fast_did_coef, load_config, load_panel, save_json,  # noqa: E402
                    twfe)

SEED = 20261121
N_DRAWS = 2000
np.random.seed(SEED)

cfg = load_config()
df = load_panel(cfg)
UNIT = cfg["cluster"]
treated_units = sorted(df.loc[df["_treated"] == 1, "_unit"].unique().tolist())
all_units = sorted(df["_unit"].unique().tolist())
print(f"rows used: {len(df)}; treated units: {len(treated_units)}; "
      f"clusters: {len(all_units)}")

# ---- primary: clustered SE (reported from the main specification) --------------------
res = twfe(df, cov="cluster")
b = float(res.params["_did"])
se_cl = float(res.bse["_did"])
p_cl = float(res.pvalues["_did"])
print(f"\nprimary: coefficient {b:.4f}, cluster-robust SE {se_cl:.4f} "
      f"({len(all_units)} clusters), p={p_cl:.4f}")

# ---- secondary: randomisation inference over treated labels -------------------------
# Units are the randomisation unit: draw 20 of the 60 schools as 'treated', keep the same
# post indicator, recompute the two-way FE coefficient. Balanced panel, so the
# double-demeaning formula is exact (checked in 05_main_did.py).
unit_series = df["_unit"].to_numpy()
y = df["_y"].to_numpy()
time = df["_time"].to_numpy()
treated_set = set(treated_units)
base_treated = np.isin(unit_series, list(treated_set)).astype(int)
start = cfg["treatment_start"]
post = (time >= start).astype(int)
b_check = fast_did_coef(y, base_treated * post, unit_series, time)
print(f"\nrandomisation check of the double-demeaning formula at the observed labels: "
      f"{b_check:.6f} vs {b:.6f}")

rng = np.random.default_rng(SEED)
draws = np.empty(N_DRAWS)
for i in range(N_DRAWS):
    pick = rng.choice(all_units, size=len(treated_units), replace=False)
    draws[i] = fast_did_coef(y, np.isin(unit_series, pick).astype(int) * post,
                             unit_series, time)
p_ri = float((np.abs(draws) >= abs(b)).mean())
print(f"\nrandomisation inference, {N_DRAWS} draws, seed {SEED}")
print(f"  observed coefficient: {b:.4f}")
print(f"  placebo draws: mean {draws.mean():.4f}, sd {draws.std(ddof=1):.4f}, "
      f"2.5th pct {np.percentile(draws, 2.5):.4f}, "
      f"97.5th pct {np.percentile(draws, 97.5):.4f}")
print(f"  share of |placebo| >= |observed|: {p_ri:.4f}")
rank = int((np.abs(draws) >= abs(b)).sum())
print(f"  draws at least as extreme: {rank} of {N_DRAWS}")

pd.DataFrame({"draw": np.arange(N_DRAWS), "coef": draws}).to_csv(
    Path("results/school_tutoring/randomisation_draws.csv"), index=False)
print("wrote results/school_tutoring/randomisation_draws.csv")

save_json({
    "primary": {"inference": f"cluster by {cfg['cluster']}",
                "n_clusters": len(all_units),
                "coef": b, "se": se_cl, "p_value": p_cl},
    "secondary_randomisation": {
        "inference": "re-assign 20 treated labels among 60 schools",
        "n_draws": N_DRAWS, "seed": SEED,
        "observed_coef": b, "placebo_sd": float(draws.std(ddof=1)),
        "placebo_mean": float(draws.mean()),
        "p_value_two_sided": p_ri, "n_extreme": rank,
        "coef_formula_check": b_check},
    "script": "src/school_tutoring/07_inference.py",
}, "inference.json")
