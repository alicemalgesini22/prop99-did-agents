"""Step 6: event study. One coefficient per period relative to treatment, with the last
pre-treatment period as the reference.

Run: uv run python src/school_tutoring/06_event_study.py
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.formula.api as smf  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from didlib import RESULTS, load_config, load_panel, save_json  # noqa: E402

cfg = load_config()
df = load_panel(cfg)
print(f"rows used: {len(df)}")

rels = sorted(df["_rel"].unique())
REF = -1  # last pre-treatment period
print(f"event times present: {rels} (reference: {REF})")
# with a single start date every unit contributes every event time; no binning needed
per = df.groupby("_rel")["_unit"].nunique()
print("units contributing at each event time:")
print(per.to_string())
assert per.min() == df["_unit"].nunique(), "event times are not common to all units"

terms = [r for r in rels if r != REF]


def tname(r: int) -> str:
    """Formula-safe name for an event-time dummy ('_rel-5' is not valid in patsy)."""
    return f"_ev_m{-r}" if r < 0 else f"_ev_p{r}"


for r in terms:
    df[tname(r)] = ((df["_rel"] == r) & (df["_treated"] == 1)).astype(int)
rhs = " + ".join(tname(r) for r in terms)
f = f"_y ~ {rhs} + C(_unit) + C(_time)"
m = smf.ols(f, data=df).fit(cov_type="cluster", cov_kwds={"groups": df["_unit"]})
print(f"\nrows used in the event study: {int(m.nobs)}; reference period {REF} "
      f"(coefficient fixed at 0 by construction)")

rows = []
for r in rels:
    name = tname(r)
    if r == REF:
        rows.append({"rel_time": r, "year": int(cfg["treatment_start"] + r),
                     "coef": 0.0, "se": 0.0, "ci_lo": 0.0, "ci_hi": 0.0,
                     "is_reference": True})
    else:
        ci = m.conf_int().loc[name].tolist()
        rows.append({"rel_time": r, "year": int(cfg["treatment_start"] + r),
                     "coef": float(m.params[name]), "se": float(m.bse[name]),
                     "ci_lo": float(ci[0]), "ci_hi": float(ci[1]),
                     "is_reference": False})
ev = pd.DataFrame(rows).sort_values("rel_time")
print()
print(ev.round(3).to_string(index=False))
ev.to_csv(RESULTS / "event_study.csv", index=False)
print(f"\nwrote results/{RESULTS.name}/event_study.csv")

# ---- joint test that all pre-treatment coefficients are zero ------------------------
pre_names = [tname(r) for r in terms if r < REF]
post_names = [tname(r) for r in terms if r > REF]
w_pre = m.f_test(" = 0, ".join(pre_names) + " = 0")
w_post = m.f_test(" = 0, ".join(post_names) + " = 0")
print(f"\njoint test, pre-treatment coefficients ({pre_names}): F={float(w_pre.fvalue):.3f}, "
      f"p={float(w_pre.pvalue):.3f}")
print(f"joint test, post-treatment coefficients ({post_names}): F={float(w_post.fvalue):.3f}, "
      f"p={float(w_post.pvalue):.3f}")

pre = ev[~ev["is_reference"] & (ev["rel_time"] < REF)]
print(f"\npre-treatment coefficients: {pre['coef'].round(2).tolist()} "
      f"(mean {pre['coef'].mean():+.3f}, all within "
      f"+/-{pre['coef'].abs().max():.3f} points)")

# ---- plot ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 4.4))
ax.axhline(0, color="black", lw=0.8)
ax.axvline(-0.5, ls="--", color="grey", lw=1)
ax.errorbar(ev["rel_time"], ev["coef"],
            yerr=[ev["coef"] - ev["ci_lo"], ev["ci_hi"] - ev["coef"]],
            fmt="o-", color="#c0392b", ecolor="#c0392b", capsize=3, ms=5)
ax.scatter([REF], [0], color="#2c3e50", zorder=5, marker="D", s=40,
           label=f"reference ({int(cfg['treatment_start']) - 1})")
ax.set_xlabel("years relative to treatment start")
ax.set_ylabel(f"effect on {cfg['outcome']} (test points)")
ax.set_title("Event study: treated x period, unit and year FE, 95% CI clustered by school")
ax.set_xticks(rels)
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(RESULTS / "event_study.png", dpi=150)
print(f"wrote results/{RESULTS.name}/event_study.png")

save_json({
    "reference_rel_time": REF,
    "reference_year": int(cfg["treatment_start"] + REF),
    "n_obs": int(m.nobs),
    "n_units": int(df["_unit"].nunique()),
    "cluster": cfg["cluster"],
    "joint_test_pre": {"F": float(w_pre.fvalue), "p": float(w_pre.pvalue)},
    "joint_test_post": {"F": float(w_post.fvalue), "p": float(w_post.pvalue)},
    "coefs": ev.to_dict(orient="records"),
    "script": "src/school_tutoring/06_event_study.py",
}, "event_study.json")
