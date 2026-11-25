"""07 - Inference: cluster-robust SEs (primary) + randomisation inference over units
+ a placebo treatment date in the pre-period."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import didlib as L

cfg = L.load_config()
OUT = Path("results") / L.RUN_DIR
unit, time, outcome = cfg["unit"], cfg["time"], cfg["outcome"]
start = cfg["treatment_start"]
SEED = 20261123
N_DRAWS = 2000
np.random.seed(SEED)

df = L.add_treatment_columns(L.read_panel(cfg), cfg)
print("rows:", len(df))

main = json.load(open(OUT / "main_did.json", encoding="utf-8"))["twfe_cluster_unit"]
obs = main["coef"]
units = np.array(sorted(df[unit].unique()))
n_treated = int(df.loc[df["treated"] == 1, unit].nunique())
print(f"observed TWFE coef = {obs:.4f}; treated units = {n_treated} of {len(units)}")
print(f"clustered SE = {main['se']:.4f}, p = {main['p']:.4f}, cluster = {main['cluster']}")

# ---- (a) randomisation inference in space --------------------------------
# Sharp-null permutation: reassign the treated label to n_treated units at random.
n_params = 1 + 1 + (df[unit].nunique() - 1) + (df[time].nunique() - 1)
post = (df[time] >= start).astype(int).to_numpy()

def coef_for(treated_mask_by_unit: dict) -> float:
    t = df[unit].map(treated_mask_by_unit).fillna(0).astype(int).to_numpy()
    d = df[[unit, time, outcome]].copy()
    d["tp"] = t * post
    return L.demean_twfe(d, cfg, value_col="tp", n_params=n_params)["coef"]

draws = []
obs_coef_fast = coef_for({u: 1 for u in set(cfg["treated_units"])})
print(f"fast re-computation of observed coef: {obs_coef_fast:.4f}")

for i in range(N_DRAWS):
    fake = set(np.random.choice(units, n_treated, replace=False).tolist())
    draws.append(coef_for({u: int(u in fake) for u in units}))
draws = np.array(draws)
strict = np.sum(np.abs(draws) >= np.abs(obs_coef_fast))
ri_p = (strict + 1) / (N_DRAWS + 1)
rank = int(np.sum(np.abs(draws) >= np.abs(obs_coef_fast)) + 1)
pd.DataFrame({"draw": np.arange(1, N_DRAWS + 1), "coef": draws}).to_csv(
    OUT / "randomisation_null.csv", index=False)

print(f"\nrandomisation inference ({N_DRAWS} draws of {n_treated}-of-{len(units)} treated assignment, seed {SEED}):")
print(f"  null |coef| >= observed in {strict} draws -> p = {ri_p:.4f}; observed rank (1=most extreme) = {rank}")

# ---- (b) placebo treatment date in the pre-period ------------------------
pre = df[df[time] < start].copy()
fake_start = int(start) - 2  # 2015: 3 fake-pre years (2012-2014), 2 fake-post (2015-2016)
pre["post_fake"] = (pre[time] >= fake_start).astype(int)
pre["tp_fake"] = pre["treated"] * pre["post_fake"]
pl_coef = L.demean_twfe(pre, cfg, value_col="tp_fake",
                        cluster=unit,
                        n_params=1 + 1 + (pre[unit].nunique() - 1) + (pre[time].nunique() - 1))
print(f"\nplacebo date test: fake start {fake_start} on {int(pre[time].min())}-{int(pre[time].max())}: "
      f"coef {pl_coef['coef']:.3f} (SE {pl_coef['se']:.3f})")
print("  (a large placebo effect here would signal pre-existing divergence, not tutoring)")

# ---- (c) how sensitive is the clustered p to the df convention? ----------
from scipy import stats as st  # noqa: F401
out = {
    "primary": {"method": "cluster-robust by unit (CR1, G/(G-1))", **main},
    "randomisation_inference": {
        "n_draws": N_DRAWS, "seed": SEED, "n_treated": n_treated, "n_units": int(len(units)),
        "observed_coef": float(obs_coef_fast), "n_more_extreme": int(strict),
        "p_value": float(ri_p), "rank_of_observed": rank,
        "null_mean": float(draws.mean()), "null_sd": float(draws.std(ddof=1)),
        "null_q025": float(np.quantile(draws, 0.025)), "null_q975": float(np.quantile(draws, 0.975)),
        "note": "two-sided; sharp null of no effect, treatment label permuted across units",
    },
    "placebo_date": {"fake_start": fake_start,
                     "sample": f"{int(pre[time].min())}-{int(pre[time].max())}",
                     "coef": float(pl_coef["coef"]), "se": float(pl_coef["se"])},
}
with open(OUT / "inference.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
print("\nwrote", OUT / "inference.json", "and randomisation_null.csv")
