"""Shared helpers for the school_tutoring DiD run.

Not an analysis step: this module only loads the run's did_config.json and builds the
treatment variables, so that no analysis script hard-codes a column name.
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RUN = "school_tutoring"
RESULTS = ROOT / "results" / RUN


def load_config() -> dict:
    return json.loads((RESULTS / "did_config.json").read_text(encoding="utf-8"))


def load_panel(cfg: dict) -> pd.DataFrame:
    """Read the raw panel and attach generic role columns.

    Adds: _unit, _time, _y, _treated, _post, _did, _rel (event time in periods).
    Nothing in data/raw is written.
    """
    df = pd.read_csv(ROOT / cfg["data_path"])
    df["_unit"] = df[cfg["unit"]]
    df["_time"] = df[cfg["time"]]
    df["_y"] = df[cfg["outcome"]]

    rule = cfg["treated_rule"]
    df["_treated"] = (df[rule["column"]] == rule["equals"]).astype(int)

    start = cfg["treatment_start"]
    df["_post"] = (df["_time"] >= start).astype(int)
    df["_did"] = df["_treated"] * df["_post"]
    df["_rel"] = df["_time"] - start  # event time; same mapping for both groups
    return df


def twfe(df, extra: str = "", cov: str = "cluster"):
    """Two-way FE regression of _y on _did (+ extra terms), unit and time dummies.

    Standard errors clustered by _unit when cov="cluster" (clusters = units).
    """
    import statsmodels.formula.api as smf

    f = "_y ~ _did + C(_unit) + C(_time)"
    if extra:
        f = f.replace("_did", f"_did + {extra}")
    m = smf.ols(f, data=df)
    if cov == "cluster":
        return m.fit(cov_type="cluster", cov_kwds={"groups": df["_unit"]})
    return m.fit()


def fast_did_coef(y, d, unit, time):
    """Exact two-way-FE coefficient on d for a *balanced* panel, by double demeaning.

    Used only inside loops that need the point estimate many times (no analytic SE).
    Verified against twfe() in 05_main_did.py.
    """
    import numpy as np
    import pandas as pd

    t = pd.DataFrame({"y": np.asarray(y, float), "d": np.asarray(d, float),
                      "i": np.asarray(unit), "t": np.asarray(time)})
    for c in ("y", "d"):
        t[c + "_r"] = (t[c] - t.groupby("i")[c].transform("mean")
                       - t.groupby("t")[c].transform("mean") + t[c].mean())
    dd = float((t["d_r"] ** 2).sum())
    return float((t["d_r"] * t["y_r"]).sum() / dd)


def save_json(obj, name: str) -> None:
    (RESULTS / name).write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
    print(f"wrote results/{RUN}/{name}")
