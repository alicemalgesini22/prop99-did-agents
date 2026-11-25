"""Step 7: Placebo inference — 1 treated unit, so SEs are not reliable.

Assign the treatment (in the same start period) to each control unit in turn,
re-estimate the TWFE, and collect the placebo coefficients. Rank the treated
unit's actual estimate among all 39 (most negative = rank 1).
placebo p-value = rank / number of units.

Reads results/workflow/did_config.json; no column names are hard-coded.
Outputs: results/workflow/07_placebo.txt, 07_placebo.csv
"""
import json
from pathlib import Path

import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[2]
CFG_PATH = ROOT / "results" / "workflow" / "did_config.json"
OUT_TXT = ROOT / "results" / "workflow" / "07_placebo.txt"
OUT_CSV = ROOT / "results" / "workflow" / "07_placebo.csv"

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
all_units = sorted(df[UNIT].unique())
control_units = [u for u in all_units if u not in treated_ids]

say(f"Placebo design: {len(control_units)} control units get a placebo treatment"
    f" starting {start}; plus the 1 actual treated unit = {len(all_units)} estimates.")
say("Each estimate: {OUTCOME} ~ treat_post + unit FE + time FE, all 1,209 rows.")
say("")

rows = []
formula = None
for u in all_units:
    d = df.copy()
    d["treat_post"] = ((d[UNIT] == u) & (d[TIME] >= start)).astype(int)
    formula = f"{OUTCOME} ~ treat_post + C({UNIT}) + C({TIME})"
    fit = smf.ols(formula, data=d).fit()
    b = fit.params["treat_post"]
    rows.append({"unit": u, "is_treated_unit": u in treated_ids, "coef": b})

res = pd.DataFrame(rows)
res = res.sort_values("coef").reset_index(drop=True)
res["rank_most_negative"] = res.index + 1
res.to_csv(OUT_CSV, index=False)

n_units = len(all_units)
treated_rank = int(res.loc[res.is_treated_unit, "rank_most_negative"].iloc[0])
treated_coef = float(res.loc[res.is_treated_unit, "coef"].iloc[0])
placebo = res[~res.is_treated_unit]
say("Placebo coefficients (sorted, most negative first):")
for _, r in res.iterrows():
    mark = "  <-- ACTUAL treated unit" if r.is_treated_unit else ""
    say(f"  rank {r['rank_most_negative']:>2}: unit {r.unit:>2}  coef {r.coef:>8.3f}{mark}")

say("")
say(f"Treated unit {treated_ids} estimate: {treated_coef:.3f}")
say(f"Rank among {n_units} (most negative = 1): {treated_rank}")
say(f"Placebo p-value = rank / {n_units} = {treated_rank}/{n_units} = {treated_rank / n_units:.4f}")
say("")
say(f"Placebo distribution: min {placebo.coef.min():.3f}, "
    f"max {placebo.coef.max():.3f}, mean {placebo.coef.mean():.3f}, "
    f"median {placebo.coef.median():.3f}")
say(f"Placebo coefficients more negative than the treated unit's: "
    f"{int((placebo.coef < treated_coef).sum())}")

OUT_PATH = OUT_TXT
OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\nSaved {OUT_TXT} and {OUT_CSV}")
