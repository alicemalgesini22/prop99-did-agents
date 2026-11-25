"""09 - Auxiliary numbers quoted in the write-up, so every number has a file."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import didlib as L

cfg = L.load_config()
OUT = Path("results") / L.RUN_DIR
unit, time, outcome = cfg["unit"], cfg["time"], cfg["outcome"]
start = cfg["treatment_start"]

main = json.load(open(OUT / "main_did.json", encoding="utf-8"))["twfe_cluster_unit"]
es = pd.read_csv(OUT / "event_study.csv")

# minimum detectable effect, 80% power, 5% two-sided, using the clustered SE and t(G-1)
G = 60
tcrit = stats.t.ppf(0.975, G - 1)
tpow = stats.t.ppf(0.80, G - 1)
mde = (tcrit + tpow) * main["se"]

post = es[es["rel_time"] >= 0]
out = {
    "mde_80pct_power": float(mde),
    "t_crit_975": float(tcrit),
    "se_used": main["se"],
    "post_coefs": post[["rel_time", "coef", "se"]].to_dict(orient="records"),
    "mean_post_coef": float(post["coef"].mean()),
    "mean_post_coef_excl_2017": float(post.loc[post["rel_time"] >= 1, "coef"].mean()),
    "note": ("MDE is the smallest true effect that would be detected with 80% power at 5% "
             "(two-sided) given this clustered SE; it ignores sampling error in the SE itself."),
}
with open(OUT / "aux_numbers.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
print(json.dumps(out, indent=2))
