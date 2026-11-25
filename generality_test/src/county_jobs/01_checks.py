"""01: panel checks + did_config.json for county_jobs.

Reads data/raw/county_jobs.csv, prints row counts after every filter,
checks duplicates/balance/missingness, writes results/county_jobs/did_config.json.
"""
import json
import os

import pandas as pd

DATA = "data/raw/county_jobs.csv"
OUT = "results/county_jobs"
os.makedirs(OUT, exist_ok=True)

df = pd.read_csv(DATA)
print(f"[rows] read from {DATA}: {len(df)}")
print(f"[cols] {list(df.columns)}")
print(df.head(3).to_string())

# ---- roles / types -------------------------------------------------------
print("\n[dtypes]\n", df.dtypes.to_string())
for c in ["county", "year"]:
    assert df[c].notna().all(), c
print("[check] county min/max:", df["county"].min(), df["county"].max())
print("[check] year min/max:", df["year"].min(), df["year"].max())
print("[check] employment_rate missing:", int(df["employment_rate"].isna().sum()))
print("[check] program_start missing rows:", int(df["program_start"].isna().sum()))

# ---- duplicates ----------------------------------------------------------
dups = df.duplicated(subset=["county", "year"], keep=False)
print(f"\n[dups] duplicated (county,year) rows: {int(dups.sum())}")
if dups.any():
    print(df.loc[dups].sort_values(["county", "year"]).to_string())
    df = df.drop_duplicates(subset=["county", "year"], keep="first")
    print(f"[rows] after dropping duplicated (county,year): {len(df)}")

# ---- balance -------------------------------------------------------------
units = df["county"].nunique()
periods = df["year"].nunique()
print(f"\n[panel] units={units}, periods={periods}, rows={len(df)}, balanced would be {units*periods}")
counts = df.groupby("county")["year"].agg(["count", "min", "max"])
bad = counts[(counts["count"] != periods) | (counts["min"] != df["year"].min()) | (counts["max"] != df["year"].max())]
print(f"[panel] counties not spanning the full period range: {len(bad)}")
if len(bad):
    print(bad.to_string())
print("[panel] rows per county distribution:\n", counts["count"].value_counts().to_string())

# ---- missing values, exact periods --------------------------------------
miss = df[df["employment_rate"].isna()]
print(f"\n[missing] employment_rate missing rows: {len(miss)}")
if len(miss):
    print("[missing] exact (county, year):", list(zip(miss["county"], miss["year"])))
    df = df.dropna(subset=["employment_rate"])
    print(f"[rows] after dropping missing employment_rate: {len(df)}")

# ---- treatment variable --------------------------------------------------
# program_start must be constant within county
nun = df.groupby("county")["program_start"].nunique(dropna=False)
print(f"\n[treat] counties with >1 distinct program_start: {int((nun > 1).sum())}")

ps = df.groupby("county")["program_start"].first()
treated = ps.dropna()
print("[treat] counties ever treated:", treated.shape[0], "of", units)
print("[treat] never treated:", int(ps.isna().sum()))
print("[treat] cohort sizes:\n", treated.astype(int).value_counts().sort_index().to_string())
print("[treat] treatment start years:", sorted(treated.astype(int).unique().tolist()))
print("[treat] treatment timing staggered:", treated.nunique() > 1)

# is program_start ever before the panel starts / after it ends?
print("[treat] program_start outside panel years:",
      int(((treated < df['year'].min()) | (treated > df['year'].max())).sum()))

# a "post" indicator, defined from the rule in the README (not a column in the data)
df["treated"] = df["program_start"].notna().astype(int)
df["post"] = ((df["program_start"].notna()) & (df["year"] >= df["program_start"])).astype(int)
print("\n[check] rows with post=1 among never-treated (must be 0):",
      int(df.loc[df["program_start"].isna(), "post"].sum()))
print("[check] rows with treated=1 and post=1:", int((df["treated"] * df["post"]).sum()))
print("[check] treated rows by cohort and pre/post:")
print(df[df["treated"] == 1].groupby(["program_start", "post"]).size().to_string())

# never-treated must have zero post rows -> confirmed above; no ready-made post column exists.
df.to_csv(f"{OUT}/panel_analysis.csv", index=False)
print(f"\n[rows] written to {OUT}/panel_analysis.csv: {len(df)}")

config = {
    "data_path": "data/raw/county_jobs.csv",
    "unit": "county",
    "time": "year",
    "outcome": "employment_rate",
    "treated_units": {
        "rule": "counties with non-empty program_start",
        "column": "program_start",
        "list": sorted(int(c) for c in treated.index),
    },
    "treatment_start": {
        "column": "program_start",
        "note": "staggered: cohorts 2008, 2011, 2014; post = program_start not empty and year >= program_start",
    },
    "controls": [],
    "cluster": "county",
    "never_treated": sorted(int(c) for c in ps[ps.isna()].index),
}
with open(f"{OUT}/did_config.json", "w") as f:
    json.dump(config, f, indent=2)
print(f"[config] written to {OUT}/did_config.json")
