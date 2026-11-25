"""Step 7: inference. Cluster-robust SEs (main), plus an in-space placebo test (each control
firm in turn as the treated firm) and a randomisation test with the same treated-group size.

Run: uv run python src/firm_training/07_inference.py
Writes results/firm_training/inference.json, placebo_estimates.csv, permutation_null.csv
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import didlib  # noqa: E402

SEED = 20261121
np.random.seed(SEED)

cfg = didlib.load_config()
df = didlib.load_panel(cfg)
start = cfg["treatment_start"]
units = np.sort(df["_unit"].unique())
times = np.sort(df["_time"].unique())
n_u, n_t = len(units), len(times)
assert len(df) == n_u * n_t, "panel must be balanced for the reshape-based routine"

# wide arrays: rows = units, cols = periods
y = df.pivot(index="_unit", columns="_time", values="_y").loc[units, times].to_numpy()
treated_unit = (df.groupby("_unit")["_treated"].first().loc[units].to_numpy() == 1)
post_col = (times >= start).astype(float)
print(f"panel {n_u} units x {n_t} periods; treated units: {treated_unit.sum()}")

# outcome residualised on unit and time FE once (does not depend on the assignment)
y_r = y - y.mean(axis=1, keepdims=True) - y.mean(axis=0, keepdims=True) + y.mean()


def did_coef(treat_mask: np.ndarray) -> float:
    """TWFE coefficient for an arbitrary treated-firm set (balanced panel, double demeaning)."""
    d = treat_mask[:, None].astype(float) * post_col[None, :]
    d_r = d - d.mean(axis=1, keepdims=True) - d.mean(axis=0, keepdims=True) + d.mean()
    return float((d_r * y_r).sum() / (d_r ** 2).sum())


b_true = did_coef(treated_unit)
print(f"check: routine reproduces the main coefficient: {b_true:+.6f}")

# ---- 1. cluster-robust SE (from step 5) ----------------------------------------------
main = json.loads((didlib.RESULTS / "main_did.json").read_text(encoding="utf-8"))
print(f"\nmain estimate {main['coef']:+.4f}, cluster-robust SE {main['se_cluster_unit']:.4f}, "
      f"t={main['t']:.2f}, p={main['p']:.4g}, {main['n_clusters']} clusters "
      f"({int(treated_unit.sum())} treated)")

# ---- 2. in-space placebo: each control firm in turn is the only treated firm ---------
control_units = units[~treated_unit]
placebo = []
for u in control_units:
    m = np.zeros(n_u, dtype=bool)
    m[units == u] = True
    placebo.append(did_coef(m))
placebo = np.array(placebo)
n_placebo = len(placebo)
rank = int((np.abs(placebo) >= abs(b_true)).sum()) + 1  # 1 = largest
p_placebo = rank / (n_placebo + 1)
print(f"\n=== in-space placebo (single control firm treated), {n_placebo} placebos ===")
print(f"placebo estimates: mean {placebo.mean():+.3f}, sd {placebo.std(ddof=1):.3f}, "
      f"min {placebo.min():+.3f}, max {placebo.max():+.3f}")
print(f"true estimate {b_true:+.4f}: |value| rank {rank} of {n_placebo + 1} "
      f"(1 = largest); placebo p = rank/(n+1) = {p_placebo:.4f}; rank/n = "
      f"{rank / n_placebo:.4f}")
print("note: these placebos have a treated group of size 1, the true design has 15, so the "
      "scale is not comparable; the randomisation test below uses the same group size.")

pd.DataFrame({"unit": control_units, "placebo_coef": placebo}).to_csv(
    didlib.RESULTS / "placebo_estimates.csv", index=False)
print("contamination warning: the comparison group of each of these placebos contains the 15 "
      "truly treated firms, whose large post-pre change pushes every placebo estimate "
      "negative (mean "
      f"{placebo.mean():+.3f}). A clean version restricted to control firms follows.")

# ---- 2b. clean in-space placebo: only control firms in the sample ---------------------
ctrl_rows = np.isin(units, control_units)
y_c = y[ctrl_rows]
y_rc = y_c - y_c.mean(axis=1, keepdims=True) - y_c.mean(axis=0, keepdims=True) + y_c.mean()
placebo_c = []
for j in range(ctrl_rows.sum()):
    m = np.zeros(int(ctrl_rows.sum()), dtype=bool)
    m[j] = True
    d = m[:, None].astype(float) * post_col[None, :]
    d_r = d - d.mean(axis=1, keepdims=True) - d.mean(axis=0, keepdims=True) + d.mean()
    placebo_c.append(float((d_r * y_rc).sum() / (d_r ** 2).sum()))
placebo_c = np.array(placebo_c)
rank_c = int((np.abs(placebo_c) >= abs(b_true)).sum()) + 1
p_placebo_c = rank_c / (len(placebo_c) + 1)
print(f"\n=== clean in-space placebo (control firms only), {len(placebo_c)} placebos ===")
print(f"placebo estimates: mean {placebo_c.mean():+.3f}, sd {placebo_c.std(ddof=1):.3f}, "
      f"min {placebo_c.min():+.3f}, max {placebo_c.max():+.3f}")
print(f"true estimate {b_true:+.4f}: |value| rank {rank_c} of {len(placebo_c) + 1}; "
      f"p = rank/(n+1) = {p_placebo_c:.4f}; rank/n = {rank_c / len(placebo_c):.4f}")
pd.DataFrame({"unit": control_units, "placebo_coef_clean": placebo_c}).to_csv(
    didlib.RESULTS / "placebo_estimates_clean.csv", index=False)

# ---- 3. randomisation test with 15 treated firms -------------------------------------
n_treated = int(treated_unit.sum())
n_draws = 1000
draws = np.empty(n_draws)
for r in range(n_draws):
    m = np.zeros(n_u, dtype=bool)
    m[np.random.choice(n_u, n_treated, replace=False)] = True
    draws[r] = did_coef(m)
p_perm = float((np.abs(draws) >= abs(b_true)).mean())
print(f"\n=== randomisation test: {n_draws} random treated groups of size {n_treated} "
      f"(seed {SEED}) ===")
print(f"null draws: mean {draws.mean():+.3f}, sd {draws.std(ddof=1):.3f}, "
      f"5th pct {np.percentile(draws, 5):+.3f}, 95th pct {np.percentile(draws, 95):+.3f}")
print(f"true estimate {b_true:+.4f}; two-sided p = share(|draw| >= |true|) = {p_perm:.4f}")

pd.DataFrame({"perm_coef": draws}).to_csv(didlib.RESULTS / "permutation_null.csv",
                                          index=False)

out = {
    "main_coef": float(b_true),
    "se_cluster_unit": main["se_cluster_unit"],
    "t": main["t"], "p_cluster": main["p"],
    "n_clusters": int(n_u), "n_treated_units": n_treated,
    "placebo": {"n": int(n_placebo), "mean": float(placebo.mean()),
                "sd": float(placebo.std(ddof=1)),
                "min": float(placebo.min()), "max": float(placebo.max()),
                "rank_of_true": rank, "p_rank_over_n": float(rank / n_placebo),
                "p_rank_over_n_plus_1": float(p_placebo)},
    "placebo_clean_controls_only": {
        "n": int(len(placebo_c)), "mean": float(placebo_c.mean()),
        "sd": float(placebo_c.std(ddof=1)), "min": float(placebo_c.min()),
        "max": float(placebo_c.max()), "rank_of_true": rank_c,
        "p_rank_over_n": float(rank_c / len(placebo_c)),
        "p_rank_over_n_plus_1": float(p_placebo_c)},
    "randomisation": {"n_draws": n_draws, "seed": SEED,
                      "mean": float(draws.mean()), "sd": float(draws.std(ddof=1)),
                      "p_two_sided": p_perm},
}
(didlib.RESULTS / "inference.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"\nwrote {(didlib.RESULTS / 'inference.json').relative_to(didlib.ROOT)}")
