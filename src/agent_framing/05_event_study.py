"""Step 6: event study for the agent_framing run.

One coefficient per year relative to treatment; 1988 (last pre-treatment
year) is the reference. Regressors: [const, CA x 1{year=t} for t != 1988,
unit FE, year FE]. Reports a linear slope fitted on the pre-1989 event
coefficients to characterise their shape.

Writes results/agent_framing/05_event_study.png / .csv / .txt / .json
"""
import csv
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import didlib

cfg = didlib.load_config()
cols, _ = didlib.read_panel(cfg)

unit = didlib.as_int(cols[cfg["unit"]])
year = didlib.as_int(cols[cfg["time"]])
y = cols[cfg["outcome"]]
grp = didlib.treated_units_mask(cols, cfg)
start = cfg["treatment_start"]
ref = cfg["reference_period"]
N = len(y)

years = np.unique(year)
event_cols = [((year == t) & grp).astype(float) for t in years if t != ref]
unitD, yearD, _, _ = didlib.fe_dummies(unit, year, ref_year=ref)
X = np.column_stack([np.ones(N)] + event_cols + [unitD, yearD])
b, u, XtX_inv, rank = didlib.ols(y, X)
assert rank == X.shape[1], "event-study design not full rank"
V = didlib.vcov_classical(X, u, XtX_inv)

ev_years = [int(t) for t in years if t != ref]
coefs = [float(x) for x in b[1:1 + len(ev_years)]]
ses = [float(np.sqrt(V[i, i])) for i in range(1, 1 + len(ev_years))]

pre_mask = [t < start for t in ev_years]
slope_pre = float(np.polyfit(np.array(ev_years)[pre_mask],
                             np.array(coefs)[pre_mask], 1)[0])

fig, ax = plt.subplots(figsize=(9, 5))
ci = 1.96 * np.array(ses)
ax.errorbar(ev_years, coefs, yerr=ci, fmt="o-", color="tab:red",
            capsize=3, label="event coefficient (+/- 1.96 classical SE)")
ax.axvline(start - 0.5, color="black", linestyle="--", linewidth=1)
ax.axhline(0, color="grey", linewidth=0.8)
ax.set_xlabel("Year")
ax.set_ylabel(f"{cfg['outcome']} (packs/person/year), relative to {ref}")
ax.set_title("Event study: California x year, reference 1988\n"
             "(SEs are classical and ignore treated-unit uncertainty)")
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
png = os.path.join(didlib.RESULTS_DIR, "05_event_study.png")
fig.savefig(png, dpi=150)

with open(os.path.join(didlib.RESULTS_DIR, "05_event_study.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["year", "coef", "se_classical", "ci_lo", "ci_hi", "is_pre"])
    for t, c, s in zip(ev_years, coefs, ses):
        w.writerow([t, f"{c:.4f}", f"{s:.4f}", f"{c - 1.96 * s:.4f}",
                    f"{c + 1.96 * s:.4f}", t < start])

pre_coefs = [(t, c) for t, c, p in zip(ev_years, coefs, pre_mask) if p]
lines = [
    f"Event study (agent_framing): {cfg['outcome']}, reference year {ref}",
    f"rows used: {N} (all; no filters); design rank {rank} = {X.shape[1]} columns (full rank)",
    f"number of event coefficients: {len(ev_years)} ({sum(pre_mask)} pre, {len(ev_years) - sum(pre_mask)} post)",
    "",
    "pre-1989 coefficients (year: coef (se)):",
] + [f"  {t}: {c: .3f} ({s:.3f})"
     for (t, c), s in zip(pre_coefs, [s for s, p in zip(ses, pre_mask) if p])] + [
    "",
    f"linear slope of the pre-1989 event coefficients: {slope_pre:.4f} packs/person/year per year",
    f"mean of the 5 event coefficients just before treatment (1984-1987): "
    f"{np.mean([c for t, c in pre_coefs if 1984 <= t <= 1987]):.4f}",
    f"mean of the first 5 post coefficients (1989-1993): "
    f"{np.mean(coefs[sum(pre_mask):sum(pre_mask) + 5]):.4f}",
    "",
    "SEs plotted are classical: the event interactions are identified from a",
    "single treated unit, so no data-driven SE is fully trustworthy here;",
    "the shape (not the bands) is what matters, plus the placebo test.",
    f"wrote {png}",
]
didlib.save_text("05_event_study.txt", lines)

with open(os.path.join(didlib.RESULTS_DIR, "05_event_study.json"), "w", encoding="utf-8") as f:
    json.dump({"years": ev_years, "coefs": coefs, "ses": ses,
               "pre_slope": slope_pre, "reference": ref}, f, indent=2)
print("\n".join(lines))
print(f"\nwrote 05_event_study.png / .csv / .txt / .json in {didlib.RESULTS_DIR}")
