"""Step 8: robustness. A unit-specific linear pre-trend for the treated unit, plus window checks.

Ro1  TWFE including a treated-unit-specific linear time trend over the whole window
Ro2  2x2 DiD on a treated-unit series detrended with its own pre-period slope
Ro3  2x2 DiD on a treated-unit series detrended with the pre-period gap slope
     (treated minus control mean, which nets out common year effects)
Ro4  the main TWFE on shorter windows, where the pre-1989 trend is flatter
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import did_common as dc

cfg = dc.load_config()
p = dc.load_panel(cfg)
unit_all, time_all, y_all = p["unit"], p["time"], p["y"]
ing_all = p["in_group"]
t0 = float(cfg["treatment_start"])
cluster_all = unit_all

res: dict = {}
print(f"all rows: {len(y_all)}")


def twfe(mask, extra_cols=None, extra_names=None):
    unit, time, y = unit_all[mask], time_all[mask], y_all[mask]
    treat = p["treated"][mask]
    cols = [np.ones((len(y), 1)), treat.reshape(-1, 1)]
    names = ["const", "treated"]
    if extra_cols is not None:
        cols.append(extra_cols)
        names += extra_names
    cols += [dc.dummies(unit), dc.dummies(time)]
    fit = dc.ols(y, np.column_stack(cols), names=names, cluster=unit)
    return fit


# ---------------------------------------------------------------- main spec
base = twfe(np.ones(len(y_all), dtype=bool))
b_main = float(base["params"][1])
print(f"\n[mainspec] treated coef = {b_main:+.4f}  (rows {base['n']})")
res["main"] = {"coef": b_main, "n": base["n"]}

# ---------------------------------------------------------------- Ro1
t = (time_all - t0)
xtrend = (ing_all.astype(float) * t).reshape(-1, 1)
ro1 = twfe(np.ones(len(y_all), dtype=bool), xtrend, ["treated_x_linear_trend"])
b_ro1 = float(ro1["params"][1])
g_ro1 = float(ro1["params"][2])
se_ro1 = float(ro1["se_classic"][1])
print(f"[Ro1] TWFE + treated-unit linear trend: treated coef = {b_ro1:+.4f} "
      f"(classic se {se_ro1:.4f}); trend coef = {g_ro1:+.4f} packs/yr")
print(f"      change from main: {b_ro1 - b_main:+.4f} ({100 * (b_ro1 - b_main) / b_main:+.1f}% of the main estimate)")
res["ro1_trend_in_twfe"] = {"coef": b_ro1, "trend_coef": g_ro1, "se_classic": se_ro1,
                            "change_vs_main": b_ro1 - b_main}

# ---------------------------------------------------------------- Ro2 / Ro3
def two_by_two(ca_series):
    post = time_all >= t0
    ch_t = ca_series[ing_all & post].mean() - ca_series[ing_all & ~post].mean()
    ch_c = y_all[~ing_all & post].mean() - y_all[~ing_all & ~post].mean()
    return ch_t - ch_c, ch_t, ch_c


pre = time_all < t0
ca = ing_all
ylin = unit_all == cfg["treated_units"][0]

# CA-only pre-period slope
b_ca = float(np.polyfit(time_all[pre & ca], y_all[pre & ca], 1)[0])
# pre-period gap slope (CA minus the control mean in each year)
yrs = np.unique(time_all)
ctrl_mean = np.array([y_all[(~ca) & (time_all == tt)].mean() for tt in yrs])
ca_series = np.array([y_all[ca & (time_all == tt)].mean() for tt in yrs])
gap = ca_series - ctrl_mean
b_gap = float(np.polyfit(yrs[yrs < t0], gap[yrs < t0], 1)[0])
b_ctrl = float(np.polyfit(yrs[yrs < t0], ctrl_mean[yrs < t0], 1)[0])
print(f"\npre-{int(t0)} linear slopes (packs per year): treated unit {b_ca:+.4f}; "
      f"control mean {b_ctrl:+.4f}; gap {b_gap:+.4f}")

det2 = np.where(ca, y_all - b_ca * (time_all - t0), y_all)
d2, ch_t2, ch_c2 = two_by_two(det2)
print(f"[Ro2] 2x2 on treated unit detrended by its own pre-period slope ({b_ca:+.4f}/yr): "
      f"treated change {ch_t2:+.3f}, control change {ch_c2:+.3f}, DiD = {d2:+.4f}")
print(f"      change from main: {d2 - b_main:+.4f} ({100 * (d2 - b_main) / b_main:+.1f}%)")
res["ro2_detrend_ca_slope"] = {"slope": b_ca, "did": d2, "change_vs_main": d2 - b_main}

det3 = np.where(ca, y_all - b_gap * (time_all - t0), y_all)
d3, ch_t3, ch_c3 = two_by_two(det3)
print(f"[Ro3] 2x2 on treated unit detrended by the pre-period GAP slope ({b_gap:+.4f}/yr): "
      f"treated change {ch_t3:+.3f}, control change {ch_c3:+.3f}, DiD = {d3:+.4f}")
print(f"      change from main: {d3 - b_main:+.4f} ({100 * (d3 - b_main) / b_main:+.1f}%)")
res["ro3_detrend_gap_slope"] = {"slope": b_gap, "did": d3, "change_vs_main": d3 - b_main}

# ---------------------------------------------------------------- Ro4 windows
print("\n[Ro4] main TWFE on shorter windows (pre-1989 trend is flatter from the early 1980s):")
wins = []
for start in [1970, 1975, 1980, 1981, 1984, 1986]:
    m = time_all >= start
    fit = twfe(m)
    b = float(fit["params"][1])
    gpre = float(np.polyfit(yrs[(yrs >= start) & (yrs < t0)], gap[(yrs >= start) & (yrs < t0)], 1)[0])
    print(f"  window {start}-2000: treated coef = {b:+8.3f} (classic se {float(fit['se_classic'][1]):6.3f}), "
          f"rows {fit['n']}, pre-period gap slope in window {gpre:+.3f}/yr")
    wins.append({"start": start, "coef": b, "se_classic": float(fit["se_classic"][1]),
                 "n": fit["n"], "pre_gap_slope_in_window": gpre})
res["ro4_windows"] = wins

print("\nrows: no rows are dropped except when a window starts after 1970, as labelled above")
dc.save_json(res, "06_robustness.json")
