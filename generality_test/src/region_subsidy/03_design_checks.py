"""03 - Design checks: how many treated units, and is treatment timing staggered?"""
from __future__ import annotations

from didlib import add_treatment_columns, load_config, read_panel, save_json

cfg = load_config()
df = read_panel(cfg)
df = add_treatment_columns(df, cfg)

checks: dict = {}
checks["n_units"] = int(df[cfg["unit"]].nunique())
checks["n_treated_units"] = int(df.loc[df["treated"] == 1, cfg["unit"]].nunique())
checks["n_control_units"] = int(df.loc[df["treated"] == 0, cfg["unit"]].nunique())
checks["treated_share_of_units"] = checks["n_treated_units"] / checks["n_units"]
checks["n_treated_obs"] = int((df["treated"] == 1).sum())
checks["n_treated_post_obs"] = int(df["treat_post"].sum())

# Staggering: a timing column would vary across treated units. The data have
# none, and the config assigns one start quarter, so timing is uniform by
# construction -- but confirm the treated set never switches on/off in the flag.
checks["group_flag_changes_over_time"] = bool(
    (df.groupby(cfg["unit"])[cfg["group_flag_column"]].nunique() > 1).any()
)
checks["distinct_start_quarters"] = 1 if cfg["treatment_start"] else 0
checks["timing"] = "uniform (one start quarter for all treated units)"
checks["staggered"] = False
checks["few_treated_units_flag"] = checks["n_treated_units"] < 5
checks["clusters_for_inference"] = int(df[cfg["unit"]].nunique())

print(f"units: {checks['n_units']}, treated: {checks['n_treated_units']}, "
      f"control: {checks['n_control_units']}")
print(f"timing: {checks['timing']}; staggered: {checks['staggered']}")
print(f"treated post observations: {checks['n_treated_post_obs']}")
print(f"cluster count for inference: {checks['clusters_for_inference']}")
if checks["n_treated_units"] < 5:
    print("WARNING: fewer than ~5 treated units -> clustered SEs unreliable, use placebo tests")
else:
    print(">=5 treated units: cluster-robust SE by unit is feasible; "
          "placebo/randomisation inference is still reported because the treated cluster count is small")

save_json(checks, "design_checks.json")
