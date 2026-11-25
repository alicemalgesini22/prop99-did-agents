"""03_did_eventstudy.py — Main TWFE DiD (step 5), 2x2 cross-check, and
event study with 1988 as reference (step 6).

Reads results/agent/did_config.json. Writes results/agent/main_did.txt,
results/agent/event_study.csv, results/agent/event_study.png.
"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = pathlib.Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "results" / "agent" / "did_config.json").read_text())

UNIT, TIME, OUT = CFG["unit"], CFG["time"], CFG["outcome"]
TSTART, REF = CFG["treatment_start"], CFG["reference_period"]
TREAT0 = CFG["treated_units"][0]

out_lines = []
def say(x=""):
    print(x)
    out_lines.append(str(x))

df = pd.read_csv(ROOT / CFG["data_path"])
df["treat_"] = ((df[UNIT] == TREAT0) & (df[TIME] >= TSTART)).astype(int)

# ---------- step 5: TWFE ----------
m = smf.ols(f"{OUT} ~ treat_ + C({UNIT}) + C({TIME})", data=df).fit()
say("=== Step 5: Two-way fixed effects DiD ===")
say(f"Formula: {OUT} ~ treat_ + C(state) + C(year), N = {int(m.nobs)} rows")
say(f"treat_ coefficient: {m.params['treat_']:.4f}")
say(f"SE (conventional, iid): {m.bse['treat_']:.4f}, "
    f"95% CI [{m.conf_int().loc['treat_', 0]:.4f}, {m.conf_int().loc['treat_', 1]:.4f}]")
mc = smf.ols(f"{OUT} ~ treat_ + C({UNIT}) + C({TIME})", data=df)\
    .fit(cov_type="cluster", cov_kwds={"groups": df[UNIT]})
say(f"SE (clustered by {UNIT}): {mc.bse['treat_']:.4f}")
say(f"R-squared: {m.rsquared:.4f}")
say("NOTE: only 1 treated unit -> clustered SEs unreliable; see placebo test (04).")

# ---------- 2x2 cross-check ----------
pre = df[TIME] < TSTART
ca_pre = df.loc[(df[UNIT] == TREAT0) & pre, OUT].mean()
ca_post = df.loc[(df[UNIT] == TREAT0) & ~pre, OUT].mean()
co_pre = df.loc[(df[UNIT] != TREAT0) & pre, OUT].mean()
co_post = df.loc[(df[UNIT] != TREAT0) & ~pre, OUT].mean()
did2 = (ca_post - ca_pre) - (co_post - co_pre)
say("\n2x2 difference of means (cross-check):")
say(f"  California: pre {ca_pre:.3f} -> post {ca_post:.3f} (diff {ca_post - ca_pre:.3f})")
say(f"  Control mean: pre {co_pre:.3f} -> post {co_post:.3f} (diff {co_post - co_pre:.3f})")
say(f"  2x2 DiD = {did2:.4f}  (TWFE estimate above: {m.params['treat_']:.4f})")

# ---------- step 6: event study ----------
rel = df[TIME] - TSTART
dummies = {}
name_map = {}
for r in sorted(rel.unique()):
    if r == REF - TSTART:
        continue  # 1988 reference
    safe = f"ev_{'n' if r < 0 else 'p'}{abs(r)}"
    dummies[safe] = ((df[UNIT] == TREAT0) & (rel == r)).astype(int)
    name_map[safe] = int(r)
evdf = pd.concat([df[[OUT, UNIT, TIME]], pd.DataFrame(dummies)], axis=1)
es_terms = " + ".join(dummies.keys())
es = smf.ols(f"{OUT} ~ {es_terms} + C({UNIT}) + C({TIME})", data=evdf).fit(
    cov_type="HC1")

rows = []
for k in dummies:
    r = name_map[k]
    rows.append({"rel_year": r,
                 "year": TSTART + r,
                 "coef": es.params[k], "se": es.bse[k],
                 "ci_lo": es.conf_int().loc[k, 0], "ci_hi": es.conf_int().loc[k, 1]})
es_tab = pd.DataFrame(rows)
es_tab.to_csv(ROOT / "results" / "agent" / "event_study.csv", index=False)

say("\n=== Step 6: event study (1988 = reference) ===")
say("coef = treated-unit deviation vs controls relative to 1988; HC1 SEs")
say(es_tab.round(4).to_string(index=False))
pre_coefs = es_tab.loc[es_tab.rel_year < 0, "coef"]
say(f"\nPre-1989 coefficients: {len(pre_coefs)} of them, mean {pre_coefs.mean():.3f}, "
    f"range [{pre_coefs.min():.3f}, {pre_coefs.max():.3f}]")
# linear pattern check: correlation of pre coefficients with rel_year
x = es_tab.loc[es_tab.rel_year < 0, "rel_year"].astype(float)
slope = np.polyfit(x, pre_coefs, 1)[0]
say(f"OLS slope of pre-period coefficients on relative year: {slope:.3f} packs/yr")
say("(negative slope => gap was already widening before treatment; "
    "positive => narrowing)")

# plot
fig, ax = plt.subplots(figsize=(9, 5))
ax.errorbar(es_tab.rel_year, es_tab.coef, yerr=1.96 * es_tab.se, fmt="o", capsize=3,
            label="coefficient (95% CI, HC1)")
ax.axvline(-0.5, color="red", ls=":", label="treatment start")
ax.axhline(0, color="grey", lw=0.5)
ax.set_xlabel("years relative to 1989 (0 = 1989)")
ax.set_ylabel(f"effect on {OUT} (packs/person/year)")
ax.set_title(f"Event study, {OUT}: treated (California) vs controls, 1988 = reference")
ax.legend()
fig.tight_layout()
fig.savefig(ROOT / "results" / "agent" / "event_study.png", dpi=150)
say("\nSaved results/agent/event_study.csv, event_study.png, main_did.txt")
(ROOT / "results" / "agent" / "main_did.txt").write_text("\n".join(out_lines) + "\n")
