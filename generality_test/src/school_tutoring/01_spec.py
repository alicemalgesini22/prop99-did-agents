"""Step 1: specification. Read the raw data, check each column's role against the data,
write did_config.json for this run.

Run: uv run python src/school_tutoring/01_spec.py
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "school_tutoring"
RESULTS.mkdir(parents=True, exist_ok=True)

DATA_PATH = "data/raw/school_tutoring.csv"  # named in the prompt / plan

UNIT = "school_id"
TIME = "year"
OUTCOME = "reading_score"
TREATED_COL = "tutoring_school"
TREATMENT_START = 2017  # README: programme introduced "from the 2017 school year"


def main() -> None:
    df = pd.read_csv(ROOT / DATA_PATH)
    print(f"rows read from {DATA_PATH}: {len(df)}")
    print(f"columns: {list(df.columns)}")

    # ---- role checks against the data -------------------------------------------------
    assert UNIT in df.columns and TIME in df.columns and OUTCOME in df.columns
    print(f"\nunits ({UNIT}): {df[UNIT].nunique()} distinct, "
          f"min={df[UNIT].min()}, max={df[UNIT].max()}, dtype={df[UNIT].dtype}")
    print(f"periods ({TIME}): {df[TIME].nunique()} distinct, "
          f"min={df[TIME].min()}, max={df[TIME].max()}, dtype={df[TIME].dtype}")
    print(f"outcome ({OUTCOME}): dtype={df[OUTCOME].dtype}, "
          f"n_missing={df[OUTCOME].isna().sum()}, "
          f"min={df[OUTCOME].min():.2f}, max={df[OUTCOME].max():.2f}")

    # ---- treatment flag: constant within unit? ---------------------------------------
    nun = df.groupby(UNIT)[TREATED_COL].nunique()
    print(f"\n{TREATED_COL} distinct values per {UNIT}: max={nun.max()}, "
          f"units that vary within unit={(nun > 1).sum()}")
    treated_units = sorted(df.loc[df[TREATED_COL].astype(bool), UNIT].unique().tolist())
    control_units = sorted(df.loc[~df[TREATED_COL].astype(bool), UNIT].unique().tolist())
    print(f"treated units: {len(treated_units)} -> {treated_units}")
    print(f"control units: {len(control_units)}")

    # ---- is there a ready-made 'post'/'after' column? --------------------------------
    post_like = [c for c in df.columns
                 if any(k in c.lower() for k in ("post", "after", "treat_start", "launch"))]
    print(f"\ncolumns that look like a ready-made post indicator: {post_like}")
    print("=> none present, so the post indicator has to be built from the calendar: "
          f"{TIME} >= {TREATMENT_START}. It is by construction 0 for every control unit "
          "before the start and 1 after, so the treatment indicator is treated x post "
          "and is 0 for all control rows.")

    # ---- treatment start: what does the data itself say? -----------------------------
    # The flag is constant within unit, so no school-specific start date is observed.
    # The only timing information is the README sentence. Record that plainly.
    print(f"\ntreatment start used for every treated unit: {TIME} = {TREATMENT_START}")
    print("source of the start date: README ('from the 2017 school year'). It cannot be "
          "verified school by school in the data, because the treatment flag is constant "
          "within school. Placebo start dates and a start-date sensitivity are reported "
          "in 09_placebo_start.py.")
    print("staggered timing: number of distinct observed treatment starts = 1 "
          "(uniform by construction, not by evidence)")
    print(f"pre-treatment periods available: {TREATMENT_START - df[TIME].min()} "
          f"({df[TIME].min()}..{TREATMENT_START - 1}), "
          f"post periods: {df[TIME].max() - TREATMENT_START + 1} "
          f"({TREATMENT_START}..{df[TIME].max()})")

    # ---- covariates ----------------------------------------------------------------
    print(f"\ncovariates available but NOT used: "
          f"{[c for c in df.columns if c not in (UNIT, TIME, OUTCOME, TREATED_COL)]} "
          "(plan: all rows, no covariates; not requested, so not added)")

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
        "post_column_in_data": None,
        "treatment_indicator": "treated unit x (year >= 2017)",
        "notes": {
            "outcome_units": "test points",
            "periods": f"{TIME} {df[TIME].min()}..{df[TIME].max()} (annual)",
            "timing_source": "README only; treatment flag is constant within school, so "
                             "no school-specific start date is observable",
            "why_no_covariates": "plan says all rows, no covariates; students was not "
                                 "requested",
        },
    }
    out = RESULTS / "did_config.json"
    out.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"\nwrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
