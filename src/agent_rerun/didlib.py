"""Shared helpers for the agent_rerun DiD run.

Why no pandas: the machine's application-control policy blocks the pandas
wheel binaries (ImportError: DLL load failed ... blocked the file) for
pandas 3.1.1 and 2.3.3 alike, and statsmodels.api imports pandas. All data
handling and estimation here is therefore plain numpy, validated internally
(see results/agent_rerun/summary.md).

Every script reads did_config.json; no column name is hard-coded here.
"""
import csv
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(HERE))  # src/agent_rerun -> src -> project root
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results", "agent_rerun")

CONFIG_PATH = os.path.join(RESULTS_DIR, "did_config.json")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def abspath(p):
    """Resolve a path from the config relative to the project root."""
    return p if os.path.isabs(p) else os.path.join(PROJECT_ROOT, p)


def read_panel(cfg):
    """Read the CSV into a dict of typed numpy arrays.

    Column typing is inferred: bool if all non-empty cells are True/False,
    float if all non-empty cells parse as float (missing cells -> NaN),
    else object. Returns (columns, header).
    """
    path = abspath(cfg["data_path"])
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames)
        rows = list(reader)

    cols = {}
    for name in header:
        raw = [r[name] for r in rows]
        stripped = [c.strip() for c in raw]
        nonempty = [c for c in stripped if c != ""]
        if nonempty and all(c in ("True", "False") for c in nonempty):
            cols[name] = np.array([c == "True" for c in stripped], dtype=bool)
        else:
            try:
                vals = np.array([float(c) if c != "" else np.nan for c in stripped])
                cols[name] = vals
            except ValueError:
                cols[name] = np.array(raw, dtype=object)
    return cols, header


def as_int(x):
    """Assert a float array is integral and return it as int."""
    xi = np.round(x).astype(int)
    assert np.allclose(x, xi), "non-integral values where ints expected"
    return xi


def ols(y, X):
    """OLS via normal equations; returns (beta, resid, (X'X)^-1)."""
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    u = y - X @ b
    return b, u, XtX_inv


def vcov_classical(X, u, XtX_inv):
    N, K = X.shape
    s2 = u @ u / (N - K)
    return s2 * XtX_inv


def vcov_hc1(X, u, XtX_inv):
    N, K = X.shape
    meat = X.T @ (u[:, None] ** 2 * X)
    return (N / (N - K)) * XtX_inv @ meat @ XtX_inv


def vcov_cluster(X, u, XtX_inv, groups):
    """Cluster-robust sandwich with the CR1 small-sample correction."""
    N, K = X.shape
    uniq = np.unique(groups)
    meat = np.zeros((K, K))
    for g in uniq:
        m = groups == g
        s = X[m].T @ u[m]
        meat += np.outer(s, s)
    G = len(uniq)
    c = (G / (G - 1)) * ((N - 1) / (N - K))
    return c * XtX_inv @ meat @ XtX_inv


def fe_dummies(unit_ids, years, ref_year):
    """Unit dummies (drop first unit) and year dummies (drop ref_year).

    Returns (unitD, yearD, unit_levels, year_levels); constant columns of
    ones are added by the caller as needed.
    """
    units = np.unique(unit_ids)
    years_u = np.unique(years)
    unit_levels = units[1:]
    year_levels = np.array([y for y in years_u if y != ref_year])
    unitD = np.column_stack([(unit_ids == g).astype(float) for g in unit_levels])
    yearD = np.column_stack([(years == t).astype(float) for t in year_levels])
    return unitD, yearD, unit_levels, year_levels


def group_means(cols, cfg, mask):
    unit = as_int(cols[cfg["unit"]])
    t = as_int(cols[cfg["time"]])
    y = cols[cfg["outcome"]]
    treated_mask = cols[cfg["treatment_group_column"]] & (t >= cfg["treatment_start"])
    pre = mask & (t < cfg["treatment_start"])
    post = mask & (t >= cfg["treatment_start"])
    ca_pre = pre & cols[cfg["treatment_group_column"]]
    ca_post = post & cols[cfg["treatment_group_column"]]
    co_pre = pre & ~cols[cfg["treatment_group_column"]]
    co_post = post & ~cols[cfg["treatment_group_column"]]
    return {
        "treated_pre": np.nanmean(y[ca_pre]),
        "treated_post": np.nanmean(y[ca_post]),
        "control_pre": np.nanmean(y[co_pre]),
        "control_post": np.nanmean(y[co_post]),
    }
