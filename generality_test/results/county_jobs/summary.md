# county_jobs: did the job-placement programme change counties' employment rate?

Run folder: `results/county_jobs/` (code in `src/county_jobs/`). Data: `data/raw/county_jobs.csv`,
description `data/README_county_jobs.md`, plan `plans/plan_county_jobs.md`.

## Specification (`results/county_jobs/did_config.json`, written by `01_checks.py`)

| Role | Column | Where it comes from |
|---|---|---|
| unit | `county` | README: county id 1–45; 45 distinct values in the data |
| time | `year` | README: yearly, 2004–2019; 16 distinct values |
| outcome | `employment_rate` | README: percent, never empty; 0 missing in the data |
| treatment group | `program_start` non-empty | README rule: a county is in the programme in a year if `program_start` is not empty and `year >= program_start` |
| treatment start | `program_start` (staggered: 2008, 2011, 2014) | 10 counties per cohort |
| controls | none | plan says "no covariates" |
| cluster | `county` | 45 clusters |

There is no ready-made `post`/`after` column in the data. I built `post` from the README rule and
checked it: rows with `post = 1` among never-treated counties = 0; 270 treated rows are post.

## Panel checks (`01_checks.py`, `results/county_jobs/panel_analysis.csv`)

- 720 rows read; 0 duplicate (`county`, `year`) rows; no rows dropped.
- 45 counties × 16 years = 720; every county has all 16 years, so the panel is balanced; 0 rows dropped.
- `employment_rate` missing in 0 rows, so no period had to be dropped.
- `program_start` is constant within every county (0 counties with >1 value); 30 counties treated,
  15 never treated; cohorts 2008/2011/2014 with 10 counties each; no start year outside 2004–2019.

## Design checks

- Treated units: 30. Never-treated: 15. Treatment timing is **staggered** (three start years).
- With staggered timing, plain two-way fixed effects averages "already-treated vs not-yet-treated"
  comparisons and can be biased when effects vary across cohorts or over time. I therefore made the
  main estimator the Callaway–Sant'Anna group-time ATT with never-treated counties as the comparison
  group, and report TWFE only as a cross-check.
- 30 treated units / 45 clusters: clustered standard errors are usable, so inference is clustered by
  county (the aggregate uses a county-level cluster bootstrap).

## Raw trends (`02_raw_trends.py`, `raw_trends.png`, `raw_trends_means.csv`)

Never-treated employment rises steadily (70.0 → 73.9). All three cohorts rise too. Cohort 2014 shows a
visible jump in 2014 (73.9 → 77.0). Cohort 2008 rises faster than never-treated before its start
(67.7 → 69.2 over 2004–2007), which is the main threat I saw in the raw data; the cohort-by-year 2x2
event-study estimates below show that this pre-trend is small once the never-treated comparison is used.

## Main estimate (`03_main_estimate.py` → `main_estimates.csv`, `att_gt.csv`)

| Estimator | Estimate (pp) | SE | Source |
|---|---|---|---|
| CS ATT, cohort-size weighted over post cells (**main**) | **+2.839** | 0.257 (bootstrap) | `main_estimates.csv`, `inference_main.csv` |
| CS ATT, unweighted mean of the 27 post cells | +2.986 | — | `main_estimates.csv` |
| TWFE `treated × post` + county FE + year FE, cluster county | +1.952 | 0.246 (cluster) | `main_estimates.csv` |
| Simple 2x2 difference of means, cohort 2008 | +4.365 | — | `two_by_two.csv` |
| Simple 2x2 difference of means, cohort 2011 | +1.225 | — | `two_by_two.csv` |
| Simple 2x2 difference of means, cohort 2014 | +3.067 | — | `two_by_two.csv` |
| Mean of the three 2x2s | +2.886 | — | `two_by_two.csv` |

Cohort-specific CS ATTs (mean over post years): 2008 +4.127, 2011 +1.586, 2014 +2.804.
The 2x2 for each cohort uses all years before its start as "pre" and all years from its start as "post",
compared with never-treated counties over the same calendar windows. TWFE (+1.95) is smaller than the
CS estimate (+2.84) — consistent with the known bias of TWFE under staggered timing with
cohort-varying effects; the 2x2 average (+2.89) agrees closely with CS.

## Event study (`04_event_study.py` → `event_study.csv`, `event_study.png`)

One CS ATT per event time, reference `e = -1`, never-treated controls, 95% cluster-bootstrap CIs
(999 draws, seed 20261125).

- Pre-treatment coefficients are **flat and near zero**: e = −4..−2 are −0.063, −0.184, −0.058
  (SE 0.21–0.23); joint Wald test W = 0.66, df 3, p = 0.884. No evidence of differential pre-trends.
  (18 individual pre cells; 2 have |t| > 2, both cohort 2011: +0.789 in 2006 and +0.666 in 2007.
  That cohort's own pre-trend is mildly positive, which if anything inflates its post estimate.)
- Post-treatment coefficients rise from +1.046 at e = 0 to +2.976 at e = 5, then to +6.2/+7.3 at
  e = 9–11, where only cohort 2008 contributes. The effect is not a one-off level jump: it keeps
  growing with years since treatment.
- e = −10 and −9 are identified only from cohort 2014; e = 6..8 from cohorts 2008 and 2011; the
  `cohorts` column of `event_study.csv` records the composition at each e.

## Inference (`05_inference.py` → `inference_main.csv`)

45 clusters, 30 treated. Main CS ATT +2.839, bootstrap SE 0.257, 95% percentile CI [+2.334, +3.321],
t = 11.1. TWFE cluster SE 0.246, CI [+1.470, +2.435]. The zero effect is rejected at 5%.
Since there are 30 treated units, I used clustered inference rather than placebo tests.

## Robustness (`06_robustness.py` → `robustness_detrended.csv`, `robustness_detrended_cells.csv`)

The main threat in this dataset is that the estimated effect keeps growing, which a continuing
differential trend could produce. I removed each cohort's linear pre-treatment differential trend
(cohort mean minus never-treated mean, fitted on years before the start and extrapolated) from every
ATT(g,t):

- Detrended overall ATT = **+2.656** (bootstrap SE 0.415, CI [+1.847, +3.477]);
  change from the main estimate −0.183 (−6%).
- Cohort means after detrending: 2008 +3.533 (was +4.127), 2011 +1.511 (was +1.586),
  2014 +2.924 (was +2.804).

The estimate barely moves, so a linear differential trend does not explain the result.

## Against the plan's "what would prove me wrong"

- Estimate far from zero or sign changes: the estimate is +2.7 to +2.9 pp and positive in every
  estimator (CS, 2x2 per cohort, TWFE, detrended). Sign does not change.
- Event study shows clear pre-trend differences: it does not; pre-coefficients are flat (p = 0.884).
- Inference fails to reject zero at 5%: it rejects (CI [+2.33, +3.32] for the main estimate).

## Limits

- Only three adoption cohorts of 10 counties each, and 15 never-treated counties. The cohort-specific
  effects differ a lot (+1.6 for 2011 vs +4.1 for 2008), so the aggregate +2.84 is an average over
  quite different counties; I would not read it as a single policy effect.
- The effect keeps growing for up to 11 years after adoption (cohort 2008 reaches ~+7 pp at e = 11).
  I am not sure this is a programme effect rather than a slow divergence that started before adoption
  and is not linear; linear detrending cannot rule that out.
- Adoption timing may be endogenous (counties may adopt when their labour market is changing), and the
  design has no covariate adjustment, as the plan requires.
- The event study's far leads/lags come from one cohort only, so those points are effectively
  cohort-specific trends.
- No anticipation is assumed; the near-zero e = −2 coefficient is consistent with that but does not
  prove it.

I am not sure about the size of the effect; I am reasonably confident about its sign and that it is
not zero, given flat pre-trends, agreement across estimators and the detrending check.

## Choices I made without asking

1. Roles: unit = `county`, time = `year`, outcome = `employment_rate`, treatment = non-empty
   `program_start` with `post = year >= program_start`, per the README rule; verified `post = 0` for
   all never-treated rows, since the data has no ready-made post column.
2. Comparison group = never-treated counties only (not not-yet-treated), because 15 never-treated
   counties are available and they are the cleanest comparison.
3. Because timing is staggered, the main estimator is Callaway–Sant'Anna group-time ATT aggregated
   over post cells with cohort-size weights; TWFE is reported only as a cross-check.
4. Base period for each cohort is `g − 1`; no anticipation window is imposed.
5. Aggregation weights: cohort size (equal here); I also report the unweighted mean over post cells.
6. Standard errors: clustered by county; for the aggregate CS estimate and the event study I used a
   nonparametric county-level cluster bootstrap, 999 draws, seed 20261125, dropping draws that lose a
   cohort or all never-treated counties (0 dropped).
7. The 2x2 cross-check defines pre as all years before the cohort's start and post as all years from it,
   with never-treated counties over the same calendar windows, and I report it per cohort plus its mean.
8. Pre-trend test: joint Wald on event times −4, −3, −2, the range where all three cohorts contribute,
   using the bootstrap covariance.
9. Robustness check: linear pre-trend detrending per cohort (the plan asks for one check addressing the
   main threat, which I took to be the growing effect / differential trend).
10. I wrote an intermediate `panel_analysis.csv` (raw data plus constructed `treated`/`post`) into
    `results/county_jobs/` rather than touching `data/raw/`.
11. `00_cs_utils.py` is a helper module imported by the numbered scripts, not a step.
12. No covariates (plan), no additional checks beyond the plan, and the reviewer was not called, as instructed.
