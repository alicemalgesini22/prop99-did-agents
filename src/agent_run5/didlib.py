"""Shared helpers for the agent_run5 DiD run.

Reads did_config.json for every column name. Implemented with csv + numpy +
scipy because the pandas/statsmodels wheels are blocked in this environment
(Windows application-control policy; verified 16 Nov 2026). Estimators are the
standard ones: OLS by least squares, classical and cluster-robust (CR1)
covariances.
"""
import csv
import json

import numpy as np
from scipy import stats

CONFIG_PATH = "results/agent_run5/did_config.json"


def load_config(path=CONFIG_PATH):
    return json.load(open(path))


def read_panel(path):
    """Read the csv into a dict of column -> list of raw strings, plus row count."""
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    cols = {k: [r[k] for r in rows] for k in rows[0]}
    return cols, len(rows)


def as_float(vals):
    return np.array([np.nan if v.strip() == "" else float(v) for v in vals], dtype=float)


def as_int(vals):
    return np.array([int(float(v)) for v in vals], dtype=int)


def as_bool(vals):
    return np.array([v.strip().lower() == "true" for v in vals], dtype=bool)


def ols(y, X):
    """OLS via least squares. Returns beta, resid, rank, vcov_classical."""
    beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
    u = y - X @ beta
    n, k = X.shape
    sigma2 = float(u @ u) / (n - rank)
    XtX_inv = np.linalg.pinv(X.T @ X)
    vcov = sigma2 * XtX_inv
    return beta, u, rank, vcov


def cluster_vcov(X, u, cluster_ids, rank):
    """CR1 cluster-robust covariance, clustered by the given id array."""
    n, k = X.shape
    XtX_inv = np.linalg.pinv(X.T @ X)
    meat = np.zeros((k, k))
    clusters = np.unique(cluster_ids)
    G = len(clusters)
    for g in clusters:
        idx = np.where(cluster_ids == g)[0]
        Xg = X[idx] * u[idx][:, None]
        meat += Xg.T @ Xg
    c = (G / (G - 1.0)) * ((n - 1.0) / (n - rank))
    return c * XtX_inv @ meat @ XtX_inv


def twfe(y, unit_codes, year_vals, extra_cols, cluster_ids):
    """Two-way fixed effects regression.

    Design: one dummy per unit + one dummy per year (first year dropped to break
    the unit-dummy/year-dummy collinearity) + the given extra columns.
    Returns dict with the coefficient of the FIRST extra column.
    """
    units = np.unique(unit_codes)
    years = np.unique(year_vals)
    n = len(y)
    D_unit = np.zeros((n, len(units)))
    for j, g in enumerate(units):
        D_unit[unit_codes == g, j] = 1.0
    D_year = np.zeros((n, len(years) - 1))
    for j, t in enumerate(years[1:]):
        D_year[year_vals == t, j] = 1.0
    X = np.column_stack([D_unit, D_year] + [np.asarray(c, dtype=float) for c in extra_cols])
    beta, u, rank, vcov = ols(y, X)
    se = np.sqrt(np.diag(vcov))
    coef_pos = X.shape[1] - len(extra_cols)  # first extra column
    se_cl = np.sqrt(np.diag(cluster_vcov(X, u, cluster_ids, rank)))[coef_pos]
    tstat = beta[coef_pos] / se_cl if se_cl > 0 else np.nan
    pval = 2 * stats.t.sf(abs(tstat), df=(len(units) - 1)) if se_cl > 0 else np.nan
    return {
        "coef": float(beta[coef_pos]),
        "se_classical": float(se[coef_pos]),
        "se_cluster": float(se_cl),
        "t_cluster": float(tstat),
        "p_cluster": float(pval),
        "n": int(n),
        "rank": int(rank),
        "clusters": int(len(units)),
        "resid": u,
        "beta_all": beta,
    }
