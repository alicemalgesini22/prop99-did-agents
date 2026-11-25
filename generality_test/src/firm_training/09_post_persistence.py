"""Step 9 (descriptives for the write-up): does the estimated gap persist after launch?

Reads the event-study output and the group means; writes results/firm_training/post_persistence.json.
Run: uv run python src/firm_training/09_post_persistence.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import didlib  # noqa: E402

cfg = didlib.load_config()
start = cfg["treatment_start"]
means = pd.read_csv(didlib.RESULTS / "raw_trends.csv")
es = pd.read_csv(didlib.RESULTS / "event_study.csv")

post = means[means["_time"] >= start]
first = post[post["_time"] <= start + 11]["gap"].mean()
second = post[post["_time"] >= start + 12]["gap"].mean()
slope_post = np.polyfit(post["_time"], post["gap"], 1)[0]

es_first = es[(es["rel_month"] >= 0) & (es["rel_month"] <= 11)]["coef"].mean()
es_second = es[es["rel_month"] >= 12]["coef"].mean()

print(f"mean treated-control gap, post months {start}-{start + 11}: {first:.3f}")
print(f"mean treated-control gap, post months {start + 12}-{int(post['_time'].max())}: "
      f"{second:.3f} (change {second - first:+.3f})")
print(f"linear slope of the gap in the post period: {slope_post:+.4f} per month")
print(f"event-study mean coefficient, rel 0-11: {es_first:+.3f}; rel >= 12: {es_second:+.3f}")

out = {"post_gap_first_12_months": float(first),
       "post_gap_last_12_months": float(second),
       "post_gap_change": float(second - first),
       "post_gap_slope_per_month": float(slope_post),
       "event_study_mean_rel0_11": float(es_first),
       "event_study_mean_rel_ge12": float(es_second)}
(didlib.RESULTS / "post_persistence.json").write_text(json.dumps(out, indent=2),
                                                      encoding="utf-8")
print(f"wrote {(didlib.RESULTS / 'post_persistence.json').relative_to(didlib.ROOT)}")
