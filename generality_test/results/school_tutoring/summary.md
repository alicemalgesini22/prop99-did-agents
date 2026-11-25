# School tutoring and reading scores — DiD write-up

Run folder: `results/school_tutoring/` · Code: `src/school_tutoring/` · Seed: `20261121`
Plan: `plans/plan_school_tutoring.md` · Data description: `data/README_school_tutoring.md`

## 1. Question and specification

Did the tutoring programme change schools' average reading scores? Design: difference-in-
differences with school and year fixed effects, all rows, no covariates.

`did_config.json` (written by `01_spec.py`):

| Role | Column / value | Where it comes from |
|---|---|---|
| data | `data/raw/school_tutoring.csv` | named in the prompt |
| unit | `school_id` | 60 distinct integer ids, 1–60, one row per school-year |
| time | `year` | 10 annual periods, 2012–2021, no gaps |
| outcome | `reading_score` | float, test points, no missing values |
| treated units | `tutoring_school == True` → 20 schools | README: constant within school; the data confirm 0 schools change status |
| treatment start | `year >= 2017` | README ("from the 2017 school year"); see the caveat in §3 |
| treatment indicator | `treated × post` | built in the script; no ready-made post column exists in the data |
| controls | none | plan says all rows, no covariates; `students` was not requested |
| cluster | `school_id` (60 clusters) | units are the randomisation unit |

There is no `post`/`after` column in this file, so nothing could be used unthinkingly: the
post indicator is constructed as `year >= 2017` and is therefore 0 for every control row by
construction (`01_spec.py` prints the column list it searched).

## 2. Panel checks — `02_panel_checks.py` → `panel_checks.json`

- 600 rows read; 60 schools × 10 years; 0 duplicate `(school_id, year)` pairs; 0 rows dropped.
- No missing values in any column, so there are **no periods with missing data** to list
  (`reading_score` is complete in all 10 years for all 60 schools).
- Balanced: every school is observed in every year 2012–2021 (600 = 60 × 10).
- 20 treated and 40 control schools, with the same split in every period.
- Rows used downstream: 600. No filter was applied at any point.

## 3. Design checks — `03_design_checks.py` → `design_checks.json`

- **Treated units: 20.** That is above the "fewer than about 5" threshold, so clustered
  standard errors by school (60 clusters) are usable as the primary inference.
- **Timing: not staggered.** A single common start date (2017) for all treated schools, so
  the staggered-adoption bias of plain two-way FE does not arise and no
  Callaway–Sant'Anna / Sun–Abraham estimator is needed.
- **Caveat on timing:** the treatment flag is constant within school, so the data cannot
  show each school's start date. 2017 is taken from the README and is *unverifiable in the
  data*. I am not sure it is exactly right for every school; §8 tests how much that matters.
- **Pre-treatment differential trend (the main testable threat):** with pre-2017 rows only
  (300 rows), the coefficient on `treated × linear trend` is **−0.112 points/year
  (cluster SE 0.608, p = 0.854)** — no detectable divergence. Pre-period mean levels differ
  by about 10 points (control 510.48, treated 500.04), which school fixed effects absorb.
  Mean within-school pre-slopes are close: control 1.538 (sd 2.247), treated 1.426 (sd 1.849).

## 4. Raw trends — `04_raw_trends.py` → `raw_trends.csv`, `raw_trends.png`

Group means rise in both groups over the whole window; the treated–control gap moves from a
mean of −10.436 before 2017 to −10.889 from 2017, a change of −0.453 points. The gap series
in the right-hand panel shows no break at the vertical line, only year-to-year noise
(2013: −12.97, 2018: −9.12).

## 5. Main estimate — `05_main_did.py` → `main_did.json`

`reading_score ~ treated×post + school FE + year FE`, all 600 rows, SE clustered by school:

**−0.4532 points (SE 0.9633, t = −0.470, p = 0.638, 95% CI [−2.3411, 1.4348]).**

Cross-checks: the double-demeaning formula reproduces the coefficient exactly (−0.453150,
difference 1.4e−13), and the simple 2×2 difference of means gives the same number
(treated +6.679, control +7.132, DiD −0.4531).

## 6. Event study — `06_event_study.py` → `event_study.csv`, `event_study.json`, `event_study.png`

Reference period 2016 (event time −1); unit and year FE; 95% CI clustered by school; 600
rows, every school contributes to every event time, so no binning.

| rel. year | −5 | −4 | −3 | −2 | −1 | 0 | +1 | +2 | +3 | +4 |
|---|---|---|---|---|---|---|---|---|---|---|
| coef | 1.831 | −2.714 | 0.172 | −0.173 | 0 | −1.930 | 1.144 | 0.321 | −1.398 | −1.287 |
| SE | 2.329 | 2.498 | 2.255 | 2.591 | — | 2.113 | 2.420 | 2.667 | 2.532 | 2.416 |

The pre-treatment coefficients are **flat, not trending**: 1.83, −2.71, 0.17, −0.17, i.e.
noisy but with no drift, and the joint test of the four pre-period coefficients is
F = 0.868, p = 0.488. The 2013 wobble (−2.7) is the largest pre-period deviation and is
individually insignificant (SE 2.50). Post-treatment coefficients are all small and
individually insignificant; joint test of the five post coefficients: F = 0.368, p = 0.869.

## 7. Inference — `07_inference.py` → `inference.json`, `randomisation_draws.csv`

- **Primary (20 treated units, 60 clusters):** cluster-robust SE 0.9633, p = 0.638. The
  estimate does not reject zero at 5%; the CI rules out effects below −2.34 points and above
  +1.43 points.
- **Secondary, randomisation inference** (2000 draws, seed 20261121, re-assigning the 20
  treated labels among the 60 schools, balanced panel so the double-demeaning formula is
  exact): placebo draws have mean 0.013 and sd 0.954; 1264 of 2000 draws are at least as
  extreme as the observed −0.453, **p = 0.632**. Same conclusion as the clustered SE.

## 8. Robustness — `08_robustness.py` → `robustness.csv`; `09_placebo_start.py` → `placebo_start_dates.csv`

**Pre-trend specifications** (trend centred on 2016, SE clustered by school, 600 rows):

| spec | coef | SE | p |
|---|---|---|---|
| main TWFE | −0.4532 | 0.9633 | 0.638 |
| (a) treated-group linear trend | 0.1413 | 2.2136 | 0.949 |
| (b) school-specific linear trends, all 60 schools | 0.1413 | 2.3459 | 0.952 |
| (c) unit-specific trends for the 20 treated schools | 0.1413 | 2.2544 | 0.950 |

The estimate moves by +0.59 points when trends are allowed, from −0.45 to +0.14 — well
inside one standard error, so the conclusion is unchanged. Two things I checked rather than
assumed: (i) specification (b) is rank-deficient by one column because a linear trend is
constant within a year; one slope is dropped as the normalisation and the `_did` coefficient
is verified against the full 60-slope design (identical to 6 decimals); (ii) **(a), (b) and
(c) return the same coefficient to 4 decimals** — with one common start date and a balanced
panel the residualised treated-school trend columns are all proportional to each other
(correlation 0.160251 for every one of the 20 columns), so the three trend variants collapse
to one estimator. I therefore do not treat the trend robustness as independent evidence on
parallel trends; the evidence on that assumption is the event study (§6) and the pre-period
trend test (§3). That collapse is an empirical fact in this panel; that it holds in general
is **my inference, unverified**.

**Placebo start dates** (the check aimed at the main threat — the unverifiable date):

- Pre-2017 rows only (300 rows, 300 dropped so the real programme cannot contribute):
  fake start 2014 → **+0.4415 (SE 1.7748, p = 0.804)**; fake start 2015 → **+0.1505
  (SE 1.9429, p = 0.938)**. Placebo breaks in periods with no programme produce effects of
  the same small magnitude as the main estimate, so a coefficient of about half a point is
  what this design produces from noise alone.
- Moving the assumed start date on the full sample: 2016 → −0.3039 (SE 1.0345),
  2017 → −0.4532 (SE 0.9633), 2018 → +0.1639 (SE 1.1202). All near zero and insignificant.

## 9. Conclusion

The estimate is a **near-zero, imprecise** change in reading scores: −0.45 points
(SE 0.96, 95% CI [−2.34, 1.43]) against a sample mean of 510.49 points (sd 27.89). All three
of the plan's falsification conditions are met — the estimate is close to zero and changes
sign across specifications, the event study shows no differential pre-trend, and the
inference does not reject zero at 5%. **I make no causal claim that the programme raised
reading scores**, and no claim that it lowered them: the data are consistent with effects
anywhere between −2.34 and +1.43 points.

## 10. Limits

- **Power.** The clustered SE is about 1 point, so effects of roughly ±2 points or smaller
  cannot be distinguished from zero. A null result here is weak evidence of "no effect".
- **Treatment date unverifiable.** The flag is constant within school; 2017 comes only from
  the README. The placebo and start-date checks (§8) show the answer does not depend on it
  within ±1 year, but I cannot verify the date school by school.
- **Outcome is a school average**, so within-school composition changes (which pupils sit the
  test) are invisible, and `students` (enrolment) was not used as a covariate because the
  plan excludes covariates.
- **The post window is 2017–2021**, which contains the 2020 and 2021 school years. If the
  disruption of those years hit treated and control schools differently, the DiD absorbs it
  as programme effect; nothing in this design separates the two (**my inference,
  unverified**).
- **Trend robustness is degenerate here** (§8), so the parallel-trends assumption rests on
  the event study and the pre-period trend test, both of which are flat but imprecise.

## Files

| Output | Script |
|---|---|
| `did_config.json` | `01_spec.py` |
| `panel_checks.json` | `02_panel_checks.py` |
| `design_checks.json` | `03_design_checks.py` |
| `raw_trends.csv`, `raw_trends.png` | `04_raw_trends.py` |
| `main_did.json` | `05_main_did.py` |
| `event_study.csv/.json/.png` | `06_event_study.py` |
| `inference.json`, `randomisation_draws.csv` | `07_inference.py` |
| `robustness.csv`, `robustness.json` | `08_robustness.py` |
| `placebo_start_dates.csv/.json` | `09_placebo_start.py` |
| shared loader and estimators | `didlib.py` |

Run in order 01 → 09 with `uv run python src/school_tutoring/NN_*.py`.

## Choices I made without asking

1. **Treatment indicator built from the calendar** (`year >= 2017`) because the file has no
   post/after column; checked that this is 0 for every control row.
2. **2017 as the start date for all treated schools**, from the README, since the flag is
   constant within school. Flagged as unverifiable, and tested with placebo and ±1-year
   sensitivity.
3. **No covariates** (`students` unused), following the plan.
4. **Clustered SE by school as the primary inference** (20 treated units, 60 clusters), with
   randomisation inference as a secondary check that the plan did not ask for.
5. **Event-study reference period = 2016** (last pre-treatment year), all 10 event times
   included with no endpoint binning, since every school is observed in every year.
6. **Trend robustness implemented three ways** (group trend, all-school trends, treated-school
   trends), centring the trend on 2016; one slope dropped in the all-school version to remove
   the exact redundancy with the year effects, with the coefficient verified against the full
   design.
7. **Placebo start dates 2014 and 2015** on pre-2017 rows only, chosen as the only two dates
   that leave at least two pre-periods and at least two post-periods inside the pre-window.
8. **Randomisation inference with 2000 draws and seed 20261121**; placebo p-value taken as
   the two-sided share of |draw| ≥ |observed|.
9. **No rows dropped anywhere**; no trimming of outliers, which were not requested.
