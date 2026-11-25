"""Step 7: placebo inference for the agent_rerun run.

With 1 treated unit, cluster-robust SEs are not reliable, so per plan.md test 3:
assign the treatment in 1989 to each of the 38 control states in turn,
re-estimate the same TWFE, and report where California's estimate ranks among
the 39 estimates (38 placebos + California). Placebo p-value = rank / 39,
fixed in plan.md ('What would prove me wrong'): rank 1 -> 1/39 ~ 0.026.

Writes results/agent_rerun/05_placebo.json and 05_placebo.png
"""
import json
import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import didlib

cfg = didlib.load_config()
cols, _ = didlib.read_panel(cfg)

unit = didlib.as_int(cols[cfg["unit"]])
year = didlib.as_int(cols[cfg["time"]])
y = cols[cfg["outcome"]]
is_treated_group = cols[cfg["treatment_group_column"]]
t0 = cfg["treatment_start"]
N = len(y)

unitD, yearD, unit_levels, year_levels = didlib.fe_dummies(unit, year, ref_year=int(year.min()))
X_base = np.column_stack([np.ones(N), unitD, yearD])  # treated column appended per placebo


def twfe_beta(treat_vec):
    X = np.column_stack([treat_vec.astype(float), X_base])
    b, u, XtX_inv = didlib.ols(y, X)
    return float(b[0])


estimates = {}
# real treatment first
beta_ca = twfe_beta(is_treated_group & (year >= t0))
estimates[3] = {"estimate": beta_ca, "real": True}

for s in np.unique(unit[~is_treated_group]):  # the 38 control states
    beta_s = twfe_beta((unit == s) & (year >= t0))
    estimates[int(s)] = {"estimate": beta_s, "real": False}

vals = np.array([v["estimate"] for v in estimates.values()])
real_flag = np.array([v["real"] for v in estimates.values()])

# rank of California among the 39 (most negative = rank 1, per plan.md)
order = np.argsort(vals)  # ascending = most negative first
rank_desc = int(np.where(order == np.where(real_flag)[0][0])[0][0]) + 1
p_value = rank_desc / len(vals)

out_json = os.path.join(didlib.RESULTS_DIR, "05_placebo.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump({
        "placebo_p_value_rule": "rank of California among 39 estimates (most negative = 1) / 39, fixed in plan.md",
        "n_placebos": int((~real_flag).sum()),
        "california_estimate": float(beta_ca),
        "california_rank": rank_desc,
        "placebo_p_value": float(p_value),
        "placebo_estimates": {str(k): v["estimate"] for k, v in estimates.items()},
        "placebo_mean": float(vals[~real_flag].mean()),
        "placebo_sd": float(vals[~real_flag].std(ddof=1)),
        "placebo_quantiles": {str(q): float(np.quantile(vals[~real_flag], q)) for q in (0.05, 0.5, 0.95)},
    }, f, indent=2)
print(f"wrote {out_json}")

fig, ax = plt.subplots(figsize=(8.5, 4.2))
placebo_vals = vals[~real_flag]
ax.scatter(np.sort(placebo_vals), np.arange(1, len(placebo_vals) + 1), s=18, color="#4d4d4d",
           label="placebo estimates (38 control states)")
ax.scatter([beta_ca], [rank_desc], s=90, color="#b2182b", marker="D",
           label=f"California (rank {rank_desc} of {len(vals)})")
ax.axvline(0, color="grey", lw=0.5)
ax.set_xlabel(f"TWFE estimate of a placebo treatment in 1989 ({cfg['outcome']}, packs/person/year)")
ax.set_ylabel("rank (most negative = 1)")
ax.set_title("Placebo distribution, 38 control states + California")
ax.legend(fontsize=8, loc="lower right")
fig.tight_layout()
out_png = os.path.join(didlib.RESULTS_DIR, "05_placebo.png")
fig.savefig(out_png, dpi=150)
plt.close(fig)
print(f"wrote {out_png}")

print(f"\nCalifornia estimate: {beta_ca:.4f}")
print(f"placebo estimates: mean {vals[~real_flag].mean():.4f}, sd {vals[~real_flag].std(ddof=1):.4f}, "
      f"min {vals.min():.4f}, max {vals.max():.4f}")
print(f"California rank (most negative = 1): {rank_desc} of {len(vals)}")
print(f"placebo p-value = {rank_desc}/{len(vals)} = {p_value:.4f}")
