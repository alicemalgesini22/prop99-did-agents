# Firm training programme and monthly revenue — DiD write-up

Run folder: `results/firm_training/`. Code: `src/firm_training/`, run in numeric order.
Data: `data/raw/firm_training.csv` (read only), described in `data/README_firm_training.md`.
Plan: `plans/plan_firm_training.md`.

## 1. Question

Did joining the management training programme change firms' monthly revenue?

## 2. Configuration (`results/firm_training/did_config.json`, written by `01_spec.py`)

| Role | Column / value | Where it comes from |
|---|---|---|
| unit | `firm_id` (50 firms, 1–50) | README: one row per (`firm_id`, `month`) |
| time | `month` (1–48) | README; 48 distinct values, no gaps |
| outcome | `revenue` (thousand euro) | README; never missing, checked |
| treated | rule `joined_training == True` → 15 firms | README: "True for firms that joined the programme, in every month" |
| treatment start | `month = 25` | README: programme launched in month 25; `after_launch` switches on exactly at 25 for every firm (checked) |
| controls | none | plan: "all rows, no covariates" |
| cluster | `firm_id` (50 clusters) | default; 15 of them treated |

**The `after_launch` trap.** `after_launch` is 1 for *every* firm from month 25 on
(mean 0.5 for treated and for control firms, and 0 rows where it disagrees with
`month >= 25`; printed by `01_spec.py`). It is a pure time dummy and is **not** used as the
treatment indicator. The treatment indicator is `treated firm × (month >= 25)`, which is 0
for all control-firm rows by construction.

## 3. Panel checks (`02_panel_checks.py` → `panel_checks.json`)

- 2,400 rows read; duplicates on (`firm_id`, `month`): 0 → nothing dropped.
- Missing outcome: 0 → nothing dropped. Missing unit/time: 0 → nothing dropped.
- Rows used: **2,400** = 50 firms × 48 months, perfectly balanced; every firm has all 48
  periods; no gaps in the calendar 1–48.
- Missing values elsewhere: `employees` has **300 missing rows, months 1–6, 50 rows in each
  of months 1,2,3,4,5,6, all 50 firms affected**. `employees` is not used (plan: no
  covariates), so no rows were dropped for it.
- `joined_training` is constant within firm (0 firms vary), 15 treated / 35 control.

## 4. Design checks (`03_design_checks.py` → `design_checks.json`)

- **15 treated units, 35 controls.** Single treatment cohort: the only start period present
  is month 25, and the data carry no firm-level adoption date (`joined_training` is constant
  within firm), so timing is **not staggered**. Plain two-way fixed effects on
  `treated × post` is therefore appropriate; the Goodman-Bacon / negative-weight problem
  does not arise here. If firms in reality joined at different dates, that information is
  not in this file and the estimate is an average over whatever exposure actually occurred.
- 15 treated units is enough to cluster, but only 15 treated clusters, so inference below
  relies mainly on a randomisation test rather than on the cluster-robust SE alone.
- Levels differ: pre-launch mean revenue 108.45 (treated) vs 92.66 (control). Firm fixed
  effects absorb this.
- **Pre-period trends:** differential linear trend (treated minus control, unit FE + common
  month slope) **+0.021 per month, SE 0.039, p = 0.59**. Separate pre-period slopes:
  treated +0.270/month (SE 0.032), control +0.249/month (SE 0.023). No detectable
  differential trend.
- Change over the last 6 pre-months vs the 6 before: treated −1.75, control −1.53,
  difference −0.22 (no pre-launch divergence in that window).
- Within-firm post-minus-pre change: treated 17.02 (sd 1.89, range 13.4–19.8), control 9.13
  (sd 1.56, range 5.9–11.7).

## 5. Raw trends (`04_raw_trends.py` → `raw_trends.png`, `raw_trends.csv`)

Both groups rise over the 48 months. The treated–control gap averages 15.79 before month 25
and 23.68 after; the jump happens at month 25 and then holds (`raw_trends.png`, right panel).
The pre-launch gap is noisy, ranging from 13.2 (month 1) to 18.9 (month 17) and 13.8 at
month 24.

## 6. Main estimate (`05_main_did.py` → `main_did.json`)

Two-way FE: `revenue ~ treated×post + firm FE + month FE`, all 2,400 rows, no covariates,
SEs clustered by firm.

| | estimate | SE | 95% CI | p |
|---|---|---|---|---|
| treated × post | **+7.889** | 0.5545 (cluster, 50 firms) | [6.802, 8.975] | 6.3e-46 |
| unclustered SE for reference | | 0.4387 | | |

- N = 2,400, parameters 98, R² = 0.958.
- **2×2 cross-check** (no FE): treated 108.45 → 125.47 (+17.02); control 92.66 → 101.79
  (+9.13); DiD = **+7.889**. Identical to the TWFE estimate to 4 decimals, as expected with
  a balanced panel and a single treatment cohort.
- The fast double-demeaning routine used in the permutation loop reproduces the OLS
  coefficient exactly (difference −8e-15), checked in the same script.

## 7. Event study (`06_event_study.py` → `event_study.csv`, `event_study.png`)

`treated × month` dummies, reference rel = −1 (month 24), SEs clustered by firm.

- **Pre-treatment coefficients are not flat at zero**: they average **+2.04**, drift upward
  only mildly (linear fit +0.047/month), and a joint test rejects zero
  (**F = 4.81 on 23 restrictions, p = 2e-06**). Individually, most pre-coefficients are
  between 0 and +4 with SEs around 1.5–2.3; the ones significant at 5% are rel −22, −8, −3,
  −2.
- The level of that pre-block is mostly one fact: the gap in the reference month (13.84) is
  about 2 thousand euro below the average pre-launch gap (15.79), so every pre-coefficient
  inherits roughly +2.
- **Post-treatment**: coefficient +7.34 at rel 0, +9.62 at rel 1, then a band of roughly
  +8 to +13; mean +9.84. So the effect is a level shift at month 25 that persists, and the
  event study reads slightly larger than the main estimate precisely because its reference
  month is low.
- Reading of the plot: pre-period looks approximately **flat** (no clear rise or fall), with
  a positive offset relative to the reference month; post-period jumps and stays.

## 8. Inference (`07_inference.py` → `inference.json`, `placebo_estimates*.csv`, `permutation_null.csv`)

- Cluster-robust SE by firm: 0.5545, t = 14.23, p = 6e-46. With only 15 treated clusters
  this p is likely too optimistic, so two design-based checks follow.
- **In-space placebo** (each control firm in turn as the only treated firm, 35 placebos):
  estimates range −5.74 to +0.20, mean −2.41. The true estimate ranks **1 of 36**;
  placebo p = rank/(n+1) = **0.028** (rank/n = 0.029). Caveat: these placebos have a
  treated group of size 1 whose comparison group contains the 15 truly treated firms, which
  mechanically pushes them negative. The clean version restricted to control firms only
  (35 placebos, mean 0.00, sd 1.61, range −3.35 to +2.63) also ranks the true estimate
  **1 of 36**, p = 0.028.
- **Randomisation test** with the same group size (1,000 random sets of 15 firms, seed
  20261121): null draws mean +0.05, sd 1.23, 5th/95th percentiles −1.96/+2.05. The true
  +7.89 is outside every draw: **p < 0.001** (0 of 1,000; the resolution limit is 0.001).

## 9. Robustness (`08_robustness.py` → `robustness.csv`, `robustness.json`)

| Specification | estimate | SE |
|---|---|---|
| main (firm + month FE) | 7.889 | 0.554 |
| **unit-specific linear trends for the 15 treated firms** | **8.346** | 0.954 |
| one common linear trend for treated firms | 8.346 | 0.952 |
| in-time placebo, fake start at month 13 (pre data only) | −0.012 | 0.566 |
| in-time placebo, fake start at month 19 (pre data only) | −0.156 | 0.804 |
| sample months 13–48 | 7.895 | 0.611 |
| sample months 7–48 | 7.700 | 0.614 |
| sample months 1–36 | 8.427 | 0.639 |
| pre = months 1–12 only, post = 25–48 | 7.883 | 0.636 |
| leave-one-treated-firm-out | 7.688 to 8.148 | — |

- Allowing each treated firm its own linear pre-trend moves the estimate **+0.458
  (+5.8 %)** and roughly doubles the SE (0.55 → 0.95), because identification now leans on
  extrapolating each firm's pre-trend. The sign and size survive. (The 15-trend and
  single-trend versions give an identical coefficient here; I verified this against a direct
  least-squares fit and against a synthetic dataset, so it is a property of the estimator
  with one cohort, not a coding error.)
- **Main threat in the data, and the check that addresses it:** the pre-launch gap is noisy
  and the reference month (24) sits about 2 below the pre-launch average, so the event study
  and the 2×2 could in principle be picking up pre-existing divergence. The in-time placebos
  test exactly that: a fake launch inside the pre-period produces **−0.01 (month 13)** and
  **−0.16 (month 19)**, both indistinguishable from zero. Together with the pre-trend test
  (+0.021/month, p = 0.59) this argues against the estimate being a pre-existing trend, but
  it does not remove the +2 offset in the event study.
- The effect is not driven by one firm: dropping any single treated firm leaves 7.69–8.15.
- Descriptive note (`09_post_persistence.py` → `post_persistence.json`): the post-launch gap
  averages 24.22 in months 25–36 and 23.14 in months 37–48 (slope −0.059/month), i.e. the
  level shift is roughly flat, possibly fading slightly.

## 10. Conclusion

Against the plan's "what would prove me wrong": the estimate is not close to zero
(+7.9 thousand euro per month on a pre-launch control mean of 92.7, about 8.5 %), its sign
never changes across the checks (range +7.69 to +8.43, plus +8.35 with treated-specific
trends), and inference rejects zero at 5 % on every test I ran (cluster p ≈ 6e-46,
randomisation p < 0.001, placebo rank 1 of 36, p = 0.028). The pre-treatment event-study
coefficients do not show a clear trend break, but they are not jointly zero, so the third
part of the plan's list is only partly satisfied.

My reading: the data are consistent with the programme raising revenue by roughly
7.9 thousand euro per month (95 % CI 6.8–9.0 with firm-clustered SEs; 6.5–10.2 when each
treated firm gets its own linear trend). I am **not sure** the number is exactly 7.9,
because the pre-period gap is noisy and the event study anchored on month 24 gives about
9.8, so a range of roughly 7.5–10 is what I would defend.

### Limits

- **Adoption dates are not observed.** `joined_training` is constant within firm and the only
  timing information is the launch month. If firms actually joined at different months, this
  design cannot see it and the estimate mixes different exposure lengths.
- **15 treated clusters.** The cluster-robust p-value should not be taken at face value; the
  randomisation test (p < 0.001) is the inference I trust, and it is limited to 1,000 draws.
- **No covariates**, by the plan. Any shock at month 25 that hit the 15 treated firms
  differently from the 35 controls is not controlled for. `employees` could not be used
  without dropping months 1–6 (300 missing rows) and is not in the plan.
- **Revenue is in nominal thousand euro**; no deflator is provided, but month fixed effects
  absorb any common price/wage movement, so this matters only if inflation differed by group.
- **Levels, unweighted.** Effects are estimated in euro, so large firms count the same as
  small ones; I did not estimate a proportional specification (not in the plan).
- **Pre-period noise.** The pre-launch gap fluctuates by about ±2 thousand euro around its
  mean, which is a quarter of the estimated effect; the reference month happens to be low.
- I did not test for spillovers between firms (no information on which firms interact).

## 11. Files

| File | Made by |
|---|---|
| `did_config.json` | `01_spec.py` |
| `panel_checks.json` | `02_panel_checks.py` |
| `design_checks.json` | `03_design_checks.py` |
| `raw_trends.png`, `raw_trends.csv` | `04_raw_trends.py` |
| `main_did.json` | `05_main_did.py` |
| `event_study.csv`, `event_study.png`, `event_study.json` | `06_event_study.py` |
| `inference.json`, `placebo_estimates.csv`, `placebo_estimates_clean.csv`, `permutation_null.csv` | `07_inference.py` |
| `robustness.csv`, `robustness.json` | `08_robustness.py` |
| `post_persistence.json` | `09_post_persistence.py` |
| this file | written by hand from the files above |

## Choices I made without asking

1. **Treatment indicator** = `joined_training == True` × `month >= 25`. I rejected
   `after_launch` as the treatment because it is 1 for every firm after month 25 (checked:
   0 rows disagree with `month >= 25`).
2. **Treatment start = month 25 for all 15 treated firms**, from the README's launch date and
   the `after_launch` column; the data contain no firm-level adoption date.
3. **Main specification**: two-way FE, all rows, no covariates (plan), firm and month FE,
   treatment indicator as in (1).
4. **SEs clustered by firm** (50 clusters), with the unclustered SE reported for reference.
5. **Because only 15 firms are treated**, I added a randomisation test (1,000 draws, seed
   20261121) and treated it as the primary inference; the placebo test follows the procedure.
6. **Placebo design**: each control firm in turn as the sole treated firm, and additionally a
   version restricted to control firms (the literal version's comparison group contains the
   truly treated firms and is therefore biased downward). Both are reported.
7. **Event study**: saturated `treated × month` dummies with rel = −1 (month 24) as reference,
   i.e. the last pre-treatment period as the procedure requires; 95 % CI, clustered SEs.
8. **Robustness set**: the required treated-specific linear trends, plus in-time placebos at
   months 13 and 19, three pre-window restrictions, and leave-one-treated-firm-out. I chose
   the in-time placebo as the plan's "one check that addresses the main threat" (an unstable
   pre-launch gap), because it tests whether the design manufactures an effect where none
   can exist.
9. **No rows dropped** at any stage; the panel is balanced and `revenue` is complete, so no
   missing-data decision was needed. `employees` was left out entirely rather than imputed.
10. **No weighting, no transformation of the outcome** (plan fixes revenue in levels), and no
    additional covariates (not requested).
