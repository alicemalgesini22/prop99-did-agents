"""Multiverse of DiD estimates for California / Proposition 99.

Written outside the project agents (with Claude, in the planning chat) and run by hand:
    uv run python src/checks/multiverse.py
Uses only the standard library and numpy (pandas is blocked by Windows application
control on this machine), and none of the agents' code.
Output: results/checks/multiverse.csv
"""
import csv
from pathlib import Path

import numpy as np

DATA = Path("data/raw/california_tobacco.csv")
OUT = Path("results/checks/multiverse.csv")
TREATED, START = 3, 1989

with DATA.open(newline="") as f:
    rows = list(csv.DictReader(f))
state = np.array([int(r["state"]) for r in rows])
year = np.array([int(r["year"]) for r in rows])
y = np.array([float(r["cigsale"]) for r in rows])
print("rows loaded:", len(rows))

years = np.unique(year)
states = np.unique(state)
# Yearly gap: California minus the unweighted mean of the 38 control states
gap = np.array([y[(year == t) & (state == TREATED)].mean() - y[(year == t) & (state != TREATED)].mean()
                for t in years])
G = dict(zip(years.tolist(), gap))
post_years = [t for t in years if t >= START]
post = np.array([G[t] for t in post_years])

def mean_gap(a, b):
    return np.mean([G[t] for t in years if a <= t <= b])

out = []
def add(choice, estimate, note=""):
    out.append({"choice": choice, "estimate": round(float(estimate), 2), "note": note})

# 1. Plain DiD with different pre-periods
add("DiD, pre-period 1970-1988 (plan.md test 1)", post.mean() - mean_gap(1970, START - 1))
add("DiD, pre-period 1970-1987 (drop 1988: possible anticipation)", post.mean() - mean_gap(1970, 1987))
add("DiD, pre-period 1980-1988 only", post.mean() - mean_gap(1980, START - 1))

# 2. Event study, average post effect, with two reference years
for ref in (1988, 1987):
    add(f"Event study, mean post-1989 coefficient, reference {ref}", (post - G[ref]).mean())

# 3. Trend adjustment: linear trend of the gap fitted on different pre windows, extrapolated
for first in (1970, 1975, 1980, 1984):
    pre_t = np.array([t for t in years if first <= t < START])
    slope, intercept = np.polyfit(pre_t, [G[t] for t in pre_t], 1)
    effect = (post - (intercept + slope * np.array(post_years))).mean()
    add(f"Trend-adjusted, linear trend of the gap fitted {first}-1988 (plan.md test 4 uses 1970)",
        effect, f"slope {slope:.3f} per year")

# 4. TWFE with a California-specific linear trend over all years (least squares with dummies)
cols = [np.ones(len(y))]
cols += [(state == s).astype(float) for s in states[1:]]
cols += [(year == t).astype(float) for t in years[1:]]
treat_post = ((state == TREATED) & (year >= START)).astype(float)
cols += [treat_post, (state == TREATED) * (year - 1970.0)]
X = np.column_stack(cols)
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
add("TWFE + California linear trend over all years", beta[-2])

# 5. Placebo rank with California kept in / removed from the control pool
def did(mask, s):
    t_pre = y[mask & (state == s) & (year < START)].mean()
    t_post = y[mask & (state == s) & (year >= START)].mean()
    o_pre = y[mask & (state != s) & (year < START)].mean()
    o_post = y[mask & (state != s) & (year >= START)].mean()
    return (t_post - t_pre) - (o_post - o_pre)

everyone = np.ones(len(y), dtype=bool)
without_ca = state != TREATED
for keep_ca in (True, False):
    est = {s: did(everyone if (s == TREATED or keep_ca) else without_ca, s) for s in states}
    ranked = sorted(est, key=est.get)
    rank = ranked.index(TREATED) + 1
    pool = "kept in" if keep_ca else "removed from"
    add(f"Placebo rank of California, California {pool} the control pool", rank,
        f"p = {rank}/39 = {rank / 39:.3f}")

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["choice", "estimate", "note"])
    w.writeheader()
    w.writerows(out)
for r in out:
    print(f'{r["estimate"]:>8}  {r["choice"]}  {r["note"]}')
print("saved:", OUT)
