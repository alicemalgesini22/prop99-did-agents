"""Step 5: main estimate. Two-way fixed effects DiD, plus the 2x2 difference of means.

Specifications reported:
  (1) pooled OLS, no fixed effects  (the plain 2x2 difference of means)
  (2) unit FE only
  (3) year FE only
  (4) unit FE + year FE  <- the main specification in plan.md (test 1)

Standard errors clustered by unit (reported for (4); the others are shown for
orientation only). With a single treated unit clustered SEs are not reliable.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import did_common as dc

cfg = dc.load_config()
p = dc.load_panel(cfg)
unit, time, y, treat = p["unit"], p["time"], p["y"], p["treated"]
cluster = unit if cfg["cluster"] == cfg["unit"] else np.asarray(p["raw"][cfg["cluster"]], dtype=float)

print(f"rows used: {len(y)} (all rows; no filter)")

specs = {
    "pooled_no_FE": dict(unit_fe=False, time_fe=False),
    "unit_FE_only": dict(unit_fe=True, time_fe=False),
    "year_FE_only": dict(unit_fe=False, time_fe=True),
    "twfe_main": dict(unit_fe=True, time_fe=True),
}

rows = []
results = {}
fits = {}
for name, s in specs.items():
    cols = [np.ones((len(y), 1)), treat.reshape(-1, 1)]
    names = ["const", "treated"]
    if s["unit_fe"]:
        ud = dc.dummies(unit); cols.append(ud); names += [f"unit_{i}" for i in range(ud.shape[1])]
    if s["time_fe"]:
        td = dc.dummies(time); cols.append(td); names += [f"year_{i}" for i in range(td.shape[1])]
    X = np.column_stack(cols)
    fit = dc.ols(y, X, names=names, cluster=cluster)
    fits[name] = fit
    ct = dc.coef_table(fit, only=["treated"])["treated"]
    results[name] = {**ct, "n": fit["n"], "k": fit["k"], "r2": fit["r2"],
                     "se_cluster_note": "cluster by unit" }
    print(f"\n[{name}] treated coef = {ct['coef']:+.4f}  se_classic = {ct['se_classic']:.4f}")
    if "se_cluster" in ct:
        dfree = fit["n_clusters"] - 1
        print(f"          se_cluster (G={fit['n_clusters']}, df={dfree}) = {ct['se_cluster']:.4f}  "
              f"t = {ct['t_cluster']:+.3f}  p = {ct['p_cluster']:.4f}")
    print(f"          n = {fit['n']}, k = {fit['k']}, R2 within sample = {fit['r2']:.4f}")
    rows.append({"spec": name, "coef": ct["coef"], "se_classic": ct["se_classic"],
                 "se_cluster": ct.get("se_cluster", np.nan),
                 "t_cluster": ct.get("t_cluster", np.nan), "p_cluster": ct.get("p_cluster", np.nan),
                 "n": fit["n"], "k": fit["k"], "r2": fit["r2"]})

main = results["twfe_main"]
print(f"\nMAIN (plan.md test 1): TWFE treated coefficient = {main['coef']:+.4f} packs per person per year; "
      f"clustered SE = {main['se_cluster']:.4f} (unreliable: 1 treated unit)")

# ---- cross-check: two-way within transformation (FWL), does it give the same number?
def demean(v, g):
    out = v.copy().astype(float)
    df = {}
    for _ in range(200):
        prev = out.copy()
        for k in g:
            sums = np.bincount(k.astype(int) - k.astype(int).min(), weights=out)
            cnt = np.bincount(k.astype(int) - k.astype(int).min())
            out = out - (sums / cnt)[k.astype(int) - k.astype(int).min()]
        if np.max(np.abs(out - prev)) < 1e-13:
            break
    return out

yt = demean(y, [unit, time])
tt = demean(treat, [unit, time])
beta_within = float((tt @ yt) / (tt @ tt))
print(f"\ncross-check, two-way within (FWL) estimate: {beta_within:+.10f}")
print(f"difference from design-matrix estimate: {beta_within - main['coef']:+.2e}")
assert abs(beta_within - main["coef"]) < 1e-6, "within estimator and dummy estimator disagree"

# ---- cross-check: 2x2 difference of means, computed by hand from group means
post = p["post"]
g = p["in_group"]
m = {
    "treated_post": y[g & post].mean(), "treated_pre": y[g & ~post].mean(),
    "control_post": y[~g & post].mean(), "control_pre": y[~g & ~post].mean(),
}
did_2x2 = (m["treated_post"] - m["treated_pre"]) - (m["control_post"] - m["control_pre"])
print("\n2x2 difference of means (means of the outcome, packs per person per year):")
for k, v in m.items():
    print(f"  mean {k:13s} = {v:8.3f}")
print(f"  treated change  = {m['treated_post'] - m['treated_pre']:+.3f}")
print(f"  control change  = {m['control_post'] - m['control_pre']:+.3f}")
print(f"  2x2 DiD         = {did_2x2:+.4f}")
print(f"  difference from TWFE = {did_2x2 - main['coef']:+.4f}")

dc.save_json({"specs": results, "main_spec": "twfe_main",
              "twfe_coef": main["coef"], "twfe_se_cluster": main["se_cluster"],
              "twfe_se_classic": main["se_classic"],
              "n_clusters": fits["twfe_main"]["n_clusters"],
              "within_crosscheck": beta_within,
              "two_by_two": {"cells": m, "did": float(did_2x2)},
              "n_rows": int(len(y))}, "03_main_did.json")
dc.save_csv(rows, "03_main_did_specs.csv")
print("\nwrote results/agent_deepseek/03_main_did.json and 03_main_did_specs.csv")
