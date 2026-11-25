"""06 - Event study: treated x period dummies, last pre-treatment period as reference."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import didlib as L

cfg = L.load_config()
OUT = Path("results") / L.RUN_DIR
unit, time, outcome = cfg["unit"], cfg["time"], cfg["outcome"]
start = cfg["treatment_start"]

df = L.add_treatment_columns(L.read_panel(cfg), cfg)
print("rows:", len(df))

es, meta = L.event_study(df, cfg, ref=-1, cluster=cfg["cluster"], bin_endpoints=False)
es["calendar_year"] = start + es["rel_time"]
es.to_csv(OUT / "event_study.csv", index=False)
print(es.to_string(index=False))

pre = es[es["rel_time"] < 0]
post = es[es["rel_time"] >= 0]
print(f"\npre-treatment coefficients: {pre['coef'].round(2).tolist()}")
print(f"post-treatment coefficients: {post['coef'].round(2).tolist()}")

# joint test that all pre-treatment coefficients are zero
import numpy as np
from statsmodels.stats.contrast import ContrastResults  # noqa: F401  (import check)
res = None
# refit to get the model object for a Wald test
import statsmodels.formula.api as smf
d = df.copy()
d["rel_bin"] = d["rel_time"]
cols = {}
for p in [int(x) for x in sorted(d.loc[d["treated"] == 1, "rel_bin"].unique()) if int(x) != -1]:
    cols[f"ev_{'m' if p < 0 else 'p'}{abs(p)}"] = ((d["treated"] == 1) & (d["rel_bin"] == p)).astype(int)
d = d.assign(**cols)
formula = f"{outcome} ~ " + " + ".join(cols) + f" + C({unit}) + C({time})"
m = smf.ols(formula, data=d).fit(cov_type="cluster", cov_kwds={"groups": d[unit]})
pre_terms = [c for p, c in zip(
    [int(x) for x in sorted(d.loc[d["treated"] == 1, "rel_bin"].unique()) if int(x) != -1], cols) if p < 0]
R = np.zeros((len(pre_terms), len(m.params)))
for i, t in enumerate(pre_terms):
    R[i, list(m.params.index).index(t)] = 1.0
wt = m.wald_test(R, scalar=True)
meta["pretrend_joint_test"] = {"wald_chi2": float(wt.statistic), "p": float(wt.pvalue),
                               "df_num": len(pre_terms), "terms": pre_terms,
                               "note": "H0: all pre-treatment coefficients = 0; Wald chi2 "
                                       "(not F) from cluster-robust OLS"}
print(f"\njoint pre-trend test: Wald chi2={wt.statistic:.3f} on {len(pre_terms)} df, "
      f"p={wt.pvalue:.4f}")
meta["pre_coefs"] = pre["coef"].tolist()
meta["post_coefs"] = post["coef"].tolist()

fig, ax = plt.subplots(figsize=(8, 4.8))
es_p = es.sort_values("rel_time")
ax.errorbar(es_p["rel_time"], es_p["coef"],
            yerr=1.96 * es_p["se"], fmt="o-", capsize=3, color="C0")
ax.axhline(0, color="grey", linewidth=0.8)
ax.axvline(-0.5, color="black", linestyle="--", linewidth=1)
ax.axvline(0.5, color="black", linestyle=":", linewidth=1)
ax.set_xticks(sorted(es_p["rel_time"].unique()))
ax.set_xlabel(f"years relative to treatment start ({start}); reference = -1")
ax.set_ylabel("coefficient on treated x period (test points)")
ax.set_title("Event study: treated vs control gap by year")
fig.tight_layout()
fig.savefig(OUT / "event_study.png", dpi=150)

with open(OUT / "event_study.json", "w", encoding="utf-8") as fh:
    json.dump(meta, fh, indent=2)
print("\nwrote", OUT / "event_study.csv", "|", OUT / "event_study.png", "|", OUT / "event_study.json")
