"""Step 6: event study. One coefficient per period relative to treatment, last pre-period
(month 24, rel = -1) as reference.

Run: uv run python src/firm_training/06_event_study.py
Writes results/firm_training/event_study.csv, event_study.png, event_study.json
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.formula.api as smf  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import didlib  # noqa: E402

cfg = didlib.load_config()
df = didlib.load_panel(cfg)

# event-time dummies interacted with the treated group, omitting rel = -1
rels = sorted(df["_rel"].unique())
ref = -1
names = {}
for k in rels:
    if k == ref:
        continue
    name = f"ev_m{abs(k)}" if k < 0 else f"ev_p{k}"
    df[name] = ((df["_rel"] == k) & (df["_treated"] == 1)).astype(float)
    names[name] = k

formula = "_y ~ " + " + ".join(names) + " + C(_unit) + C(_time)"
print(f"event-study regression: {len(names)} event-time coefficients, "
      f"reference rel = {ref} (month {cfg['treatment_start'] + ref})")
res = smf.ols(formula, data=df).fit(cov_type="cluster",
                                    cov_kwds={"groups": df["_unit"]})
print(f"N={int(res.nobs)}, clusters={df['_unit'].nunique()}, R2={res.rsquared:.4f}")

tab = pd.DataFrame({
    "rel_month": [names[n] for n in names],
    "coef": [res.params[n] for n in names],
    "se": [res.bse[n] for n in names],
    "p": [res.pvalues[n] for n in names],
}).sort_values("rel_month").reset_index(drop=True)
tab["ci_lo"] = tab["coef"] - 1.96 * tab["se"]
tab["ci_hi"] = tab["coef"] + 1.96 * tab["se"]
tab.to_csv(didlib.RESULTS / "event_study.csv", index=False)
print("\nevent-study coefficients (rel month, coef, se):")
print(tab.round(3).to_string(index=False))

# ---- joint test of the pre-treatment coefficients ------------------------------------
pre_names = [n for n in names if names[n] < ref]
ftest = res.f_test(" = 0, ".join(pre_names) + " = 0")
print(f"\njoint test that all {len(pre_names)} pre-treatment coefficients (rel <= {ref - 1}) "
      f"are zero: F={float(ftest.fvalue):.3f}, p={float(ftest.pvalue):.4f}")

# separate linear trend in the pre-period, from the event-study coefficients
pre_tab = tab[tab["rel_month"] < ref]
slope = np.polyfit(pre_tab["rel_month"], pre_tab["coef"], 1)[0]
print(f"linear fit to the pre-treatment coefficients: slope {slope:+.4f} per month "
      f"({slope * 12:+.3f} per year)")
print(f"mean pre-treatment coefficient: {pre_tab['coef'].mean():+.4f}")
print(f"mean post-treatment coefficient (rel >= 0): "
      f"{tab.loc[tab['rel_month'] >= 0, 'coef'].mean():+.4f}")

# ---- plot -----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 5))
ax.errorbar(tab["rel_month"], tab["coef"],
            yerr=[tab["coef"] - tab["ci_lo"], tab["ci_hi"] - tab["coef"]],
            fmt="o", ms=4, lw=1, color="C0", capsize=2)
ax.axhline(0, color="grey", lw=1)
ax.axvline(-0.5, color="black", ls="--", lw=1)
ax.axvline(ref, color="C1", ls=":", lw=1)
ax.set_xlabel(f"months relative to treatment start (rel = 0 is month {cfg['treatment_start']})")
ax.set_ylabel(f"effect on {cfg['outcome']} (thousand euro)")
ax.set_title("Event study, reference = rel -1; 95% CI, SEs clustered by firm")
fig.tight_layout()
fig.savefig(didlib.RESULTS / "event_study.png", dpi=150)
print(f"\nwrote {(didlib.RESULTS / 'event_study.png').relative_to(didlib.ROOT)} and "
      f"event_study.csv")

out = {
    "reference_rel": ref,
    "n_pre_coefs": len(pre_names),
    "joint_pre_F": float(ftest.fvalue),
    "joint_pre_p": float(ftest.pvalue),
    "pre_linear_slope_per_month": float(slope),
    "mean_pre_coef": float(pre_tab["coef"].mean()),
    "mean_post_coef": float(tab.loc[tab["rel_month"] >= 0, "coef"].mean()),
    "coef_rel0": float(tab.loc[tab["rel_month"] == 0, "coef"].iloc[0]),
    "coef_rel1": float(tab.loc[tab["rel_month"] == 1, "coef"].iloc[0]),
}
(didlib.RESULTS / "event_study.json").write_text(json.dumps(out, indent=2),
                                                encoding="utf-8")
print(f"wrote {(didlib.RESULTS / 'event_study.json').relative_to(didlib.ROOT)}")
