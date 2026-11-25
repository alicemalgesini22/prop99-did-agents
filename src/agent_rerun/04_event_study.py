"""Step 6: event study for the agent_rerun run.

One coefficient per year for the treated unit (California) relative to the
reference year 1988 (fixed in plan.md test 2), with unit FE and year FE:
  cigsale ~ [California x year dummies, all years != 1988] + unit FE + year FE
Writes results/agent_rerun/04_event_study.json and 04_event_study.png
"""
import json
import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import didlib

cfg = didlib.load_config()
cols, _ = didlib.read_panel(cfg)

unit = didlib.as_int(cols[cfg["unit"]])
year = didlib.as_int(cols[cfg["time"]])
y = cols[cfg["outcome"]]
is_treated_group = cols[cfg["treatment_group_column"]]
REF = cfg["reference_year_event_study"]
N = len(y)

years = np.arange(year.min(), year.max() + 1)
keep = [int(t) for t in years if t != REF]  # 1970..1987, 1989..2000 -> 30 coefficients

# California x year dummies for every year except the reference
caD = np.column_stack([(is_treated_group & (year == t)).astype(float) for t in keep])
unitD, yearD, unit_levels, year_levels = didlib.fe_dummies(unit, year, ref_year=REF)
# constant + drop-first dummies: the reference cell is (first control unit, 1988).
# A previous version of this script omitted the constant, which silently made
# (control unit 1, 1988) the zero baseline and shifted every coefficient by
# +2 x gap_1988; verified against the group-mean event study.
X = np.column_stack([np.ones(N), caD, unitD, yearD])
ca_names = [f"ca_x_{t}" for t in keep]

b, u, XtX_inv = didlib.ols(y, X)
v = didlib.vcov_classical(X, u, XtX_inv)  # classical; see notes on inference
idx = {nm: i + 1 for i, nm in enumerate(ca_names)}  # +1: constant is column 0
coefs = np.array([b[idx[f"ca_x_{t}"]] for t in keep])
ses = np.array([np.sqrt(v[idx[f"ca_x_{t}"], idx[f"ca_x_{t}"]]) for t in keep])

out_json = os.path.join(didlib.RESULTS_DIR, "04_event_study.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump({
        "reference_year": REF,
        "years": keep,
        "coefficients": coefs.tolist(),
        "se_classical": ses.tolist(),
        "note": "coefficient = California-vs-control gap in that year minus the gap in the reference year; "
                "SEs are classical (1 treated unit -> placebo test is the inference, see 05_placebo)",
    }, f, indent=2)
print(f"wrote {out_json}")

pre = np.array([t < cfg["treatment_start"] for t in keep])
post = ~pre
# descriptive weighted slope of pre coefficients (inverse-variance weights;
# ignores coefficient covariances -- descriptive only)
w = 1.0 / ses[pre] ** 2
tt = np.array(keep, dtype=float)[pre]
denom = np.sum(w) * np.sum(w * tt * tt) - np.sum(w * tt) ** 2
wls_slope = float((np.sum(w) * np.sum(w * tt * coefs[pre]) - np.sum(w * tt) * np.sum(w * coefs[pre])) / denom)
se_slope = float(np.sqrt(1.0 / np.sum(w)))  # known-variance WLS: Var(b) = 1/sum(w); descriptive (covariances ignored)

fig, ax = plt.subplots(figsize=(9, 4.6))
ax.errorbar(np.array(keep)[pre], coefs[pre], yerr=1.96 * ses[pre], fmt="o", ms=4,
            color="#2166ac", label="pre-treatment (1970-1987)")
ax.errorbar(np.array(keep)[post], coefs[post], yerr=1.96 * ses[post], fmt="o", ms=4,
            color="#b2182b", label="post-treatment (1989-2000)")
ax.scatter([REF], [0], marker="s", s=40, color="black", label=f"reference year {REF} (0 by construction)")
ax.axvline(cfg["treatment_start"] - 0.5, color="black", ls="--", lw=1)
ax.axhline(0, color="grey", lw=0.5)
ax.set_xlabel("year")
ax.set_ylabel(f"{cfg['outcome']} gap vs reference year {REF} (packs/person/year)")
ax.set_title(f"Event study: California x year, reference {REF}\n"
             "(95% classical intervals - indicative only, 1 treated unit; see 05_placebo)")
ax.legend(fontsize=8)
fig.tight_layout()
out_png = os.path.join(didlib.RESULTS_DIR, "04_event_study.png")
fig.savefig(out_png, dpi=150)
plt.close(fig)
print(f"wrote {out_png}")

print(f"\npre-treatment coefficients ({int(pre.sum())} years {keep[0]}-{keep[pre.nonzero()[0][-1]]}):")
for t, c, s in zip(np.array(keep)[pre], coefs[pre], ses[pre]):
    print(f"  {t}: {c: 8.3f}  ({s:.3f})")
print(f"descriptive WLS slope of pre coefficients: {wls_slope:.3f} +- {se_slope:.3f} packs/person/year per year")
print("(descriptive only: inverse-variance weights, coefficient covariances ignored)")
print(f"\npost-treatment coefficients:")
for t, c, s in zip(np.array(keep)[post], coefs[post], ses[post]):
    print(f"  {t}: {c: 8.3f}  ({s:.3f})")
