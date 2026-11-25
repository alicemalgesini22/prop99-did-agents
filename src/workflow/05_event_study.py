"""Step 6: Event study — one coefficient per year relative to treatment,
last pre-treatment period as reference. Plotted with 95% CIs.

Reads results/workflow/did_config.json; no column names are hard-coded.
Outputs: results/workflow/06_event_study.txt, 06_event_study.csv, 06_event_study.png
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[2]
CFG_PATH = ROOT / "results" / "workflow" / "did_config.json"
OUT_TXT = ROOT / "results" / "workflow" / "06_event_study.txt"
OUT_CSV = ROOT / "results" / "workflow" / "06_event_study.csv"
OUT_PNG = ROOT / "results" / "workflow" / "06_event_study.png"

cfg = json.loads(CFG_PATH.read_text())
UNIT, TIME, OUTCOME = cfg["unit"], cfg["time"], cfg["outcome"]
DATA = ROOT / cfg["data_path"]

lines = []


def say(s=""):
    print(s)
    lines.append(str(s))


df = pd.read_csv(DATA)
treated_ids = cfg["treated_units"]
start = cfg["treatment_start"]
df = df.assign(is_treated=df[UNIT].isin(treated_ids))

periods = sorted(df[TIME].unique())
reference = max(y for y in periods if y < start)  # last pre-treatment period
say(f"Reference period: {reference} (last pre-treatment year)")
say(f"Rows used: {len(df)} (no filters)")

# one treated x year dummy per period except the reference
ev_cols = []
for y in periods:
    if y == reference:
        continue
    col = f"ev_{y}"
    df[col] = (df.is_treated & (df[TIME] == y)).astype(int)
    ev_cols.append(col)

formula = f"{OUTCOME} ~ {' + '.join(ev_cols)} + C({UNIT}) + C({TIME})"
fit = smf.ols(formula, data=df).fit()
say(f"Model: {formula}")
say(f"N = {int(fit.nobs)}, R-squared = {fit.rsquared:.4f}")
say("")
say(f"{'year':>6} {'coef':>10} {'SE':>8} {'95% CI':>22} {'period':>8}")
rows = []
for col in ev_cols:
    y = int(col.split("_")[1])
    b, se = fit.params[col], fit.bse[col]
    lo, hi = fit.conf_int().loc[col]
    period = "pre" if y < start else "post"
    rows.append({"year": y, "coef": b, "se": se, "ci_lo": lo, "ci_hi": hi,
                 "period": period})
    say(f"{y:>6} {b:>10.3f} {se:>8.3f} [{lo:>10.3f},{hi:>10.3f}] {period:>8}")
say(f"{reference:>6} {'0.000':>10} {'—':>8} {'(reference)':>22} {'pre':>8}")

res = pd.DataFrame(rows)
res.to_csv(OUT_CSV, index=False)

# pre-trend pattern: simple direction of the pre-period coefficients
pre = res[res.period == "pre"]
say("")
say(f"Pre-trend check ({len(pre)} pre-period coefficients vs {reference}):")
say(f"  pre coefficients range: {pre.coef.min():.2f} to {pre.coef.max():.2f}")
say(f"  first pre coef ({pre.year.min()}): {pre.coef.iloc[0]:.2f}; "
    f"last pre coef before ref ({pre.year.iloc[-1]}): {pre.coef.iloc[-2]:.2f}")
say(f"  mean pre coef: {pre.coef.mean():.2f}")
say("  (interpretation printed by hand in the report - script only reports numbers)")

# plot
fig, ax = plt.subplots(figsize=(8.5, 5))
ax.errorbar(res.year, res.coef, yerr=[res.coef - res.ci_lo, res.ci_hi - res.coef],
            fmt="o", capsize=3, color="tab:purple", label="event-study coef (95% CI)")
ax.axhline(0, color="grey", linewidth=0.8)
ax.axvline(start - 0.5, color="black", linestyle="--", linewidth=1,
           label=f"treatment start ({start})")
ax.set_xlabel(TIME)
ax.set_ylabel(f"{OUTCOME} coefficient (treated x year)")
ax.set_title(f"Event study: treated unit x year, reference = {reference}")
ax.legend()
fig.tight_layout()
fig.savefig(OUT_PNG, dpi=150)

print(f"\nSaved {OUT_TXT}, {OUT_CSV}, {OUT_PNG}")
