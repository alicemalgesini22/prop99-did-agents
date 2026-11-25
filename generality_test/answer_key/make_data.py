"""Generates the four panel datasets for the generality test and prints the true effects.
KEEP THIS FILE AND ITS OUTPUT OUTSIDE THE AGENTS' FOLDER until all runs are finished.
numpy only, fixed seed. Run: python make_data.py  (writes the CSVs in the current folder)"""
import csv
import numpy as np

rng = np.random.default_rng(20261121)

def write(name, rows):
    with open(name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

truth = {}

# A. firms x months, common timing, many treated, TRUE EFFECT +8
N, T, START = 50, 48, 25
treated = set(rng.choice(np.arange(1, N + 1), 15, replace=False).tolist())
fe = rng.normal(100, 20, N + 1)
tfe = 0.4 * np.arange(T + 1) + 3 * np.sin(np.arange(T + 1) * 2 * np.pi / 12)
rows = []
for i in range(1, N + 1):
    base_emp = rng.normal(40, 10)
    for t in range(1, T + 1):
        y = fe[i] + tfe[t] + (8.0 if (i in treated and t >= START) else 0) + rng.normal(0, 5)
        rows.append({"firm_id": i, "month": t, "revenue": round(y, 3),
                     "employees": "" if t <= 6 else round(base_emp + rng.normal(0, 2), 1),
                     "joined_training": i in treated, "after_launch": t >= START})
write("firm_training.csv", rows)
truth["A firm_training"] = {"treated": sorted(treated), "start": START, "true_effect": 8.0}

# B. schools x years, common timing, TRUE EFFECT 0, parallel trends
N, years, START = 60, list(range(2012, 2022)), 2017
treated = set(rng.choice(np.arange(1, N + 1), 20, replace=False).tolist())
fe = rng.normal(500, 30, N + 1)
rows = []
for i in range(1, N + 1):
    size = int(rng.integers(300, 1200))
    for t in years:
        y = fe[i] + 1.5 * (t - 2012) + rng.normal(0, 6)
        rows.append({"school_id": i, "year": t, "reading_score": round(y, 2),
                     "students": size + int(rng.integers(-30, 31)), "tutoring_school": i in treated})
write("school_tutoring.csv", rows)
truth["B school_tutoring"] = {"treated": sorted(treated), "start": START, "true_effect": 0.0}

# C. regions x quarters, common timing, TRUE EFFECT 0, treated regions on a steeper trend (pre-trends fail)
N, T, START = 30, 24, 13
treated = set(rng.choice(np.arange(1, N + 1), 10, replace=False).tolist())
fe = rng.normal(50, 8, N + 1)
rows = []
for i in range(1, N + 1):
    for t in range(1, T + 1):
        slope = 0.8 if i in treated else 0.2
        y = fe[i] + slope * t + rng.normal(0, 1.5)
        rows.append({"region_id": i, "quarter": t, "investment": round(y, 3), "subsidy_region": i in treated})
write("region_subsidy.csv", rows)
truth["C region_subsidy"] = {"treated": sorted(treated), "start": START, "true_effect": 0.0,
                             "note": "treated regions grow 0.6 per quarter faster in every quarter, before and after"}

# D. counties x years, STAGGERED, effects differ across cohorts and grow over time
N, years = 45, list(range(2004, 2020))
ids = rng.permutation(np.arange(1, N + 1)).tolist()
cohort = {}
for c in ids[0:10]: cohort[c] = 2008
for c in ids[10:20]: cohort[c] = 2011
for c in ids[20:30]: cohort[c] = 2014
def eff(a, t):
    k = t - a
    if a == 2008: return 1.0 + 0.6 * k
    if a == 2011: return 0.5 + 0.2 * k
    if a == 2014: return 3.0
fe = rng.normal(70, 6, N + 1)
rows, effs = [], []
for i in range(1, N + 1):
    a = cohort.get(i)
    for t in years:
        e = eff(a, t) if (a is not None and t >= a) else 0.0
        if a is not None and t >= a: effs.append(e)
        y = fe[i] + 0.25 * (t - 2004) + e + rng.normal(0, 0.7)
        rows.append({"county": i, "year": t, "employment_rate": round(y, 3),
                     "program_start": a if a is not None else ""})
write("county_jobs.csv", rows)
truth["D county_jobs"] = {"cohorts": {"2008": "1 + 0.6 x years since start", "2011": "0.5 + 0.2 x years since start",
                                     "2014": "3.0 constant"}, "never_treated": 15,
                          "true_ATT_treated_county_years": round(float(np.mean(effs)), 3)}
for k, v in truth.items():
    print(k, v)
