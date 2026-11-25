"""Shared helpers for the school_tutoring DiD run.

All column names, the treatment start and the treated-unit rule come from
did_config.json; nothing here hard-codes a data column name.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

RUN_DIR = "school_support"
CONFIG_PATH = Path("results") / RUN_DIR / "did_config.json"
RESULTS = Path("results") / RUN_DIR


def load_config(path: Path | str = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def read_panel(cfg: dict) -> pd.DataFrame:
    df = pd.read_csv(cfg["data_path"])
    unit, time = cfg["unit"], cfg["time"]
    df[unit] = pd.to_numeric(df[unit], errors="raise").astype(int)
    df[time] = pd.to_numeric(df[time], errors="raise").astype(int)
    df = df.sort_values([unit, time]).reset_index(drop=True)
    return df


def add_treatment_columns(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """treated: 1 for treated units in every period; post: 1 from treatment_start on."""
    unit, time, outcome = cfg["unit"], cfg["time"], cfg["outcome"]
    out = df.copy()
    treated_units = set(cfg["treated_units"])
    out["treated"] = out[unit].isin(treated_units).astype(int)
    out["post"] = (out[time] >= cfg["treatment_start"]).astype(int)
    out["treat_post"] = out["treated"] * out["post"]
    out["rel_time"] = out[time] - cfg["treatment_start"]
    out[outcome] = pd.to_numeric(out[outcome], errors="coerce")
    return out


def _fit(formula: str, df: pd.DataFrame, cluster: str, extra: dict | None = None):
    """OLS via statsmodels formula; cluster-robust SE by `cluster` when given."""
    if extra:
        for k, v in extra.items():
            df = df.assign(**{k: v})
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
    }


def simple_2x2(df: pd.DataFrame, cfg: dict) -> dict:
    """Difference of four cell means: (treated post - treated pre) - (ctrl post - ctrl pre)."""
    g = df.groupby(["treated", "post"], observed=True)[cfg["outcome"]].mean()
    tp, tpre, cp, cpre = g.loc[(1, 1)], g.loc[(1, 0)], g.loc[(0, 1)], g.loc[(0, 0)]
    return {
        "mean_treated_post": float(tp), "mean_treated_pre": float(tpre),
        "mean_control_post": float(cp), "mean_control_pre": float(cpre),
        "diff_treated": float(tp - tpre), "diff_control": float(cp - cpre),
        "did_2x2": float((tp - tpre) - (cp - cpre)),
    }


def event_study(df: pd.DataFrame, cfg: dict, ref: int = -1,
                cluster: str | None = None,
                bin_endpoints: bool = False) -> tuple[pd.DataFrame, dict]:
    """One treated-x-period dummy per relative period, ref omitted.

    bin_endpoints=False keeps every period separate (10 periods here).
    """
    unit, time, outcome = cfg["unit"], cfg["time"], cfg["outcome"]
    d = df.copy()
    lo, hi = int(d["rel_time"].min()), int(d["rel_time"].max())
    d["rel_bin"] = (d["rel_time"].clip(lower=-4, upper=3) if bin_endpoints else d["rel_time"])
    periods = sorted(d.loc[d["treated"] == 1, "rel_bin"].unique())
    periods = [int(p) for p in periods if int(p) != ref]
    cols = {}
    for p in periods:
        cols[f"ev_{'m' if p < 0 else 'p'}{abs(p)}"] = (
            (d["treated"] == 1) & (d["rel_bin"] == p)
        ).astype(int)
    d = d.assign(**cols)
    terms = list(cols)
    formula = f"{outcome} ~ " + " + ".join(terms) + f" + C({unit}) + C({time})"
    res, used = _fit(formula, d, cluster)
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
            "endpoint_binning": [int(lo), int(hi)]}
    return es, meta


def demean_twfe(df: pd.DataFrame, cfg: dict, value_col: str = "treat_post",
                cluster: str | None = None, n_params: int | None = None) -> dict:
    """Fast TWFE by within-unit and within-time demeaning (for placebo loops)."""
    unit, time, outcome = cfg["unit"], cfg["time"], cfg["outcome"]
    d = df[[unit, time, outcome, value_col]].dropna().copy()
    y, x = d[outcome].to_numpy(float), d[value_col].to_numpy(float)

    # alternating projections (two-way within transformation)
    def twoway(v: np.ndarray) -> np.ndarray:
        g = pd.DataFrame({unit: d[unit].to_numpy(), time: d[time].to_numpy(), "v": v})
        for _ in range(500):
            g["v"] = g["v"] - g.groupby(unit, observed=True)["v"].transform("mean")
            g["v"] = g["v"] - g.groupby(time, observed=True)["v"].transform("mean")
            if np.max(np.abs(g.groupby(unit, observed=True)["v"].transform("mean"))) < 1e-10:
                break
        return g["v"].to_numpy()
    yt, xt = twoway(y), twoway(x)
    beta = float((xt @ yt) / (xt @ xt))
    resid = yt - beta * xt
    N = len(yt)
    K = n_params if n_params is not None else 2
    dfc = (N - 1) / (N - K)  # same finite-sample factor statsmodels applies
    if cluster is None:
        se = float(np.sqrt((resid @ resid) / (N - K) / (xt @ xt)))
    else:
        grp = d[cluster].to_numpy()
        # cluster-robust: (X'X)^-1 sum_g (X_g'e_g)^2 (X'X)^-1, with G/(G-1) correction
        scores = pd.Series(xt * resid).groupby(grp, observed=True).sum().to_numpy()
        G = len(np.unique(grp))
        meat = np.sum(scores ** 2)
        se = float(np.sqrt(dfc * G / (G - 1) * meat / (xt @ xt) ** 2))
    return {"coef": beta, "se": se, "n": int(len(yt))}
