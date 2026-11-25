"""Check script 2 (checking-results skill): recompute the headline estimate as a
2x2 difference of means, independently of the run's code (no didlib, no
statsmodels). The skill says to use "only pandas", but pandas is blocked on this
machine by an application-control policy (see the run's summary, Choices 1), so
this uses the csv module + plain arithmetic instead - same independence, one
dependency less.

Prints the four means and the difference, then recomputes every other number of
the run's summary.md that can be recomputed from the raw file by group means:
raw-gap slopes, group-mean event study vs the run's regression output, retprice
2x2 and yearly gaps.
"""
import csv
import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(PROJECT_ROOT, "data", "raw", "california_tobacco.csv")
RUN = os.path.join(PROJECT_ROOT, "results", "agent_rerun")

with open(DATA, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

cig = {k: float(r["cigsale"]) for k, r in enumerate(rows)}
ret = {k: float(r["retprice"]) for k, r in enumerate(rows)}
state = [int(r["state"]) for r in rows]
year = [int(r["year"]) for r in rows]
cali = [r["california"] == "True" for r in rows]

pre = [k for k in range(len(rows)) if year[k] < 1989]
post = [k for k in range(len(rows)) if year[k] >= 1989]
ca_pre = [k for k in pre if cali[k]]
ca_post = [k for k in post if cali[k]]
co_pre = [k for k in pre if not cali[k]]
co_post = [k for k in post if not cali[k]]


def mean(vals, idx):
    return sum(vals[k] for k in idx) / len(idx)


m_ca_pre = mean(cig, ca_pre)
m_ca_post = mean(cig, ca_post)
m_co_pre = mean(cig, co_pre)
m_co_post = mean(cig, co_post)
did_2x2 = (m_ca_post - m_ca_pre) - (m_co_post - m_co_pre)

print("2x2 difference of means (recomputed from scratch):")
print(f"  California pre  (1970-1988): n={len(ca_pre)}, mean={m_ca_pre:.4f}")
print(f"  California post (1989-2000): n={len(ca_post)}, mean={m_ca_post:.4f}")
print(f"  Controls  pre  (1970-1988): n={len(co_pre)}, mean={m_co_pre:.4f}")
print(f"  Controls  post (1989-2000): n={len(co_post)}, mean={m_co_post:.4f}")
print(f"  2x2 DiD = {did_2x2:.4f}")

# ---- raw-gap yearly values and slopes (independent of run code)
years_all = sorted(set(year))
gap = {t: mean(cig, [k for k in range(len(rows)) if year[k] == t and cali[k]])
       - mean(cig, [k for k in range(len(rows)) if year[k] == t and not cali[k]])
       for t in years_all}


def slope(years_, gaps):
    nb = len(years_)
    sx = sum(years_); sy = sum(gaps)
    sxx = sum(x * x for x in years_); sxy = sum(x * y for x, y in zip(years_, gaps))
    return (nb * sxy - sx * sy) / (nb * sxx - sx * sx)


pre_years = [t for t in years_all if t < 1989]
post_years = [t for t in years_all if t >= 1989]
slope_pre = slope(pre_years, [gap[t] for t in pre_years])
slope_post = slope(post_years, [gap[t] for t in post_years])
print(f"\nraw-gap OLS slopes: pre-1989 {slope_pre:.4f}, post-1988 {slope_post:.4f} (packs/person/year per year)")

# ---- group-mean event study vs the run's 04 output
with open(os.path.join(RUN, "04_event_study.json"), encoding="utf-8") as f:
    es = json.load(f)
ref = es["reference_year"]
max_dev = 0.0
rows_es = []
for t, c in zip(es["years"], es["coefficients"]):
    dev = abs(c - (gap[t] - gap[ref]))
    max_dev = max(max_dev, dev)
    rows_es.append((t, c, gap[t] - gap[ref]))
print(f"\nevent study vs group means (reference {ref}): max |regression - group-mean| = {max_dev:.2e}")

# ---- retprice mechanism
ret_gap = {t: mean(ret, [k for k in range(len(rows)) if year[k] == t and cali[k]])
           - mean(ret, [k for k in range(len(rows)) if year[k] == t and not cali[k]]) for t in years_all}
r_ca_pre, r_ca_post = mean(ret, ca_pre), mean(ret, ca_post)
r_co_pre, r_co_post = mean(ret, co_pre), mean(ret, co_post)
r_2x2 = (r_ca_post - r_ca_pre) - (r_co_post - r_co_pre)
print(f"\nretprice 2x2: CA {r_ca_pre:.4f} -> {r_ca_post:.4f}; controls {r_co_pre:.4f} -> {r_co_post:.4f}; DiD = {r_2x2:.4f}")
print("retprice yearly CA-control gaps 1985-1992: "
      + ", ".join(f"{t}: {ret_gap[t]:+.2f}" for t in range(1985, 1993)))

# ---- comparison table against the run's summary.md
with open(os.path.join(RUN, "03_main_estimate.json"), encoding="utf-8") as f:
    main = json.load(f)
with open(os.path.join(RUN, "02_group_means.json"), encoding="utf-8") as f:
    gm = json.load(f)
with open(os.path.join(RUN, "07_mechanism_retprice.json"), encoding="utf-8") as f:
    mech = json.load(f)
with open(os.path.join(RUN, "05_placebo.json"), encoding="utf-8") as f:
    plac = json.load(f)

print("\nComparison with summary.md / run outputs (SAME = equal to rounding shown):")


def cmp(label, run_val, check_val, decimals=4):
    ok = round(run_val, decimals) == round(check_val, decimals)  # SAME at the rounding shown
    print(f"  {'SAME' if ok else 'DIFFERENT'}  {label}: run {run_val:.{decimals}f} vs recompute {check_val:.{decimals}f}")
    return ok


oks = [
    cmp("California pre mean (quoted 2dp in summary)", 116.21, m_ca_pre, 2),
    cmp("California post mean (quoted 2dp)", 60.35, m_ca_post, 2),
    cmp("Controls pre mean (quoted 2dp)", 130.57, m_co_pre, 2),
    cmp("Controls post mean (quoted 2dp)", 102.06, m_co_post, 2),
    cmp("main TWFE beta = 2x2", main["beta_treated_post"], did_2x2),
    cmp("raw-gap slope pre", gm["slope_gap_pre"], slope_pre),
    cmp("raw-gap slope post", gm["slope_gap_post"], slope_post),
    cmp("event-study coefficients vs group means", 0.0, max_dev),
    cmp("retprice 2x2", mech["did_2x2_retprice"], r_2x2),
    cmp("retprice gap 1988", mech["ca_minus_control_gap_by_year_1985_1992"]["1988"], ret_gap[1988]),
    cmp("retprice gap 1989", mech["ca_minus_control_gap_by_year_1985_1992"]["1989"], ret_gap[1989]),
    cmp("retprice gap 1990", mech["ca_minus_control_gap_by_year_1985_1992"]["1990"], ret_gap[1990]),
    cmp("California placebo estimate", plac["california_estimate"], did_2x2),
]
print(f"\n{sum(oks)}/{len(oks)} recomputed numbers SAME")

# numbers NOT recomputable from group means (regression-based): listed for the record
print("\nNot recomputed here (need the run's regression code; consistent with the")
print("human's independent checks in mistakes.md, errors table, session 3):")
print(f"  trend-adjusted beta (A): {json.load(open(os.path.join(RUN, '06_robustness.json'), encoding='utf-8'))['two_step']['beta_after_detrending']:.4f}")
print(f"  one-step beta (B):       {json.load(open(os.path.join(RUN, '06_robustness.json'), encoding='utf-8'))['one_step']['beta_with_ca_trend_regressor']:.4f}")
print(f"  placebo p-value:         {plac['placebo_p_value']:.4f} (rank {plac['california_rank']} of 39)")
