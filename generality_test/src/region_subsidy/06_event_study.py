"""06 - Event study: treated x relative-period dummies, reference = last pre period (q12)."""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from didlib import (RESULTS, add_treatment_columns, event_study, load_config,
                    read_panel, save_json)

cfg = load_config()
df = add_treatment_columns(read_panel(cfg), cfg)
start = cfg["treatment_start"]
ref = -1  # rel_time of the last period before treatment

es, meta, d = event_study(df, cfg, ref=ref, cluster=cfg["cluster"])
print(f"event-study terms estimated: {meta['n_event_terms']}, reference rel_time = {ref}, "
      f"n_obs = {meta['n_obs']}")
print(es[["rel_time", "coef", "se", "p", "ci_lo", "ci_hi"]].to_string(index=False))

es.to_csv(RESULTS / "event_study.csv", index=False)

pre = es[es["rel_time"] < 0]
post = es[es["rel_time"] >= 0]
print(f"\npre-treatment coefficients: {len(pre)} (rel_time {pre['rel_time'].min()} to "
      f"{pre['rel_time'].max()}), mean {pre['coef'].mean():.3f}")
print(f"post-treatment coefficients: {len(post)} (rel_time {post['rel_time'].min()} to "
      f"{post['rel_time'].max()}), mean {post['coef'].mean():.3f}")

# Joint Wald test that all pre-treatment (non-reference) coefficients are zero.
import statsmodels.formula.api as smf
cols = list(pre.loc[pre["term"] != "reference", "term"])
formula = f"{cfg['outcome']} ~ " + " + ".join(list(es.loc[es['term'] != 'reference', 'term'])) \
          + f" + C({cfg['unit']}) + C({cfg['time']})"
res = smf.ols(formula, data=d).fit(cov_type="cluster",
                                   cov_kwds={"groups": d[cfg["cluster"]]})
R = np.zeros((len(cols), len(res.params)))
for i, c in enumerate(cols):
    R[i, list(res.params.index).index(c)] = 1.0
wald = res.wald_test(R, scalar=True)
print(f"joint test of {len(cols)} pre-treatment coefficients = 0: "
      f"chi2 = {float(wald.statistic):.2f}, p = {float(wald.pvalue):.3g}")

# A simple summary of the pre-trend shape: OLS slope of the pre coefficients on rel_time.
slope = np.polyfit(pre["rel_time"].to_numpy(float), pre["coef"].to_numpy(float), 1)[0]
print(f"unweighted slope of pre-period coefficients over rel_time: {slope:.3f} per quarter")
direction = ("flat" if abs(slope) < 0.15 else ("rising" if slope > 0 else "falling"))
print(f"pre-treatment coefficients look: {direction}")

fig, ax = plt.subplots(figsize=(9, 5))
ax.axhline(0, color="grey", lw=0.8)
ax.axvline(-0.5, color="black", ls="--", lw=1.0, label="treatment start")
ax.errorbar(es["rel_time"], es["coef"],
            yerr=[es["coef"] - es["ci_lo"], es["ci_hi"] - es["coef"]],
            fmt="o", ms=4, capsize=3, color="C0")
ax.set_xlabel(f"quarters relative to treatment start (q{start}); -1 is the reference period")
ax.set_ylabel(f"effect on {cfg['outcome']} (million euro)")
ax.set_title("Event study: treated vs control regions, region and quarter FE")
ax.legend()
fig.tight_layout()
fig.savefig(RESULTS / "event_study.png", dpi=150)
print("saved event_study.png")

save_json({
    "meta": meta,
    "reference_rel_time": ref,
    "n_pre_coefs": int(len(pre)),
    "n_post_coefs": int(len(post)),
    "mean_pre_coef": float(pre["coef"].mean()),
    "mean_post_coef": float(post["coef"].mean()),
    "min_pre_coef": float(pre["coef"].min()),
    "max_pre_coef": float(pre["coef"].max()),
    "joint_pre_test": {"chi2": float(wald.statistic), "df": int(len(cols)),
                       "p": float(wald.pvalue)},
    "pre_slope_per_quarter": float(slope),
    "pre_shape": direction,
    "post_rel_coefs": post[["rel_time", "coef", "se", "p"]].to_dict(orient="records"),
}, "event_study.json")
