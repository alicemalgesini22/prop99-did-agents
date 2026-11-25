"""Step 8: robustness.

(a) unit-specific linear trends for the treated firms (required check),
(b) in-time placebo: fake treatment dates inside the pre-period,
(c) sensitivity to which pre-period months form the counterfactual.

Run: uv run python src/firm_training/08_robustness.py
Writes results/firm_training/robustness.json, robustness.csv
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import didlib  # noqa: E402

cfg = didlib.load_config()
df = didlib.load_panel(cfg)
start = cfg["treatment_start"]
rows = []


def fit(data: pd.DataFrame, extra_terms: str = "", label: str = "") -> dict:
    f = "_y ~ _did" + (f" + {extra_terms}" if extra_terms else "") + " + C(_unit) + C(_time)"
    r = smf.ols(f, data=data).fit(cov_type="cluster", cov_kwds={"groups": data["_unit"]})
    return {"spec": label, "coef": float(r.params["_did"]), "se": float(r.bse["_did"]),
            "p": float(r.pvalues["_did"]), "n_obs": int(r.nobs),
            "n_units": int(data["_unit"].nunique())}


main = json.loads((didlib.RESULTS / "main_did.json").read_text(encoding="utf-8"))
rows.append({"spec": "main (unit + time FE)", "coef": main["coef"],
             "se": main["se_cluster_unit"], "p": main["p"], "n_obs": main["n_obs"],
             "n_units": main["n_clusters"]})

# ---- (a) firm-specific linear trends for the treated firms ------------------------------
treated_units = df.loc[df["_treated"] == 1, "_unit"].unique()
d = df.copy()
d["_tr"] = d["_time"] - d["_time"].min()
trend_cols = []
for u in treated_units:
    c = f"tr_firm_{int(u)}"
    d[c] = ((d["_unit"] == u).astype(float)) * d["_tr"]
    trend_cols.append(c)
r_a = fit(d, " + ".join(trend_cols), "unit-specific linear trends for treated firms")
rows.append(r_a)
print(f"(a) with firm-specific linear trends for the 15 treated firms: "
      f"{r_a['coef']:+.4f} (SE {r_a['se']:.4f}, p={r_a['p']:.4g})")
print(f"    change vs main: {r_a['coef'] - main['coef']:+.4f} "
      f"({100 * (r_a['coef'] - main['coef']) / main['coef']:+.1f}% of the main estimate)")

# a single common linear trend for the treated group (less demanding version)
d["_tr_treated"] = d["_tr"] * d["_treated"]
r_a2 = fit(d, "_tr_treated", "one linear trend for all treated firms")
rows.append(r_a2)
print(f"    one common treated-group linear trend instead: {r_a2['coef']:+.4f} "
      f"(SE {r_a2['se']:.4f})")

# ---- (b) in-time placebo: fake treatment dates inside the pre-period -------------------
print("\n(b) in-time placebo (pre-period data only, months 1-24):")
for fake in (13, 19):
    pre = df[df["_time"] < start].copy()
    pre["_did"] = ((pre["_treated"] == 1) & (pre["_time"] >= fake)).astype(int)
    r = fit(pre, label=f"in-time placebo, fake treatment at month {fake}")
    rows.append(r)
    print(f"    fake start month {fake}: {r['coef']:+.4f} (SE {r['se']:.4f}, "
          f"p={r['p']:.3f}, N={r['n_obs']})")

# ---- (c) which pre-period months form the counterfactual -------------------------------
print("\n(c) sensitivity to the pre-period window:")
for lo, hi, lab in [(13, 48, "months 13-48"), (7, 48, "months 7-48"),
                    (1, 36, "months 1-36")]:
    sub = df[(df["_time"] >= lo) & (df["_time"] <= hi)].copy()
    r = fit(sub, label=f"sample restricted to {lab}")
    rows.append(r)
    print(f"    {lab}: {r['coef']:+.4f} (SE {r['se']:.4f}, N={r['n_obs']})")

# skip the middle pre-period entirely: months 1-12 and 25-48
sub = df[(df["_time"] <= 12) | (df["_time"] >= start)].copy()
r = fit(sub, label="pre = months 1-12 only, post = 25-48")
rows.append(r)
print(f"    pre = months 1-12 only, post = 25-48: {r['coef']:+.4f} (SE {r['se']:.4f}, "
      f"N={r['n_obs']})")

# ---- (d) leave-one-treated-firm-out ----------------------------------------------------
loo = []
for u in treated_units:
    sub = df[df["_unit"] != u].copy()
    r = fit(sub, label=f"drop treated firm {int(u)}")
    loo.append((int(u), r["coef"]))
loo_coefs = np.array([c for _, c in loo])
print(f"\n(d) leave-one-treated-firm-out: estimates range {loo_coefs.min():+.3f} to "
      f"{loo_coefs.max():+.3f} (mean {loo_coefs.mean():+.3f})")

tab = pd.DataFrame(rows)
tab.to_csv(didlib.RESULTS / "robustness.csv", index=False)
print("\n" + tab.round(4).to_string(index=False))

out = {"table": rows,
       "trends_common": r_a2,
       "leave_one_out_min": float(loo_coefs.min()),
       "leave_one_out_max": float(loo_coefs.max()),
       "leave_one_out": [{"unit": u, "coef": float(c)} for u, c in loo]}
(didlib.RESULTS / "robustness.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"\nwrote {(didlib.RESULTS / 'robustness.csv').relative_to(didlib.ROOT)} and "
      f"robustness.json")
