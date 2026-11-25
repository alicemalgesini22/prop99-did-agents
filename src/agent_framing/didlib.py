"""Shared helpers for the agent_framing DiD run.

Why no pandas / statsmodels.api: this machine's application-control policy
blocks the pandas wheel binaries (ImportError: DLL load failed ... blocked
the file, reproduced 16 Nov 2026 for pandas in .venv), and statsmodels.api
imports pandas at import time. All data handling and estimation here is
therefore plain numpy, validated internally (see 01/04 scripts).

Every script reads did_config.json; no column name is hard-coded here.
"""
import csv
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(HERE))  # src/agent_framing -> src -> project root
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results", "agent_framing")

CONFIG_PATH = os.path.join(RESULTS_DIR, "did_config.json")

np.random.seed(42)  # fixed seed (AGENTS.md); analyses below are deterministic


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
                cols[name] = np.array([float(c) if c != "" else np.nan for c in stripped])
            except ValueError:
                cols[name] = np.array(raw, dtype=object)
    return cols, header


def as_int(x):
    """Assert a float array is integral and return it as int."""
    xi = np.round(x).astype(int)
    assert np.allclose(x, xi), "non-integral values where ints expected"
    return xi


def ols(y, X):
    """OLS via least squares; returns (beta, resid, (X'X)^-1 via pinv, rank)."""
    beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
    u = y - X @ beta
    XtX_inv = np.linalg.pinv(X.T @ X)
    return beta, u, XtX_inv, int(rank)


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
    """Unit dummies (drop first unit) and year dummies (drop ref_year)."""
    units = np.unique(unit_ids)
    years_u = np.unique(years)
    unit_levels = units[1:]
    year_levels = np.array([y for y in years_u if y != ref_year])
    unitD = np.column_stack([(unit_ids == g).astype(float) for g in unit_levels])
    yearD = np.column_stack([(years == t).astype(float) for t in year_levels])
    return unitD, yearD, unit_levels, year_levels


def treated_units_mask(cols, cfg):
    """Boolean mask of rows belonging to the treated GROUP (all years)."""
    return np.isin(as_int(cols[cfg["unit"]]), np.array(cfg["treated_units"]))


def treated_post(cols, cfg, treated_units=None):
    """The treatment indicator: treated GROUP unit AND time >= treatment_start.

    treated_units overrides cfg["treated_units"] (used by the placebo test).
    """
    unit = as_int(cols[cfg["unit"]])
    year = as_int(cols[cfg["time"]])
    tu = cfg["treated_units"] if treated_units is None else treated_units
    return np.isin(unit, np.array(tu)) & (year >= cfg["treatment_start"])


def twfe(unit, year, y, treat, cluster, ref_year=1988):
    """Two-way fixed effects DiD: y ~ treat + unit FE + year FE.

    Returns dict with beta and classical / HC1 / cluster SEs.
    """
    unitD, yearD, _, _ = fe_dummies(unit, year, ref_year=ref_year)
    N = len(y)
    X = np.column_stack([np.ones(N), treat.astype(float), unitD, yearD])
    b, u, XtX_inv, rank = ols(y, X)
    assert rank == X.shape[1], f"design matrix not full rank: {rank} vs {X.shape[1]}"
    return {
        "beta": float(b[1]),
        "se_classical": float(np.sqrt(vcov_classical(X, u, XtX_inv)[1, 1])),
        "se_hc1": float(np.sqrt(vcov_hc1(X, u, XtX_inv)[1, 1])),
        "se_cluster": float(np.sqrt(vcov_cluster(X, u, XtX_inv, cluster)[1, 1])),
        "nobs": N,
        "k_params": X.shape[1],
    }


def save_text(name, lines):
    out = os.path.join(RESULTS_DIR, name)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return out
