"""Mechanism check from plan.md ('Theory'): retprice in California should rise
relative to the control states in 1989.

Same TWFE specification as the main estimate, but with retprice as the outcome,
plus the simple 2x2 difference of means and the 1989-only first-year gap change.

Writes results/agent_rerun/07_mechanism_retprice.json and 07_mechanism_retprice.txt
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import didlib

cfg = didlib.load_config()
cols, _ = didlib.read_panel(cfg)

unit = didlib.as_int(cols[cfg["unit"]])
year = didlib.as_int(cols[cfg["time"]])
p = cols[cfg["mechanism"]]
is_treated_group = cols[cfg["treatment_group_column"]]
treat = is_treated_group & (year >= cfg["treatment_start"])
N = len(cols[cfg["unit"]])

unitD, yearD, unit_levels, year_levels = didlib.fe_dummies(unit, year, ref_year=int(year.min()))
X = np.column_stack([np.ones(N), treat.astype(float), unitD, yearD])
b, u, XtX_inv = didlib.ols(p, X)
beta = float(b[1])
se_cl = float(np.sqrt(didlib.vcov_cluster(X, u, XtX_inv, unit)[1, 1]))

# 2x2 on retprice
pre = year < cfg["treatment_start"]
post = year >= cfg["treatment_start"]
ca_pre = p[pre & is_treated_group].mean()
ca_post = p[post & is_treated_group].mean()
co_pre = p[pre & ~is_treated_group].mean()
co_post = p[post & ~is_treated_group].mean()
did_2x2 = (ca_post - ca_pre) - (co_post - co_pre)

# first treatment year only (1989 vs 1988)
gap_1988 = p[(year == 1988) & is_treated_group].mean() - p[(year == 1988) & ~is_treated_group].mean()
gap_1989 = p[(year == 1989) & is_treated_group].mean() - p[(year == 1989) & ~is_treated_group].mean()

# yearly CA-minus-control retprice gaps around treatment (exact years, computed)
gap_by_year = {int(t): float(p[year == t][is_treated_group[year == t]].mean()
                             - p[year == t][~is_treated_group[year == t]].mean())
               for t in range(1985, 1993)}

res = {
    "twfe_beta_retprice": beta,
    "se_cluster_by_unit": se_cl,
    "retprice_ca_pre": float(ca_pre),
    "retprice_ca_post": float(ca_post),
    "retprice_control_pre": float(co_pre),
    "retprice_control_post": float(co_post),
    "did_2x2_retprice": float(did_2x2),
    "ca_minus_control_gap_1988": float(gap_1988),
    "ca_minus_control_gap_1989": float(gap_1989),
    "gap_change_1988_to_1989": float(gap_1989 - gap_1988),
    "ca_minus_control_gap_by_year_1985_1992": gap_by_year,
}
out_json = os.path.join(didlib.RESULTS_DIR, "07_mechanism_retprice.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2)

lines = []
lines.append("Mechanism check: retprice (unit from file unverified, see data/README.md caveat 4)")
lines.append(f"TWFE beta(treated_post) on retprice = {beta: .3f} (cluster-by-unit SE {se_cl:.3f}; "
             f"1 treated unit -> SE not reliable, this is descriptive)")
lines.append(f"2x2 difference of means on retprice = {did_2x2: .3f}")
lines.append(f"  California: {ca_pre:.2f} (1970-1988) -> {ca_post:.2f} (1989-2000)")
lines.append(f"  controls:   {co_pre:.2f} (1970-1988) -> {co_post:.2f} (1989-2000)")
lines.append(f"CA-minus-control price gap: 1988 {gap_1988:.2f} -> 1989 {gap_1989:.2f} "
             f"(change {gap_1989 - gap_1988:+.2f})")
lines.append("positive = retail price rose in California relative to controls, consistent with the tax")
lines.append("yearly CA-minus-control retprice gap, 1985-1992: "
             + ", ".join(f"{t}: {g:+.2f}" for t, g in gap_by_year.items()))
out_txt = os.path.join(didlib.RESULTS_DIR, "07_mechanism_retprice.txt")
with open(out_txt, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines))
print(f"\nwrote {out_json}\nwrote {out_txt}")
