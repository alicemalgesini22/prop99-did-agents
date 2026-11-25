"""05_robustness.py — Robustness: California-specific linear pre-trend (step 8).

(a) TWFE + California-specific linear year trend: adds (state==3)*(year-1970)
    alongside the post dummy, so the treated-unit slope is fitted on the full
    sample (pre + post) with the post jump absorbed by the dummy.
(b) Pre-period-only extrapolation: fit the California-vs-control gap trend on
    1970-1988 ONLY, extrapolate it over 1989-2000, and subtract it from the
    unadjusted 2x2 DiD. This is the version plan.md test 4 asks for.

Reads results/agent/did_config.json. Writes results/agent/robustness_trend.txt.
"""
import json
import pathlib

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = pathlib.Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "results" / "agent" / "did_config.json").read_text())

UNIT, TIME, OUT = CFG["unit"], CFG["time"], CFG["outcome"]
TSTART = CFG["treatment_start"]
TREAT0 = CFG["treated_units"][0]

out_lines = []
def say(x=""):
    print(x)
    out_lines.append(str(x))

df = pd.read_csv(ROOT / CFG["data_path"])
df["treat_"] = ((df[UNIT] == TREAT0) & (df[TIME] >= TSTART)).astype(int)
base = int(df[TIME].min())
post = df[TIME] >= TSTART

# --- (0) unadjusted baseline (same as 03) ---
m0 = smf.ols(f"{OUT} ~ treat_ + C({UNIT}) + C({TIME})", data=df).fit()
say("=== Step 8: robustness to a California-specific linear pre-trend ===")
say(f"(0) Baseline TWFE (no trend): {m0.params['treat_']:.4f}")

# --- (a) TWFE + treated-UNIT linear trend (slope fitted on ALL years) ---
df["unit_trend"] = (df[UNIT] == TREAT0).astype(int) * (df[TIME] - base)
ma = smf.ols(f"{OUT} ~ treat_ + unit_trend + C({UNIT}) + C({TIME})", data=df).fit()
say(f"(a) TWFE + treated-unit trend (state==3)*(year-{base}), slope fitted on "
    "ALL years 1970-2000:")
say(f"    unit_trend (California-specific slope): "
    f"{ma.params['unit_trend']:.4f} packs/yr")
say(f"    treat_ (post jump vs that trend) = average post-period effect: "
    f"{ma.params['treat_']:.4f}")
say(f"    change vs baseline: {ma.params['treat_'] - m0.params['treat_']:.4f}")
say("    CAVEAT: this slope pools the pre-period trend with any trend in the "
    "post-period effect itself; version (b) is the clean pre-period-only fit.")

# --- (b) pre-period-only extrapolation (plan.md test 4) ---
gap_series = (
    df[df[UNIT] == TREAT0].set_index(TIME)[OUT]
    - df[df[UNIT] != TREAT0].groupby(TIME)[OUT].mean()
).sort_index()
pre_g = gap_series[gap_series.index < TSTART]
b1, b0 = np.polyfit(pre_g.index.astype(float), pre_g.values, 1)
say(f"(b) Pre-period-only extrapolation (raw gap = CA minus unweighted control "
    "mean):")
say(f"    pre-period gap trend (1970-{TSTART - 1}): {b1:.4f} packs/yr "
    f"(intercept {b0:.2f})")
did2 = (df.loc[(df[UNIT] == TREAT0) & post, OUT].mean()
        - df.loc[(df[UNIT] == TREAT0) & ~post, OUT].mean()) - (
    df.loc[(df[UNIT] != TREAT0) & post, OUT].mean()
    - df.loc[(df[UNIT] != TREAT0) & ~post, OUT].mean())
mean_post_year = df.loc[post, TIME].mean()
mean_pre_year = df.loc[~post, TIME].mean()
trend_corr = b1 * (mean_post_year - mean_pre_year)
say(f"    unadjusted 2x2 DiD: {did2:.4f}")
say(f"    mean post year {mean_post_year:.1f}, mean pre year {mean_pre_year:.1f}; "
    f"trend correction = {trend_corr:.4f}")
say(f"    trend-adjusted 2x2 effect: {did2 - trend_corr:.4f}")

# pre-period non-linearity check (event study showed flattening near 1988)
w5 = pre_g.loc[pre_g.index >= TSTART - 5]
slope5 = np.polyfit(w5.index.astype(float), w5.values, 1)[0]
say(f"    pre-trend is NOT linear: last-5-years slope (1984-{TSTART - 1}) = "
    f"{slope5:.4f} packs/yr vs full-pre-period {b1:.4f} packs/yr")

say("\nSaved results/agent/robustness_trend.txt")
(ROOT / "results" / "agent" / "robustness_trend.txt").write_text(
    "\n".join(out_lines) + "\n")
