"""Shared helpers for the region_subsidy DiD run.

Every column name, the treatment start and the treated-unit list come from
results/region_subsidy/did_config.json; nothing here hard-codes a data column.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

RUN_DIR = "region_subsidy"
RESULTS = Path("results") / RUN_DIR
CONFIG_PATH = RESULTS / "did_config.json"


def load_config(path: Path | str = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(obj: dict, name: str) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / name
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)
    return path


def read_panel(cfg: dict) -> pd.DataFrame:
    """Read the raw CSV and type the unit/time columns declared in the config."""
    df = pd.read_csv(cfg["data_path"])
    unit, time = cfg["unit"], cfg["time"]
    df[unit] = pd.to_numeric(df[unit], errors="raise").astype(int)
    df[time] = pd.to_numeric(df[time], errors="raise").astype(int)
    df = df.sort_values([unit, time]).reset_index(drop=True)
    print(f"rows read from {cfg['data_path']}: {len(df)}")
    return df


def add_treatment_columns(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """treated = 1 for treated units in every period; post = 1 from treatment_start on."""
    unit, time, outcome = cfg["unit"], cfg["time"], cfg["outcome"]
    out = df.copy()
    treated_units = set(cfg["treated_units"])
    out["treated"] = out[unit].isin(treated_units).astype(int)
    out["post"] = (out[time] >= cfg["treatment_start"]).astype(int)
    out["treat_post"] = out["treated"] * out["post"]
    out["rel_time"] = out[time] - cfg["treatment_start"]
    out["trend"] = out[time] - out[time].min()
    out["trend_treated"] = out["trend"] * out["treated"]
    out[outcome] = pd.to_numeric(out[outcome], errors="coerce")
    print(f"rows after adding treatment columns (no rows dropped): {len(out)}")
    return out


def drop_missing_outcome(df: pd.DataFrame, cfg: dict, reason: str) -> pd.DataFrame:
    before = len(df)
    out = df.dropna(subset=[cfg["outcome"]]).copy()
    print(f"rows after dropping missing {cfg['outcome']} ({reason}): {before} -> {len(out)}")
    return out


def _fit(formula: str, df: pd.DataFrame, cluster: str | None):
    model = smf.ols(formula, data=df)
    if cluster is None:
        return model.fit(), df
    return model.fit(cov_type="cluster", cov_kwds={"groups": df[cluster]}), df


def twfe(df: pd.DataFrame, cfg: dict, extra_terms: list[str] | None = None,
         cluster: str | None = None, label: str = "main") -> dict:
    """outcome ~ treated x post + unit FE + time FE (+ extra terms)."""
    unit, time, outcome = cfg["unit"], cfg["time"], cfg["outcome"]
    terms = ["treat_post"] + list(extra_terms or [])
    formula = f"{outcome} ~ " + " + ".join(terms) + f" + C({unit}) + C({time})"
    res, used = _fit(formula, df, cluster)
    ci = res.conf_int().loc["treat_post"]
    return {
        "label": label,
        "formula": formula,
        "n_obs": int(res.nobs),
        "n_units": int(used[unit].nunique()),
        "coef": float(res.params["treat_post"]),
        "se": float(res.bse["treat_post"]),
        "t": float(res.tvalues["treat_post"]),
        "p": float(res.pvalues["treat_post"]),
        "ci_lo": float(ci[0]),
        "ci_hi": float(ci[1]),
        "cluster": cluster if cluster else "none (homoskedastic OLS)",
        "r2": float(res.rsquared),
        "extra_terms": list(extra_terms or []),
    }


def simple_2x2(df: pd.DataFrame, cfg: dict) -> dict:
    """Four cell means: (treated post - treated pre) - (control post - control pre)."""
    g = df.groupby(["treated", "post"], observed=True)[cfg["outcome"]].mean()
    tp, tpre, cp, cpre = g.loc[(1, 1)], g.loc[(1, 0)], g.loc[(0, 1)], g.loc[(0, 0)]
    return {
        "mean_treated_post": float(tp), "mean_treated_pre": float(tpre),
        "mean_control_post": float(cp), "mean_control_pre": float(cpre),
        "diff_treated": float(tp - tpre), "diff_control": float(cp - cpre),
        "did_2x2": float((tp - tpre) - (cp - cpre)),
        "n_treated_post": int(((df["treated"] == 1) & (df["post"] == 1)).sum()),
        "n_treated_pre": int(((df["treated"] == 1) & (df["post"] == 0)).sum()),
        "n_control_post": int(((df["treated"] == 0) & (df["post"] == 1)).sum()),
        "n_control_pre": int(((df["treated"] == 0) & (df["post"] == 0)).sum()),
    }


def add_event_dummies(df: pd.DataFrame, cfg: dict, ref: int = -1):
    """Return a copy of df with one treated-x-relative-period dummy per period."""
    d = df.copy()
    periods_all = sorted(int(p) for p in d.loc[d["treated"] == 1, "rel_time"].unique())
    periods = [p for p in periods_all if p != ref]
    cols = {}
    for p in periods:
        cols[f"ev_m{abs(p)}" if p < 0 else f"ev_p{p}"] = (
            (d["treated"] == 1) & (d["rel_time"] == p)
        ).astype(int)
    d = d.assign(**cols)
    return d, cols, periods_all, periods


def event_study(df: pd.DataFrame, cfg: dict, ref: int = -1,
                cluster: str | None = None) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """One treated-x-relative-period dummy per period, reference period omitted.

    Every relative period is kept separate (no endpoint binning): the panel is
    balanced, so each treated unit contributes one observation per period.
    Returns (event_study_table, meta, design_frame_with_dummies).
    """
    unit, time, outcome = cfg["unit"], cfg["time"], cfg["outcome"]
    d, cols, periods_all, periods = add_event_dummies(df, cfg, ref=ref)
    terms = list(cols)
    formula = f"{outcome} ~ " + " + ".join(terms) + f" + C({unit}) + C({time})"
    res, _ = _fit(formula, d, cluster)
    rows = []
    for p, c in zip(periods, terms):
        ci = res.conf_int().loc[c]
        rows.append({"rel_time": p, "term": c, "coef": float(res.params[c]),
                     "se": float(res.bse[c]), "p": float(res.pvalues[c]),
                     "ci_lo": float(ci[0]), "ci_hi": float(ci[1])})
    rows.append({"rel_time": ref, "term": "reference", "coef": 0.0, "se": 0.0,
                 "p": float("nan"), "ci_lo": 0.0, "ci_hi": 0.0})
    es = pd.DataFrame(rows).sort_values("rel_time").reset_index(drop=True)
    meta = {"formula": formula, "n_obs": int(res.nobs), "ref_period": ref,
            "cluster": cluster if cluster else "none",
            "n_event_terms": len(terms),
            "rel_periods_available": periods_all}
    return es, meta, d


def demean_twfe(df: pd.DataFrame, cfg: dict, treat_post_col: str,
                cluster: str | None = None) -> dict:
    """Fast TWFE by two-way within transformation (used in the placebo loop)."""
    unit, time, outcome = cfg["unit"], cfg["time"], cfg["outcome"]
    d = df[[unit, time, outcome, treat_post_col]].dropna().copy()
    y = d[outcome].to_numpy(float)
    x = d[treat_post_col].to_numpy(float)

    def twoway(v: np.ndarray) -> np.ndarray:
        g = pd.DataFrame({unit: d[unit].to_numpy(), time: d[time].to_numpy(), "v": v})
        for _ in range(1000):
            g["v"] = g["v"] - g.groupby(unit, observed=True)["v"].transform("mean")
            g["v"] = g["v"] - g.groupby(time, observed=True)["v"].transform("mean")
            if np.max(np.abs(g.groupby(unit, observed=True)["v"].transform("mean"))) < 1e-11:
                break
        return g["v"].to_numpy()

    yt, xt = twoway(y), twoway(x)
    beta = float((xt @ yt) / (xt @ xt))
    resid = yt - beta * xt
    n = len(yt)
    k = 1 + d[unit].nunique() + d[time].nunique() - 1
    dfc = (n - 1) / (n - k)
    if cluster is None:
        se = float(np.sqrt((resid @ resid) / (n - k) / (xt @ xt)))
    else:
        grp = d[cluster].to_numpy()
        scores = pd.Series(xt * resid).groupby(grp, observed=True).sum().to_numpy()
        g = len(np.unique(grp))
        se = float(np.sqrt(dfc * g / (g - 1) * np.sum(scores ** 2) / (xt @ xt) ** 2))
    return {"coef": beta, "se": se, "n": int(n)}
