# region_subsidy — difference-in-differences

**Question (plan):** did the subsidy change private investment in the regions that received it?
Data: `data/raw/region_subsidy.csv`, described in `data/README_region_subsidy.md`.
Plan: `plans/plan_region_subsidy.md`. All code: `src/region_subsidy/`. All outputs: `results/region_subsidy/`.

**Short answer:** the plain two-way fixed effects estimate is +7.29 million euro and is very
precisely estimated, but the event study shows treated regions were already on a clearly
steeper upward path before the subsidy (+0.65 per quarter over the 12 pre-quarters), and once
each treated region is allowed its own linear trend the estimate falls to −0.17 (SE 0.60,
p 0.77). I therefore make **no causal claim**: the data cannot separate a subsidy effect from
the pre-existing differential trend.

---

## 1. Specification (`src/region_subsidy/01_spec.py` → `results/region_subsidy/did_config.json`)

| role | column | why |
|---|---|---|
| unit | `region_id` | 1–30, constant across quarters, README calls it the region identifier |
| time | `quarter` | 1–24, no gaps |
| outcome | `investment` | million euro, numeric, zero missing |
| treatment group | `subsidy_region == True` | the only treatment-related column; boolean, constant within region; 10 regions true, 20 false |
| treatment start | quarter 13 | README: "received an investment subsidy from quarter 13" |
| controls | none | plan asks for no covariates |
| cluster | `region_id` (30 clusters) | default |

The data contain **no** treatment-date or "post" column (`spec_checks.json`,
`columns_resembling_post = []`), so no ready-made post column was used or trusted. The start
quarter comes from the README text only; the data cannot confirm it. Treated units are stored
explicitly in the config: 1, 6, 11, 15, 17, 20, 21, 23, 28, 30.

## 2. Panel checks (`02_panel_checks.py` → `panel_checks.json`, `panel_used.csv`)

- 720 rows read; 0 duplicate (region, quarter) keys → 720 rows kept (no rows dropped anywhere in the run).
- 30 regions × 24 quarters, perfectly balanced (24 rows per region), quarters 1–24 with no gaps.
- Missing `investment`: **0 rows** (no missing periods). Missing unit/time: 0. `subsidy_region` never missing and constant within region.
- Outcome range 40.92–96.45, mean 59.49, sd 10.14.

## 3. Design checks (`03_design_checks.py` → `design_checks.json`)

- **10 treated regions, 20 control regions**, 240 treated rows and 120 treated-post rows.
- **Timing is uniform**, not staggered: every treated region starts in quarter 13 (there is only
  one start date in the data/README). Plain TWFE is therefore not exposed to the
  staggered-adoption/negative-weighting problem that would call for Callaway–Sant'Anna or an
  imputation estimator. I kept plain TWFE, as the plan asks.
- 30 clusters, 10 of them treated: cluster-robust inference is possible but the treated cluster
  count is modest, so it is paired with randomisation inference (section 7).

## 4. Raw trends (`04_raw_trends.py` → `raw_trends.csv`, `raw_trends.png`)

Mean investment by quarter is plotted for treated and control regions with a vertical line at
quarter 13. Mean levels differ (treated start higher and rise faster): the treated−control gap
goes from **+1.02 at q1 to +8.23 at q12**, i.e. it grew by 7.21 million euro *before* the
subsidy. Levels are not the identifying assumption, but the gap movement is the first warning.

## 5. Main estimate (`05_main_did.py` → `main_did.json`, `main_estimates.csv`)

`investment ~ treated×post + region FE + quarter FE`, all 720 rows, no covariates, SE clustered by region:

- **TWFE coefficient = +7.2891** (cluster SE 0.2103, t 34.66, p ≈ 3.1e-263, 95% CI 6.8769 to 7.7013), R² 0.972.
- **Simple 2×2 cross-check = +7.2891**: treated 60.495 → 70.138 (+9.643); control 55.405 → 57.758 (+2.354); difference 7.289. It matches the TWFE number exactly, as expected for a balanced panel with a single start date.

## 6. Event study (`06_event_study.py` → `event_study.csv`, `event_study.json`, `event_study.png`)

One treated×relative-quarter dummy per quarter, reference = q12 (rel_time −1), region and quarter FE,
cluster SE by region. 23 coefficients, rel_time −12…+11.

- **Pre-treatment coefficients are clearly rising, not flat**: −7.21 at −12, −6.14 at −11, −5.88 at −10, −4.61 at −9, −3.95 at −8, −3.09 at −7, −2.49 at −6, −1.05 at −5, −0.51 at −4, −1.98 at −3, −0.72 at −2, 0 at −1 (reference). Most pre-period coefficients are individually significant; joint test of the 11 pre-period coefficients = 0: **χ² = 263.2, df 11, p = 4.9e-50**. Unweighted slope of the pre-period coefficients over rel_time: **+0.648 per quarter**.
- **Post-treatment coefficients rise smoothly from 0.80 at rel_time 0 (p 0.37) to 7.13 at +11** (mean 4.15). There is **no visible jump at the start date**; the path looks like a continuation of the pre-treatment trend.

This is exactly the failure the plan names ("clear differences in trends before treatment").

## 7. Inference (`07_inference.py` → `inference.json`, `randomisation_null.csv`)

- Cluster-robust SE by region (30 clusters, 10 treated): SE 0.2103, p ≈ 0, CI 6.88–7.70.
- Placebo-in-space randomisation test: reassign the 10-region treated set at random among the 30
  regions (5,000 draws, seed 20261124), re-estimate the same TWFE coefficient each time.
  - Placebo null: mean 0.009, sd 1.351, 2.5–97.5 percentiles −2.641 to 2.767.
  - Observed 7.289 is the most extreme of 5,001 estimates: **rank 1 of 5,001, placebo p = 1/5,001 = 0.0002** (the smallest value 5,000 draws can give).
  - So inference rejects zero at the 5% level, but that test has no power to separate the subsidy
    from the pre-existing trend: the smooth pre-trend alone would already put the observed region
    set far outside the null.

## 8. Robustness (`08_robustness.py` → `robustness.csv`, `robustness.json`)

The main threat found in the data is the differential pre-trend. I add linear trends for the treated regions:

| specification | coef | cluster SE | p | change vs main |
|---|---|---|---|---|
| main, no trends | 7.2891 | 0.2103 | ≈0 | — |
| + one linear trend for the treated group | **−0.1729** | 0.5956 | 0.772 | −7.4619 (−102.4%) |
| + one linear trend per treated region (10 terms) | **−0.1729** | 0.5997 | 0.773 | −7.4619 (−102.4%) |

The estimate collapses to about zero and loses all precision. Context: the average per-region
pre-period (q1–q12) slope of investment on quarter is 0.832 for treated regions (sd 0.187, range
0.41–1.04) and 0.184 for control regions (sd 0.098, range −0.01–0.35).

## 9. Checks against the plan's "what would prove me wrong"

- Estimate close to zero or sign changing across tests: **sign changes** — +7.29 unadjusted, −0.17 with treated trends.
- Clear differences in trends before treatment: **yes** (event study, joint p = 4.9e-50).
- Inference does not reject zero at 5%: **no**, both cluster SE and the randomisation test reject (p ≈ 0 and 0.0002).

Two of the three fail, so the design does **not** support a causal claim about the subsidy.

## Limits

- Treatment timing (quarter 13 for all treated regions) comes from the README only; the data have no date column, so I cannot verify it from the data. I am not sure it is exact.
- 10 treated regions / 30 clusters: clustered SEs are usable but rely on asymptotics with few treated clusters; the randomisation p-value is the more credible of the two.
- The trend-adjusted estimate can be wrong in either direction: with only 12 pre-periods per region, treated-specific trends may absorb a genuine, slowly building subsidy effect. I am not sure whether −0.17 means "no effect" or "effect fully absorbed by the trend"; the data cannot distinguish an immediate level effect from a pre-existing trend.
- No covariates (per plan), so nothing controls for region-specific shocks correlated with subsidy receipt.
- Outcome is a level in million euro; no log/scale alternatives were run (not in the plan).
- Anything about the policy, its size or its selection rule is outside what I computed; I make no claim about it.

## Files produced

| file | made by |
|---|---|
| `did_config.json`, `spec_checks.json` | `01_spec.py` |
| `panel_checks.json`, `panel_used.csv` | `02_panel_checks.py` |
| `design_checks.json` | `03_design_checks.py` |
| `raw_trends.csv`, `raw_trends.png` | `04_raw_trends.py` |
| `main_did.json`, `main_estimates.csv` | `05_main_did.py` |
| `event_study.csv`, `event_study.json`, `event_study.png` | `06_event_study.py` |
| `inference.json`, `randomisation_null.csv` | `07_inference.py` |
| `robustness.csv`, `robustness.json` | `08_robustness.py` |

## Choices I made without asking

1. Roles of the columns (region/time/outcome/group) taken from the README table and each verified against the data before estimating.
2. Treatment start = quarter 13, taken from the README sentence because no date column exists; recorded in the config with its source.
3. Treated units = those with `subsidy_region == True` (10 regions), written explicitly into `did_config.json` rather than re-derived at estimation time.
4. No covariates and no sample restrictions, as the plan specifies.
5. Clustering by region (default in the procedure), 30 clusters.
6. Uniform timing means no staggered-adoption estimator was needed; I kept plain TWFE and said so rather than switching method.
7. Event study: reference period rel_time = −1 (quarter 12), every period kept separate (no endpoint binning), region and quarter FE, SE clustered by region.
8. Described the pre-trend shape with an unweighted slope of the pre-period coefficients plus a joint Wald test of the pre-period coefficients; the "flat" cut-off I used for wording was |slope| < 0.15 per quarter per quarter — this cut-off is my own arbitrary choice.
9. Inference: because only 10 of 30 clusters are treated, I ran a randomisation test that permutes which 10 regions are treated (5,000 draws, seed 20261124) and reported rank/(draws+1). This replaces the procedure's "one control unit at a time" placebo, which is written for the case of one or a few treated units; with 10 treated units the natural analogue is to permute the treated set.
10. Robustness check: treated-specific linear trends, chosen because the pre-trend is the main threat visible in the data; I report both a single group trend and one trend per treated region. Percent change is computed relative to the absolute value of the main coefficient.
11. Reported descriptive per-region pre-period slopes in `robustness.json` only to explain the trend-adjusted result; no test depends on them.
12. Random seed 20261124 (today's date) for the randomisation draws; nothing else in the run is random.
