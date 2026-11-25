"""07 - Inference: cluster-robust SE by region, plus randomisation (placebo-in-space) inference.

10 treated regions out of 30 clusters is a modest number of treated clusters, so
the cluster-robust SE is reported together with a randomisation test that
reassigns the 10-region treated set at random and re-estimates the TWFE
coefficient each time (sharp null of no effect of the subsidy).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from didlib import (RESULTS, add_treatment_columns, load_config, read_panel,
                    save_json, twfe)

SEED = 20261124
N_DRAWS = 5000

cfg = load_config()
df = add_treatment_columns(read_panel(cfg), cfg)
unit, time, outcome = cfg["unit"], cfg["time"], cfg["outcome"]


def fast_twfe(d: pd.DataFrame, treat_col: str) -> float:
    """TWFE coefficient on a balanced panel: exact two-way within transform."""
    piv_y = d.pivot(index=unit, columns=time, values=outcome).to_numpy(float)
    piv_x = d.pivot(index=unit, columns=time, values=treat_col).to_numpy(float)
    yt = piv_y - piv_y.mean(1, keepdims=True) - piv_y.mean(0, keepdims=True) + piv_y.mean()
    xt = piv_x - piv_x.mean(1, keepdims=True) - piv_x.mean(0, keepdims=True) + piv_x.mean()
    return float((xt * yt).sum() / (xt * xt).sum())


main = twfe(df, cfg, cluster=cfg["cluster"], label="main_twfe_cluster_unit")
beta_obs_fast = fast_twfe(df, "treat_post")
print(f"main TWFE (statsmodels): {main['coef']:.6f}; fast within-transform: {beta_obs_fast:.6f} "
      f"(abs diff {abs(main['coef'] - beta_obs_fast):.2e})")

units = np.array(sorted(df[unit].unique()))
n_treated = len(cfg["treated_units"])
print(f"clusters: {len(units)}; treated clusters: {n_treated}; draws: {N_DRAWS}; seed: {SEED}")

rng = np.random.default_rng(SEED)
post = (df[time] >= cfg["treatment_start"]).to_numpy(int)
unit_arr = df[unit].to_numpy()

betas = np.empty(N_DRAWS)
for b in range(N_DRAWS):
    fake = set(rng.choice(units, size=n_treated, replace=False).tolist())
    df["_fake_tp"] = np.isin(unit_arr, list(fake)).astype(int) * post
    betas[b] = fast_twfe(df, "_fake_tp")
    if (b + 1) % 1000 == 0:
        print(f"  draw {b + 1}/{N_DRAWS}")

df = df.drop(columns=["_fake_tp"])
pd.DataFrame({"draw": np.arange(1, N_DRAWS + 1), "coef": betas}).to_csv(
    RESULTS / "randomisation_null.csv", index=False)

# Rank of the observed estimate among observed + placebo estimates (descending on |coef|)
ge_abs = int((np.abs(betas) >= abs(beta_obs_fast)).sum())
rank_two_sided = ge_abs + 1
p_rank = rank_two_sided / (N_DRAWS + 1)
p_two_sided = (1 + ge_abs) / (N_DRAWS + 1)
p_one_sided_pos = (1 + int((betas >= beta_obs_fast).sum())) / (N_DRAWS + 1)

print(f"placebo draws with |coef| >= observed: {ge_abs} of {N_DRAWS}")
print(f"rank of observed estimate (by |coef|, descending): {rank_two_sided} of {N_DRAWS + 1}")
print(f"placebo p-value = rank / (draws + 1) = {p_rank:.5f}")
print(f"placebo p-value (two-sided, +1 corrected) = {p_two_sided:.5f}")
print(f"placebo p-value (one-sided, positive effect) = {p_one_sided_pos:.5f}")
print(f"placebo null: mean {betas.mean():.3f}, sd {betas.std(ddof=1):.3f}, "
      f"p2.5 {np.percentile(betas, 2.5):.3f}, p97.5 {np.percentile(betas, 97.5):.3f}")

save_json({
    "cluster": cfg["cluster"],
    "n_clusters": int(len(units)),
    "n_treated_clusters": int(n_treated),
    "main_cluster_robust": {k: main[k] for k in ("coef", "se", "t", "p", "ci_lo", "ci_hi", "n_obs")},
    "randomisation": {
        "seed": SEED, "n_draws": N_DRAWS, "n_treated_per_draw": int(n_treated),
        "observed_coef": beta_obs_fast,
        "n_draws_abs_ge_observed": ge_abs,
        "rank_abs_desc": int(rank_two_sided),
        "denominator": N_DRAWS + 1,
        "p_rank": float(p_rank),
        "p_two_sided": float(p_two_sided),
        "p_one_sided_positive": float(p_one_sided_pos),
        "null_mean": float(betas.mean()), "null_sd": float(betas.std(ddof=1)),
        "null_q025": float(np.percentile(betas, 2.5)),
        "null_q975": float(np.percentile(betas, 97.5)),
    },
    "note": "Randomisation test permutes which regions are treated (10 of 30), keeping the "
            "quarter-13 start and the design. It tests the sharp null of no effect.",
}, "inference.json")
