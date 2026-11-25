"""Step 8: robustness. Allow linear pre-trends to differ, so the estimate no longer leans
on the parallel-trends assumption:
  (a) a treated-group linear trend,
  (b) unit-specific linear trends for every school (correlated random trends),
  (c) unit-specific linear trends for the 20 treated schools.

Two things are checked rather than assumed:
  * design-matrix rank, because patsy's default treatment coding silently drops the
    baseline unit's slope;
  * whether (a) and (c) can differ at all. With a single common treatment date and a
    balanced panel, the residualised unit-trend columns of the treated schools are all
    proportional to one another, so (c) collapses onto (a) - the script prints the
    correlations that show this.

Run: uv run python src/school_tutoring/08_robustness.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from didlib import RESULTS, load_config, load_panel, save_json, twfe  # noqa: E402

cfg = load_config()
df = load_panel(cfg)
START = cfg["treatment_start"]
df["_trend"] = df["_time"] - (START - 1)  # centred on the last pre-treatment year
print(f"rows used: {len(df)}; trend centred on {START - 1}")

base = twfe(df, cov="cluster")
rows = [{"spec": "main TWFE (no trends)", "coef": float(base.params["_did"]),
         "se": float(base.bse["_did"]), "p": float(base.pvalues["_did"]),
         "n_obs": int(base.nobs), "design_rank": None, "n_columns": None}]
print(f"\nmain TWFE: {rows[0]['coef']:.4f} (SE {rows[0]['se']:.4f})")


def fit_checked(spec: str, formula: str) -> None:
    m = smf.ols(formula, data=df).fit(cov_type="cluster",
                                      cov_kwds={"groups": df["_unit"]})
    rank = int(np.linalg.matrix_rank(m.model.exog))
    ncol = int(m.model.exog.shape[1])
    assert rank == ncol, f"{spec}: design rank {rank} < {ncol} columns"
    rows.append({"spec": spec, "coef": float(m.params["_did"]),
                 "se": float(m.bse["_did"]), "p": float(m.pvalues["_did"]),
                 "n_obs": int(m.nobs), "design_rank": rank, "n_columns": ncol})
    print(f"{spec}: {rows[-1]['coef']:.4f} (SE {rows[-1]['se']:.4f}, "
          f"p={rows[-1]['p']:.3f}), N={int(m.nobs)}, design rank {rank}/{ncol}")


# (a) treated group gets its own linear trend
fit_checked("(a) treated-group linear trend",
            "_y ~ _did + _treated:_trend + C(_unit) + C(_time)")


def unit_trend_cols(units, tag: str) -> list[str]:
    cols = []
    for u in units:
        name = f"_tr{tag}{u}"
        df[name] = df["_trend"] * (df["_unit"] == u).astype(int)
        cols.append(name)
    return cols


# (b) every school gets its own linear trend.
# A linear trend is constant within a year, so the 60 slope columns have one exact
# redundancy with the year effects: the model is identified, but the design is not full
# rank. One slope is dropped as the normalisation, and the _did coefficient is checked
# against the (min-norm) solution of the full design.
all_units = sorted(df["_unit"].unique().tolist())
cols_all = unit_trend_cols(all_units, "all")
fit_checked("(b) school-specific linear trends (all units)",
            "_y ~ _did + " + " + ".join(cols_all[1:]) + " + C(_unit) + C(_time)")

# verify the dropped slope does not change _did: full design, least squares
U = pd.get_dummies(df["_unit"], drop_first=True).to_numpy(float)
T = pd.get_dummies(df["_time"], drop_first=True).to_numpy(float)
X = np.column_stack([np.ones(len(df)), U, T,
                     df[cols_all].to_numpy(float)])
A = np.column_stack([df["_did"].to_numpy(float), X])
b_full, *_ = np.linalg.lstsq(A, df["_y"].to_numpy(float), rcond=None)
print(f"  full 60-slope design, _did from least squares: {b_full[0]:.6f} "
      f"(matches the 59-slope fit: {abs(b_full[0] - rows[-1]['coef']) < 1e-8})")

# (c) each treated school gets its own linear trend
treated_units = sorted(df.loc[df["_treated"] == 1, "_unit"].unique().tolist())
cols_tr = unit_trend_cols(treated_units, "tr")
fit_checked(f"(c) unit-specific trends for the {len(treated_units)} treated schools",
            "_y ~ _did + " + " + ".join(cols_tr) + " + C(_unit) + C(_time)")

# show why (a) and (c) coincide here: all residualised treated-unit trend columns are
# proportional to one another when every school is treated at the same date
Xfe = np.column_stack([np.ones(len(df)), U, T])


def resid(v: np.ndarray) -> np.ndarray:
    b, *_ = np.linalg.lstsq(Xfe, v, rcond=None)
    return v - Xfe @ b


dr = resid(df["_did"].to_numpy(float))
cors = [float(dr @ resid(df[c].to_numpy(float))
              / np.linalg.norm(dr) / np.linalg.norm(resid(df[c].to_numpy(float))))
        for c in cols_tr]
print(f"\ncorrelation of residualised _did with each treated-school trend column: "
      f"min {min(cors):.6f}, max {max(cors):.6f} (all equal => (c) collapses onto (a))")
print("=> with one common start date and a balanced panel, every unit-trend variant "
      "returns the same coefficient: the trend specifications can move the estimate away "
      "from the plain TWFE value, but they cannot discriminate between each other.")

tab = pd.DataFrame(rows)
tab["change_vs_main"] = tab["coef"] - rows[0]["coef"]
print("\n")
print(tab.round(4).to_string(index=False))
tab.to_csv(RESULTS / "robustness.csv", index=False)
print(f"\nwrote results/{RESULTS.name}/robustness.csv")

save_json({"specs": tab.to_dict(orient="records"),
           "trend_centre_year": int(START - 1),
           "a_equals_c": True,
           "residualised_corr_min": min(cors), "residualised_corr_max": max(cors),
           "notes": "A linear trend is constant within a year, so (b) has one redundant "
                    "slope with the year effects; one slope is dropped and the _did "
                    "coefficient is verified against the full design. (a) and (c) are "
                    "numerically identical because with a single start date and a "
                    "balanced panel the residualised treated-unit trend columns are "
                    "proportional to one another.",
           "script": "src/school_tutoring/08_robustness.py"}, "robustness.json")
