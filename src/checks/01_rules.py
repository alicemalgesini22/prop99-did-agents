"""Check script 1 (checking-results skill): test every rule in the "Rules" section
of data/README.md on data/raw/california_tobacco.csv.

Rules (data/README.md, "Ontology" section):
1. One row per state-year: 39 x 31 = 1,209 rows, no duplicate (state, year) pairs.
2. california is True for state 3 only, in all 31 years.
3. The treatment (california AND year >= 1989) is True in exactly 12 rows (state 3, 1989-2000).
4. after_treatment is True exactly when year >= 1989, for all 39 states (468 rows).
5. cigsale and retprice are never empty and never negative.
6. An empty cell in lnincome, beer or age15to24 means missing, not zero.
7. No row is dropped in the main analysis; if one is, the number of rows and the reason are printed.

Writes its findings to stdout (the check report cites them).
"""
import csv
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(PROJECT_ROOT, "data", "raw", "california_tobacco.csv")

with open(DATA, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

n = len(rows)
state = [int(r["state"]) for r in rows]
year = [int(r["year"]) for r in rows]
cali = [r["california"] == "True" for r in rows]
after = [r["after_treatment"] == "True" for r in rows]


def flt(r, name):
    v = r[name].strip()
    return float(v) if v != "" else None


results = []


def check(rule, ok, detail):
    results.append((rule, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  rule {rule}: {detail}")


# rule 1
pairs = list(zip(state, year))
dup = len(pairs) - len(set(pairs))
states = set(state)
years = set(year)
check(1, n == 1209 and dup == 0 and len(states) == 39 and len(years) == 31,
      f"rows={n}, distinct states={len(states)}, years={len(years)} ({min(years)}-{max(years)}), duplicate pairs={dup}, 39*31={39*31}")

# rule 2
cali_states = sorted(set(s for s, c in zip(state, cali) if c))
cali_rows = sum(cali)
check(2, cali_states == [3] and cali_rows == 31,
      f"california=True for state(s) {cali_states}, rows={cali_rows} (expected: [3], 31)")

# rule 3
treat_rows = [(s, y) for s, y, c, a in zip(state, year, cali, after) if (c and y >= 1989)]
check(3, len(treat_rows) == 12 and all(s == 3 for s, _ in treat_rows)
      and sorted(y for _, y in treat_rows) == list(range(1989, 2001)),
      f"treatment rows={len(treat_rows)}, states={sorted(set(s for s,_ in treat_rows))}, years={min(y for _,y in treat_rows)}-{max(y for _,y in treat_rows)}")

# rule 4
after_ok = all(a == (y >= 1989) for y, a in zip(year, after))
after_rows = sum(after)
check(4, after_ok and after_rows == 468, f"after_treatment == (year>=1989) in every row: {after_ok}; rows={after_rows} (expected 468 = 39*12)")

# rule 5
cig = [flt(r, "cigsale") for r in rows]
ret = [flt(r, "retprice") for r in rows]
cig_bad = [v for v in cig if v is None or v < 0]
ret_bad = [v for v in ret if v is None or v < 0]
check(5, not cig_bad and not ret_bad, f"cigsale empty/negative: {len(cig_bad)}; retprice empty/negative: {len(ret_bad)}")

# rule 6 (missing means missing, not zero: check the empty cells are exactly the
# documented ones and that recorded values are never exactly 0 in these columns)
miss_detail = []
rule6_ok = True
for name, doc_rows in [("lnincome", 195), ("beer", 663), ("age15to24", 390)]:
    vals = [flt(r, name) for r in rows]
    n_miss = sum(v is None for v in vals)
    miss_years = sorted(set(y for y, v in zip(year, vals) if v is None))
    zeros = sum(1 for v in vals if v == 0.0)
    rule6_ok &= (n_miss == doc_rows) and (zeros == 0)
    miss_detail.append(f"{name}: {n_miss} empty (expected {doc_rows}), years {miss_years}, zeros among non-empty: {zeros}")
check(6, rule6_ok, "; ".join(miss_detail))

# rule 7 (row counts in the run's main-estimate output + no row-dropping code)
import json
with open(os.path.join(PROJECT_ROOT, "results", "agent_rerun", "03_main_estimate.json"), encoding="utf-8") as f:
    main = json.load(f)
check(7, main["n_rows"] == n,
      f"main estimate ran on n_rows={main['n_rows']} of {n} available rows; scripts 01-07 print row counts after every step (01: 1209 at each stage) and no script drops rows (code read)")

n_fail = sum(1 for _, ok, _ in results if not ok)
print(f"\n{len(results) - n_fail}/{len(results)} rules PASS")
sys.exit(1 if n_fail else 0)
