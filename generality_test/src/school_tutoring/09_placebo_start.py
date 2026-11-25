"""Step 9: the robustness check aimed at the main threat this data poses.

The main threat is not a visible pre-trend (the event study is flat) but that the treatment
date cannot be verified in the data at all: the treatment flag is constant within school,
so 2017 is taken from the README. Two checks:
  (A) placebo start dates inside the pre-treatment window (2014, 2015), estimated on
      pre-2017 rows only, where no real treatment effect can exist;
  (B) sensitivity to moving the assumed start date to 2016 or 2018 on the full sample.

Run: uv run python src/school_tutoring/09_placebo_start.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from didlib import RESULTS, load_config, load_panel, save_json  # noqa: E402

import statsmodels.formula.api as smf  # noqa: E402

cfg = load_config()
df = load_panel(cfg)
START = cfg["treatment_start"]
print(f"rows used: {len(df)}")


def did_on(frame: pd.DataFrame, start: int) -> dict:
    d = frame.copy()
    d["_did_s"] = d["_treated"] * (d["_time"] >= start).astype(int)
    m = smf.ols("_y ~ _did_s + C(_unit) + C(_time)", data=d).fit(
        cov_type="cluster", cov_kwds={"groups": d["_unit"]})
    return {"start": int(start), "coef": float(m.params["_did_s"]),
            "se": float(m.bse["_did_s"]), "p": float(m.pvalues["_did_s"]),
            "n_obs": int(m.nobs)}


# ---- (A) placebo start dates, pre-treatment rows only -------------------------------
pre = df[df["_time"] < START]
print(f"\n(A) placebo starts on pre-{START} rows: {len(pre)} rows used "
      f"(dropped {len(df) - len(pre)} post-{START} rows so the real programme cannot "
      f"contribute)")
placebo = []
for s in (2014, 2015):
    r = did_on(pre, s)
    placebo.append(r)
    print(f"  fake start {s}: {r['coef']:+.4f} (SE {r['se']:.4f}, p={r['p']:.3f}), "
          f"N={r['n_obs']}")
print("  reading: fake starts in a period with no programme produce estimates of the same "
      "order as the main estimate, so a coefficient of that size is not by itself "
      "evidence of an effect.")

# ---- (B) sensitivity to the assumed start date --------------------------------------
print(f"\n(B) start-date sensitivity, full sample: {len(df)} rows")
sens = []
for s in (START - 1, START, START + 1):
    r = did_on(df, s)
    sens.append(r)
    tag = " (documented)" if s == START else ""
    print(f"  start {s}{tag}: {r['coef']:+.4f} (SE {r['se']:.4f}, p={r['p']:.3f})")

tab = pd.DataFrame(placebo + sens)
tab["kind"] = ["placebo_pre_only"] * len(placebo) + ["start_sensitivity"] * len(sens)
tab.to_csv(RESULTS / "placebo_start_dates.csv", index=False)
print(f"\nwrote results/{RESULTS.name}/placebo_start_dates.csv")

save_json({
    "placebo_pre_only": placebo,
    "start_date_sensitivity": sens,
    "note": "placebo rows restrict to years < treatment_start; sensitivity rows use all "
            "rows and vary the assumed start date",
    "script": "src/school_tutoring/09_placebo_start.py",
}, "placebo_start_dates.json")
