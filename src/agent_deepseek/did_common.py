"""Shared helpers for the agent_deepseek run.

Why pandas and statsmodels are not used here: `import pandas` fails in this
environment (pandas/_libs/window/indexers*.pyd is blocked by Windows
application control: "Un criterio di controllo dell'applicazione ha bloccato il
file"), and statsmodels.api / statsmodels.regression both import pandas, so they
fail too. numpy, scipy and matplotlib work. The data are therefore read with the
standard-library `csv` module and OLS is solved directly in numpy (design matrix
built by hand; cluster-robust sandwich written out explicitly).

No column name is hard-coded here: every name comes from did_config.json.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy import stats

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "results" / "agent_deepseek"


def load_config() -> dict:
    with open(RESULTS / "did_config.json", encoding="utf-8") as fh:
        return json.load(fh)


def _to_float(s: str) -> float:
    s = s.strip()
    return np.nan if s == "" or s.lower() in {"na", "nan", "none"} else float(s)


def _to_bool(s: str):
    s = s.strip().lower()
    if s in {"true", "false"}:
        return s == "true"
    return None


def read_csv(path: str | Path) -> dict[str, list]:
    """Read the CSV into a dict of column -> list of values (float / bool / str)."""
    p = Path(path)
    if not p.is_absolute():
        p = REPO / p
    with open(p, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    cols = list(rows[0].keys())
    out: dict[str, list] = {c: [] for c in cols}
    for r in rows:
        for c in cols:
            v = r[c]
            b = _to_bool(v)
            if b is not None:
                out[c].append(b)
                continue
            try:
                out[c].append(_to_float(v))
            except ValueError:
                out[c].append(v.strip())
    return out


def load_panel(cfg: dict) -> dict:
    """Return arrays for the roles named in the config, plus the treated flag."""
    d = read_csv(cfg["data_path"])
    unit = np.asarray(d[cfg["unit"]], dtype=float)
    time = np.asarray(d[cfg["time"]], dtype=float)
    y = np.asarray(d[cfg["outcome"]], dtype=float)
    treated_units = [float(u) for u in cfg["treated_units"]]
    in_group = np.isin(unit, treated_units)
    post = time >= float(cfg["treatment_start"])
    treated = (in_group & post).astype(float)
    return {
        "raw": d,
        "unit": unit,
        "time": time,
        "y": y,
        "in_group": in_group,
        "post": post,
        "treated": treated,
    }


def dummies(codes: np.ndarray, drop_first: bool = True) -> np.ndarray:
    """One-hot encode integer codes; drop the first level to avoid collinearity."""
    levels = np.unique(codes)
    if drop_first:
        levels = levels[1:]
    if len(levels) == 0:
        return np.empty((len(codes), 0))
    return np.column_stack([(codes == lev).astype(float) for lev in levels])


def ols(y: np.ndarray, X: np.ndarray, names: list[str] | None = None,
        cluster: np.ndarray | None = None) -> dict:
    """OLS by least squares. Returns params, classic and cluster-robust SEs.

    Cluster-robust covariance uses the usual small-sample correction
    c = G/(G-1) * (N-1)/(N-K) (the Stata `vce(cluster)` default).
    """
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    n, k = X.shape
    if np.linalg.matrix_rank(X) < k:
        raise ValueError(f"design matrix rank deficient: rank {np.linalg.matrix_rank(X)} < k {k}")
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    resid = y - X @ beta
    df = n - k
    sigma2 = float(resid @ resid) / df
    cov_classic = sigma2 * XtX_inv
    out = {
        "n": int(n), "k": int(k), "df": int(df),
        "params": beta,
        "names": names if names is not None else [f"x{i}" for i in range(k)],
        "se_classic": np.sqrt(np.diag(cov_classic)),
        "r2": float(1 - (resid @ resid) / ((y - y.mean()) @ (y - y.mean()))),
        "resid": resid,
        "XtX_inv": XtX_inv,
        "X": X,
    }
    if cluster is not None:
        cluster = np.asarray(cluster)
        groups = np.unique(cluster)
        G = len(groups)
        meat = np.zeros((k, k))
        for g in groups:
            idx = cluster == g
            Xg, ug = X[idx], resid[idx]
            s = Xg.T @ ug
            meat += np.outer(s, s)
        c = (G / (G - 1)) * ((n - 1) / (n - k))
        cov_cl = c * (XtX_inv @ meat @ XtX_inv)
        out["se_cluster"] = np.sqrt(np.diag(cov_cl))
        out["t_cluster"] = beta / out["se_cluster"]
        out["p_cluster"] = 2 * stats.t.sf(np.abs(out["t_cluster"]), df=G - 1)
        out["n_clusters"] = int(G)
        out["cov_cluster"] = cov_cl
    return out


def coef_table(fit: dict, only: list[str] | None = None) -> dict:
    """Tidy dict: name -> {coef, se_classic, se_cluster, t, p} for chosen terms."""
    keep = only if only is not None else fit["names"]
    rows = {}
    for i, nm in enumerate(fit["names"]):
        if nm not in keep:
            continue
        r = {"coef": float(fit["params"][i]), "se_classic": float(fit["se_classic"][i])}
        if "se_cluster" in fit:
            r["se_cluster"] = float(fit["se_cluster"][i])
            r["t_cluster"] = float(fit["t_cluster"][i])
            r["p_cluster"] = float(fit["p_cluster"][i])
        rows[nm] = r
    return rows


def save_json(obj, name: str) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    p = RESULTS / name
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=float)
    return p


def save_csv(rows: list[dict], name: str, fields: list[str] | None = None) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    p = RESULTS / name
    fields = fields or list(rows[0].keys())
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    return p


def fmt(x: float, nd: int = 3) -> str:
    return "nan" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{nd}f}"
