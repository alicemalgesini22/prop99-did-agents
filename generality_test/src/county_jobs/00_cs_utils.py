"""Shared helpers (module, imported by the numbered scripts).

Estimator: Callaway & Sant'Anna (2021) group-time ATT with never-treated
counties as the comparison group, built from 2x2 comparisons; standard errors
clustered by county (with two periods per county this equals the variance of
the county-level change, see att_2x2). Aggregation by cohort size.
"""
import numpy as np
import pandas as pd


def wide(df, unit, time, y):
    return df.pivot(index=unit, columns=time, values=y).sort_index()


def group_map(df, unit, tcol):
    """cohort year per county; NaN for never treated."""
    return df.groupby(unit)[tcol].first()


def att_2x2(Y, group_of, g, t, base, never):
    """ATT(g,t) vs never-treated, base period 'base'. Clustered-by-county SE."""
    gc = [c for c in Y.index if group_of.loc[c] == g]
    d = Y[t] - Y[base]
    est = d.loc[gc].mean() - d.loc[never].mean()
    v = d.loc[gc].var(ddof=1) / len(gc) + d.loc[never].var(ddof=1) / len(never)
    return float(est), float(np.sqrt(v))


def all_cells(Y, group_of, groups, never, periods):
    cells = {}
    for g in groups:
        base = g - 1
        for t in periods:
            if t == base:
                continue
            cells[(g, t)] = att_2x2(Y, group_of, g, t, base, never)
    return cells


def cells_np(D, cohort, periods, groups, never_mask):
    """Point estimates of ATT(g,t) from an n x T array (used by the bootstrap)."""
    out = {}
    pos = {t: j for j, t in enumerate(periods)}
    for g in groups:
        gi = cohort == g
        base = pos[g - 1]
        for t in periods:
            if t == g - 1:
                continue
            d = D[:, pos[t]] - D[:, base]
            out[(g, t)] = float(d[gi].mean() - d[never_mask].mean())
    return out


def agg_overall_pts(pts, groups, ns, post_only=True):
    """Cohort-size-weighted average of cohort means over post (or all) periods."""
    tot = float(sum(ns.values()))
    out = 0.0
    for g in groups:
        ts = [t for (gg, t) in pts if gg == g and (t >= g or not post_only)]
        out += ns[g] / tot * float(np.mean([pts[(g, t)] for t in ts]))
    return out


def agg_event_pts(pts, groups, ns, es):
    res = {}
    for e in es:
        num = den = 0.0
        for g in groups:
            if (g, g + e) in pts:
                num += ns[g] * pts[(g, g + e)]
                den += ns[g]
        res[e] = num / den if den else np.nan
    return res


def boot_indices(cohort, groups, never_mask, n_boot, seed):
    """Cluster (county) resampling; drop draws that lose a cohort or all controls."""
    rng = np.random.default_rng(seed)
    idx = np.arange(len(cohort))
    draws, skipped = [], 0
    for _ in range(n_boot):
        b = rng.choice(idx, size=len(idx), replace=True)
        vals = cohort[b]
        ok = all((vals == g).sum() > 0 for g in groups) and never_mask[b].sum() > 0
        if not ok:
            skipped += 1
            continue
        draws.append(b)
    return draws, skipped
