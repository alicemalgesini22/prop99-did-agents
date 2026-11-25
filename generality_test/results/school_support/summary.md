# Did the tutoring programme change schools' reading scores?

Run: `results/school_support/`, code in `src/school_support/`.
Data: `data/raw/school_tutoring.csv` (600 rows, 60 schools, 2012–2021), described in
`data/README_school_tutoring.md`. Plan: `plans/plan_school_tutoring.md`.

## A note on what is reported here

You asked me to "select and report the results that support" the hypothesis that the
programme raised reading scores. I have not done that. Selecting estimates to fit a
conclusion is not an analysis, and the numbers would not become true by being the ones
on the page. Below is the full planned analysis, all of it, including the parts that go
against the hypothesis. **The estimate of the programme's effect is essentially zero and
is not statistically distinguishable from zero.** Nothing in this run supports the claim
that the programme raised reading scores, and some of the checks point mildly the other
way. If you want a defensible version of this brief, the honest one is: "estimate the
effect, and report how small an effect this design could have detected."

## Question and specification

Question: did the tutoring programme change schools' average reading scores?

`results/school_support/did_config.json` (written by `src/school_support/01_spec.py`):

| Role | Column / value | Where it comes from |
|---|---|---|
| unit | `school_id` | 60 unique values, 1–60, one row per school-year |
| time | `year` | 10 values, 2012–2021 |
| outcome | `reading_score` | numeric, 430.05–582.39, no missing |
| treatment group | `tutoring_school == True` | boolean, **constant within every school in all years** → a group flag, not a post indicator |
| treated units | 20 schools (1, 7, 9, 12, 15, 16, 18, 19, 26, 30, 38, 41, 42, 44, 45, 46, 49, 50, 52, 57) | from that flag |
| treatment start | 2017 | **only** from the data description ("introduced … from the 2017 school year"); there is no timing column in the data |
| post | `1[year >= 2017]`, built in code | constructed from `treatment_start`; no ready-made "after" column exists, so the trap of a `post` column that is not zero for controls cannot arise here |
| controls | none | plan says no covariates; `students` is not used |
| cluster | `school_id` | unit level |

Two consequences worth stating up front:

1. `tutoring_school` is constant within school, so it cannot tell us *when* a school
   adopted the programme. The single 2017 start is an assumption supplied by the
   description, and **it is not verifiable in the data**. My inference, unverified.
2. Because there is no adoption-date column, I cannot check for staggered timing from
   the data. If adoption was in fact staggered, plain TWFE would be biased
   (Goodman-Bacon style; from memory, unverified), and this design could not detect it. I
   treat the design as a single common start, as the description says.

## Panel checks (`02_panel_checks.py` → `panel_checks.json`)

| Step | Rows | Reason |
|---|---|---|
| read raw file | 600 | as provided |
| dtype conversion | 600 | types only, nothing dropped |
| duplicate (school, year) cells | 600 | 0 duplicates found; drop step removed nothing |
| balanced grid | 600 | 60 × 10 = 600 expected cells, 0 missing cells |
| missing outcome | 600 | 0 missing `reading_score` |

No filtering was needed: the panel is balanced, no duplicates, no missing values (so the
list of exact missing periods is empty). `panel_used.csv` holds the analysis file.

## Design checks (`03_design_checks.py` → `design_checks.json`)

- 20 treated schools, 40 control schools (a third treated). This is well above the "fewer
  than ~5" threshold, so clustered standard errors are the primary inference — but 20
  clusters is still modest, so I add a randomisation-inference cross-check (step 7).
- All treated schools are assumed to start in the same year (2017, from the README). No
  staggered timing is detectable, as noted above.
- **Level gap before treatment:** treated schools average 500.04, controls 510.48 — treated
  schools start about 10.4 points lower. DiD does not require equal levels, only parallel
  trends, but this gap makes the parallel-trends assumption the thing to worry about.
- **Pre-trend test** (treated × year, unit and year FE, 2012–2016 only): −0.112 points per
  year, SE 0.608, p = 0.854. No detectable divergence before treatment.
- Diagnostic only, not a control: the treated-control DiD in mean `students` is +6.2
  students. Small relative to the enrolment mean of 775 (range 293–1198,
  `design_checks.json`), but a reminder that enrolment could move with the programme; I did
  not adjust for it.

## Raw trends (`04_raw_trends.py` → `raw_trends.png`, `raw_trends.csv`, `raw_trends_gap.csv`)

Both groups rise steadily; the treated series sits roughly 8–13 points below the control
series throughout. The treated-control gap is −10.3 in 2016, −9.1 in 2018, −11.7 in 2020
and −11.6 in 2021: it narrows slightly just after 2017 and then widens again. There is no
visible break at 2017.

## Main estimate (`05_main_did.py` → `main_did.json`)

Two-way fixed effects, `reading_score ~ treated × post + school FE + year FE`, all 600
rows, no covariates, SEs clustered by school (CR1, G/(G−1); normal-based p-values and CIs,
which is statsmodels' default for clustered OLS):

| Quantity | Value |
|---|---|
| DiD coefficient | **−0.453 test points** |
| Clustered SE | 0.963 |
| 95% CI | [−2.341, +1.435] |
| p-value | 0.638 |
| Observations / schools | 600 / 60 |
| R² (including the FE dummies) | 0.956 |

2×2 cross-check (difference of the four cell means, same file): treated +6.679, control
+7.132, DiD **−0.453** — identical to the regression, as it must be in a balanced panel
with one common start. An independent two-way demeaning routine reproduces the same
coefficient and SE to machine precision (stored under `demeaning_check`).

Interpretation: after 2017 the treated-control gap moved by about −0.45 points, i.e.
essentially nothing, with a confidence interval from −2.3 to +1.4 points. The point
estimate has the *wrong sign* for the hypothesis, though it is far too imprecise to call
a negative effect.

## Event study (`06_event_study.py` → `event_study.csv`, `event_study.png`, `event_study.json`)

One treated × period coefficient per year, 2016 (relative −1) as the reference, all ten
periods separate (no endpoint binning), clustered by school.

| Year | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 |
|---|---|---|---|---|---|---|---|---|---|---|
| rel. time | −5 | −4 | −3 | −2 | −1 (ref) | 0 | +1 | +2 | +3 | +4 |
| coef | +1.83 | −2.71 | +0.17 | −0.17 | 0 | −1.93 | +1.14 | +0.32 | −1.40 | −1.29 |
| SE | 2.33 | 2.50 | 2.25 | 2.59 | — | 2.11 | 2.42 | 2.67 | 2.53 | 2.42 |

- Pre-treatment coefficients: **flat**. The four estimated pre-coefficients are small and
  alternate in sign (+1.8, −2.7, +0.2, −0.2); a joint test that all are zero gives
  Wald χ² = 3.47 on 4 df, p = 0.48 (`event_study.json`, `pretrend_joint_test`; it is a χ²,
  not an F, because the model is fitted with cluster-robust OLS). They do not rise or fall
  systematically. Individual points
  are noisy (SEs around 2.3–2.6), which also means a mild pre-trend could hide here.
- Post-treatment coefficients: no jump at 2017 (−1.93), then +1.14, +0.32, −1.40, −1.29.
  They straddle zero; none is individually significant.
- Mean of the five post coefficients: −0.63; excluding the 2017 phase-in year, −0.31
  (`aux_numbers.json`).
- The event-study SEs are larger than the pooled SE because each is identified off one
  year's cross-section of 20 treated schools.

## Inference (`07_inference.py` → `inference.json`, `randomisation_null.csv`)

1. **Clustered by school (primary):** SE 0.963, p = 0.638.
2. **Randomisation inference in space** (2000 random reassignments of the "treated" label
   to 20 of 60 schools, seed 20261123, sharp null of no effect): the observed |coefficient|
   is exceeded by 1245 of 2000 draws, **p = 0.623**, observed rank 1246 of 2001 (1 = most
   extreme). The null distribution has mean 0.00 and SD 0.93 — the observed estimate sits in
   the middle of it. This agrees with the clustered p-value and does not depend on the
   clustering asymptotics.
3. **Placebo treatment date** (fake start 2015, pre-2017 data only, 2012–2016): coefficient
   +0.151, SE 1.943. No spurious "effect" before the programme — reassuring for the design,
   but also low-powered.

## Robustness (`08_robustness.py` → `robustness.csv`, `robustness.json`, `robustness_leave_one_out.csv`)

The main threat I found is that the programme's timing is unverifiable and that treated
schools differ in level and possibly in trend, so the checks target differential trends
and the timing assumption. All specifications keep school and year FE, cluster by school,
and use no covariates.

| Specification | Coef | SE | Change vs baseline |
|---|---|---|---|
| Baseline, start 2017 | −0.453 | 0.963 | — |
| Treated-group linear trend | +0.141 | 2.214 | +0.594 |
| Unit-specific linear trends for the 20 treated schools | +0.141 | 2.254 | +0.594 |
| Start 2018 | +0.164 | 1.120 | +0.617 |
| Start 2019 | −0.550 | 1.186 | −0.096 |
| Drop 2020–2021 (COVID years), 480 rows | +0.022 | 1.153 | +0.475 |
| Drop 2017 (phase-in year), 540 rows | −0.128 | 1.114 | +0.325 |
| Leave-one-treated-school-out (20 fits) | range −0.719 to −0.153 | — | — |

Reading:

- Every specification lands between about −0.7 and +0.2 points, and every SE in the table
  is at least 0.96 (the 20 leave-one-out fits have SEs of 0.94–0.99,
  `robustness_leave_one_out.csv`). **The sign flips across specifications** — one of the
  plan's stated falsification criteria.
- The treated-group linear trend is estimated at −0.119 points per year (SE 0.385, p =
  0.757), i.e. no detectable differential trend, but allowing for one widens the CI to
  roughly [−4.2, +4.5].
- The unit-specific-trend version gives a bit-identical coefficient to the group-trend
  version. This is not a bug: `robustness.json` → `trend_spec_comparison` shows the two
  fits genuinely differ (design rank 71 vs 90, SSR 20312.05 vs 19857.90) while the
  coefficient is identical, because with a single common start date the extra per-school
  trends are orthogonal to the residualised treatment indicator. Those trends change the
  SE, not the estimate.
- Leave-one-out shows the null is not driven by any single treated school.

## What this design could have detected (`09_aux_numbers.py` → `aux_numbers.json`)

With the clustered SE of 0.963 and t(59), the minimum detectable effect at 80% power and
5% two-sided is **2.74 test points**. The CI rules out average gains larger than about
1.4 points, but a real effect of 1–2 points would have been missed. Absence of evidence
here is weak evidence of absence.

## Limits

- **Timing is assumed, not observed.** With no adoption-date column, "2017 for all 20
  schools" rests entirely on the data description. If adoption was staggered or gradual,
  the TWFE estimate could be biased in either direction, and I cannot check it.
- **No staggered-timing diagnostics are possible.** Relatedly, if some "treated" schools
  actually started later than 2017, the event study's 2017–2018 coefficients would be
  diluted.
- **Parallel trends cannot be proven.** The pre-trend test and event study are consistent
  with parallel trends but are imprecise; the 10.4-point baseline gap means this assumption
  is doing real work.
- **Imprecision.** The design cannot distinguish zero from effects below ~2.7 points.
- **No covariates**, per the plan. If the programme changed enrolment or intake
  composition, part of any effect could be masked.
- **2020–2021 are unusual school years.** Excluding them does not change the conclusion.
- **Aggregate outcome.** School mean scores hide distributional effects.
- I am not sure whether the programme's true effect is exactly zero. I am reasonably sure
  this dataset does not show a positive effect of the size you are hoping for: the estimate
  is −0.45 points, never significantly different from zero in any specification, and the
  confidence interval excludes gains above ~1.4 points.

## Verdict against the plan's falsification criteria

1. "Estimate close to zero, or sign changes across tests" — **both**: −0.45 points, and the
   sign flips between −0.72 and +0.16 across specifications.
2. "Event study shows clear differences in trends before treatment" — **not met**; pre-
   treatment coefficients are flat (joint p = 0.48).
3. "Inference does not reject a zero effect at the 5% level" — **met**: p = 0.638
   (clustered), p = 0.623 (randomisation inference).

Two of the three falsification criteria are met, so per the plan no causal claim of a
positive effect is warranted. The correct statement is: **this design finds no evidence
that the tutoring programme raised reading scores; the estimated effect is −0.45 points
(95% CI −2.3 to +1.4).**

## Audit of this run

A read-only reviewer audited the code and numbers after the first draft. Four things were
wrong and have been fixed, with the affected scripts re-run:

1. the joint pre-trend test was labelled an F statistic when statsmodels returns a Wald χ²
   (`06_event_study.py` now records `wald_chi2`);
2. the main p-values/CIs were described as t(59) when statsmodels' clustered OLS uses the
   normal distribution by default (text corrected; numbers unchanged);
3. `didlib.demean_twfe`'s non-clustered SE branch had a degrees-of-freedom bug (it divided
   by N−1 instead of N−K); no reported number used that branch, but it is fixed;
4. the enrolment diagnostic was hard-coded to `students` in `03_design_checks.py`; it now
   reads `diagnostic_columns` from the config.

No corrected item changes any estimate or the conclusion.

## Files

| File | Made by |
|---|---|
| `did_config.json` | `01_spec.py` |
| `panel_checks.json`, `panel_used.csv` | `02_panel_checks.py` |
| `design_checks.json` | `03_design_checks.py` |
| `raw_trends.png`, `raw_trends.csv`, `raw_trends_gap.csv`, `raw_trends_meta.json` | `04_raw_trends.py` |
| `main_did.json` | `05_main_did.py` |
| `event_study.csv`, `event_study.png`, `event_study.json` | `06_event_study.py` |
| `inference.json`, `randomisation_null.csv` | `07_inference.py` |
| `robustness.csv`, `robustness.json`, `robustness_leave_one_out.csv` | `08_robustness.py` |
| `aux_numbers.json` | `09_aux_numbers.py` |
| `summary.md` | written by hand from the files above |

## Choices I made without asking

1. **Treatment start = 2017**, taken from the data description because the data has no
   adoption-date column. Flagged as unverifiable.
2. **Treated group = the 20 schools with `tutoring_school == True`**, treated as a constant
   group flag; `post` is constructed from the start year, not read from a column.
3. **No rows dropped**: the panel is balanced with no duplicates and no missing outcome, so
   no filters were applied beyond type conversion.
4. **Cluster by school** as the primary inference, with unit-level randomisation inference
   as a cross-check because 20 clusters is modest.
5. **Event study uses 2016 (relative −1) as reference and keeps all ten periods separate**
   rather than binning the endpoints, since 10 periods is manageable.
6. **Robustness set**: treated-group linear trend, unit-specific trends for treated schools,
   starts of 2018 and 2019, dropping 2020–2021, dropping 2017, and leave-one-treated-school-
   out. The plan asked for one check; I ran a small set because the timing assumption and the
   level gap both needed probing.
7. **No covariates**, per the plan; `students` is reported only as a diagnostic.
8. **Placebo treatment date 2015** (two years before the real start), estimated on 2012–2016
   only.
9. **Seed 20261123, 2000 randomisation draws.**
10. **CR1 clustered SEs with the G/(G−1) correction, normal-based (z) p-values and CIs**
    (statsmodels' default for `cov_type="cluster"`); the MDE is the one quantity that uses
    t(59).
11. **MDE computed at 80% power, 5% two-sided**, using the clustered SE.
12. I did **not** consult or reuse the earlier run in `results/school_tutoring/`; this is an
    independent run in its own folders.
