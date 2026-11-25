"""Step 1: specification. Read the raw data, check each column's role against the data,
write did_config.json for this run.

Run: uv run python src/firm_training/01_spec.py
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "firm_training"
RESULTS.mkdir(parents=True, exist_ok=True)

DATA_PATH = "data/raw/firm_training.csv"  # named in the prompt / plan; only place it is written down

UNIT = "firm_id"
TIME = "month"
OUTCOME = "revenue"
TREATED_COL = "joined_training"
POST_COL = "after_launch"
TREATMENT_START = 25  # README: programme launched in month 25


def main() -> None:
    df = pd.read_csv(ROOT / DATA_PATH)
    print(f"rows read from {DATA_PATH}: {len(df)}")

    # ---- role checks against the data -------------------------------------------------
    assert UNIT in df.columns and TIME in df.columns and OUTCOME in df.columns
    print(f"\nunits ({UNIT}): {df[UNIT].nunique()} distinct, "
          f"min={df[UNIT].min()}, max={df[UNIT].max()}, integer-like={df[UNIT].dtype}")
    print(f"periods ({TIME}): {df[TIME].nunique()} distinct, "
          f"min={df[TIME].min()}, max={df[TIME].max()}")
    print(f"outcome ({OUTCOME}): dtype={df[OUTCOME].dtype}, "
          f"n_missing={df[OUTCOME].isna().sum()}, "
          f"min={df[OUTCOME].min():.3f}, max={df[OUTCOME].max():.3f}")

    # treatment flag must be constant within unit, else it is a time-varying treatment
    nun = df.groupby(UNIT)[TREATED_COL].nunique()
    print(f"\n{TREATED_COL} distinct values per unit: max={nun.max()} "
          f"(0 units vary within unit: {(nun > 1).sum()})")
    treated_units = sorted(df.loc[df[TREATED_COL].astype(bool), UNIT].unique().tolist())
    control_units = sorted(df.loc[~df[TREATED_COL].astype(bool), UNIT].unique().tolist())
    print(f"treated units: {len(treated_units)} -> {treated_units}")
    print(f"control units: {len(control_units)}")

    # ---- the ready-made 'post' column: is it zero for control units? -------------------
    # This is the trap in the README: after_launch is True for months >= 25 for EVERY firm.
    post_by_group = df.groupby(TREATED_COL)[POST_COL].mean()
    print(f"\nmean of {POST_COL} by {TREATED_COL}:")
    print(post_by_group.to_string())
    post_is_universal = bool(df.loc[df[TIME] >= TREATMENT_START, POST_COL].all() and
                             not df.loc[df[TIME] < TREATMENT_START, POST_COL].any())
    print(f"{POST_COL} == 1 exactly when {TIME} >= {TREATMENT_START} for all firms: "
          f"{post_is_universal}")
    print("=> after_launch is a pure time dummy, identical for treated and control firms. "
          "It CANNOT be used as the treatment indicator; the treatment indicator must be "
          "treated x post.")

    # does the post column disagree with the calendar anywhere?
    disagree = df[(df[POST_COL].astype(bool)) != (df[TIME] >= TREATMENT_START)]
    print(f"rows where {POST_COL} != ({TIME} >= {TREATMENT_START}): {len(disagree)}")

    # ---- treatment start per treated unit ---------------------------------------------
    # The flag is constant within unit, so timing is not observed firm by firm.
    # The only timing information is the launch month in the README, checked against the
    # post column above: month 25.
    print(f"\ntreatment start used for all treated units: {TIME} = {TREATMENT_START}")
    print("staggered timing check: number of distinct treatment starts = 1 "
          "(the data carry no firm-specific start date; flag is constant within firm)")

    config = {
        "data_path": DATA_PATH,
        "unit": UNIT,
        "time": TIME,
        "outcome": OUTCOME,
        "treated_rule": {"column": TREATED_COL, "equals": True},
        "treated_units": treated_units,
        "control_units": control_units,
        "treatment_start": TREATMENT_START,
        "controls": [],
        "cluster": UNIT,
        "post_column_in_data": POST_COL,
        "post_column_usable_as_treatment": False,
        "notes": {
            "outcome_units": "thousand euro per month",
            "periods": f"{TIME} 1..{df[TIME].max()} (monthly)",
            "treatment_indicator": "treated_unit x (month >= treatment_start)",
            "why_no_covariates": "plan says all rows, no covariates; employees has "
                                 "missing values and was not requested",
        },
    }
    out = RESULTS / "did_config.json"
    out.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"\nwrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
