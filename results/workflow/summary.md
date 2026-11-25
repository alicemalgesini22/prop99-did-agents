# Summary — Difference-in-Differences: California Proposition 99 and per-capita cigarette sales

Run date: 12 Nov 2026. Agent model: GLM-5.3-Flash Free in OpenCode (per plan.md model log).
All numbers below come from files in `results/workflow/`; the script that produced each file is named.
All output paths below are relative to `C:\Users\alice\my-analysis`.

## 1. Question

Did California's Proposition 99 (25-cent/pack tax, effective 1 January 1989) reduce
per-capita cigarette **sales** (packs/person/year, tax-paid — `cigsale` measures sales,
not consumption) in California relative to the other 38 states, compared with what would
have happened without it? (From `plan.md`.)

## 2. Configuration

Config file: `results/workflow/did_config.json` (written in step 1; confirmed by the human).

| Field | Value | Basis |
|---|---|---|
| `data_path` | `data/raw/california_tobacco.csv` | plan.md, data/README.md |
| `unit` | `state` (numeric ID 1–39) | panel is state–year |
| `time` | `year` (1970–2000) | data |
| `outcome` | `cigsale` | packs/person/year; **sales, not consumption** (README, AGENTS.md) |
| `treated_units` | state 3 (California) | `california` is True in exactly 31 rows, all state 3 |
| `treatment_rule` | `california == True AND year >= 1989` | gives exactly 12 treated rows |
| `treatment_start` | 1989 | Proposition 99 effective 1 Jan 1989 |
| `controls` | the other 38 states (IDs 1, 2, 4–39) | plan.md |
| `controls_covariates` | none | plan.md test 1; AGENTS.md forbids covariates without asking |
| `cluster` | `state` | default; **not used for inference** (see step 7) |

Key treatment check: `after_treatment` is **not** the treatment variable — it is 1 in 468
rows, of which 456 are non-California (verified in step 1; `02_panel_checks.txt`).
The treatment is `california AND year >= 1989` (AGENTS.md rule), never `after_treatment` alone.
`data/taxonomy.json` does not exist; roles were filled from `data/README.md` and verified against the data.

## 3. Checks and estimates

### Step 2 — Panel checks (`src/workflow/01_panel_checks.py` → `results/workflow/02_panel_checks.txt`)
- 1,209 rows; 39 states; 31 years (1970–2000); **0** duplicate `(state, year)` pairs;
  **balanced** (39 × 31 = 1,209; every state has exactly 31 rows).
- Missing values (exact years, missing for all 39 units): `lnincome` 1970–71, 1998–2000;
  `beer` 1970–1983, 1998–2000; `age15to24` 1991–2000. `cigsale`, `retprice`: no missing.
- **Filters: none. Rows after filters: 1,209 (unchanged).** Reasons: no duplicates, outcome
  and treatment columns complete, unused covariates' gaps irrelevant.

### Step 3 — Design checks (`src/workflow/02_design_checks.py` → `results/workflow/03_design_checks.txt`)
- **1 treated unit** (state 3), treatment starts 1989 — common timing, no staggered adoption,
  so plain TWFE is applicable.
- **Only 1 treated unit ⇒ clustered SEs are not reliable; inference uses the placebo test.**

### Step 4 — Raw trends (`src/workflow/03_raw_trends.py` → `results/workflow/04_raw_trends.png`, `.csv`)
- Both series decline 1970–2000. In 1970 California sold more than the control mean
  (123.0 vs 120.08; `04_raw_trends.csv`). The raw level gap is not informative by itself;
  the DiD/FE estimate is what matters.
- **Pre-trend visible in raw data:** California declined faster than the control mean well
  before 1989 (mid-1970s CA ≈ 127 vs control ≈ 141; 1988: CA 90.10 vs control 113.82). The
  treated-vs-control gap was already **widening** (becoming more negative) before treatment.

### Step 5 — Main estimate (`src/workflow/04_main_estimate.py` → `results/workflow/05_main_estimate.txt`)
- TWFE: `cigsale ~ treat_post + C(state) + C(year)`, all 1,209 rows, no covariates.
- **treat_post coefficient: −27.349 packs per person per year** (classical SE 4.409; cluster-by-state
  SE 2.849 — the cluster SE is reported for reference but is **not reliable**, see step 3).
- Cross-check, 2×2 difference of means: California −55.861 (116.211 → 60.350) vs controls
  −28.511 (130.570 → 102.058) → **DiD = −27.349**, identical to TWFE (balanced panel).

### Step 6 — Event study (`src/workflow/05_event_study.py` → `results/workflow/06_event_study.txt`, `.csv`, `.png`)
- One treated × year coefficient per year, **reference = 1988**, state FE + year FE, N = 1,209.
- **Pre-period coefficients are NOT flat:** +26.6 (1970) declining monotonically to ≈ +3
  (1983–1987). The gap vs controls was moving against California throughout the pre-period,
  mainly in the 1970s; roughly flat 1983–1987. All pre CIs are wide (classical SE ≈ 17.0) and
  include zero.
- **Post-period coefficients fall steadily** from −3.5 (1989) to −26.8 (2000), approaching the
  TWFE estimate by the end. Post coefficients are not individually significant (wide CIs) —
  expected with 1 treated unit.

### Step 7 — Placebo inference (`src/workflow/06_placebo.py` → `results/workflow/07_placebo.txt`, `.csv`)
- The 1989 treatment was assigned to each of the 38 control states in turn; the same TWFE was
  re-estimated each time; California's actual estimate was ranked among all 39
  (most negative = rank 1).
- **California ranks 4th of 39** (−27.349). **Placebo p-value = 4/39 = 0.103.**
- Three placebo states are more negative: unit 22 (−61.639), unit 21 (−38.583),
  unit 24 (−35.066). Placebo distribution: min −61.6, max +27.5, mean +0.72, median +2.47.
- **This fails the plan's falsification criterion** (rank 1 → p ≈ 0.026; rank 2 → p ≈ 0.051;
  rank 4 → p ≈ 0.103 > 0.05). The estimate is not extreme relative to placebo assignments.
- Known limitation of this placebo design: California remains in the pool as a control when
  each placebo is estimated (my choice — plan.md does not specify whether California stays in
  the placebo control pool).

### Step 8 — Robustness: California-specific linear pre-trend (`src/workflow/07_robustness.py` → `results/workflow/08_robustness.txt`, `.csv`, `.png`)
- Primary method (plan.md test 4, trend fitted on the pre-period only): linear trend of the
  treated-vs-control gap fitted on 1970–1988, extrapolated through 1989–2000 as the
  counterfactual gap.
- **Pre-period gap trend: −1.232 packs per person per year per year (SE 0.106).** Sign convention: gap = California −
  control mean, so the negative slope means the gap was **widening** — California was falling
  further behind the controls during 1970–1988 (gap ≈ +3 in 1970 to −23.7 in 1988;
  gap levels from `04_raw_trends.csv`), not
  narrowing. (Correction to my step-8 report, per the human's review.)
- **Trend-adjusted effect: −8.258 packs per person per year** (per-year effects −12.69 to +0.04; mean raw post
  gap −41.708 minus mean extrapolated gap −33.450).
- Secondary estimator, labeled as DIFFERENT (trend fitted on all periods, not pre-only):
  TWFE + treated × linear time → treat_post **−5.177**.
- Comparison: unadjusted TWFE −27.349 → trend-adjusted −8.258 (change +19.091). The effect
  shrinks by ~70% but does not disappear (−8.3 ≈ 7% of California's pre-period mean of 116).

## 4. Verdict

**No clean causal claim.** By plan.md's own falsification criteria:
1. Trend adjustment (step 8): the effect shrinks from −27.3 to −8.3 (secondary variant −5.2) —
   **partially triggered**: still clearly negative, but far from the unadjusted estimate.
2. Event study (step 6): pre-period coefficients are not flat — California's gap vs controls
   was already widening before 1989 (steep in the 1970s, flat 1983–1987), but it fell by about
   3.6 packs per person per year between 1987 and 1988, before the tax. **Triggered as a
   concern.**
3. Placebo test (step 7): **fails** — rank 4/39, p = 0.103 > 0.05; three untreated states give
   more negative placebo "effects".

The unadjusted TWFE estimate is −27.349 packs per person per year, but the design checks do not support
interpreting it causally. The residual negative effect after trend adjustment (−8.3) is
consistent with some genuine effect (my inference, unverified), but the ambiguity below
prevents a firm conclusion.

## 5. Limits and things I am not sure about

- **1 treated unit**: cluster-robust SEs are not reliable; inference rests on the placebo test,
  which fails at the 0.05 level.
- **Counterfactual trend ambiguity (I am not sure):** the raw gap flattens in 1983–1988 while
  the fitted linear trend (−1.232/yr) keeps declining. If the true counterfactual was the
  flattening recent trend rather than the 1970–88 average slope, the linear extrapolation
  overstates the counterfactual decline and −8.3 over-corrects; if the trend was truly linear,
  −8.3 stands. I cannot resolve this from the data alone.
- **Fall in the gap before the tax (I am not sure):** the gap fell by about 3.6 packs per
  person per year between 1987 and 1988, before the tax took effect. This could be
  anticipation of Proposition 99 (the vote was in November 1988) (my inference, unverified),
  and it means the choice of 1988 as the event-study reference year affects the size of the
  post-1989 effects.
- **Placebo contamination**: California stays in the control pool in each placebo re-estimation
  (my choice, not specified in plan.md). A synthetic-control approach would address this
  (from memory, unverified — data/README.md cites Abadie, Diamond & Hainmueller (2010) only as
  the source of the data); not run, as it is outside the plan's tests.
- **No covariates** (per plan.md test 1 and AGENTS.md); `lnincome`, `beer`, `age15to24` have
  whole years missing (exact years in step 2) and would drop rows.
- **Mechanism check (`retprice` rising in California in 1989)** is described in plan.md's
  Theory section but not in its Test list; I did not run it. It remains unverified.
- `retprice`'s unit ("probably cents") is unverified per data/README.md — any future use of it
  inherits that caveat.
- Control group is the unweighted mean of 38 heterogeneous states; no state was down-weighted
  or matched (outside the plan's specification).
- Float32 representation artifacts in the raw file (e.g. 89.800003…) were left untouched;
  display values rounded.

## 6. Choices I made without asking

1. Placed everything in `results/workflow/` and `src/workflow/` (numbered `01`–`07` in run
   order) per the run-isolation rule; the config lives at `results/workflow/did_config.json`.
2. Filled the config roles from `data/README.md` (no `data/taxonomy.json` exists) and verified
   each against the data.
3. Reported both classical and cluster-by-state SEs in step 5, but relied on neither for
   inference (1 treated unit); the placebo test is the operative inference, as plan.md specifies.
4. In step 8, implemented "California-specific linear time trend fitted on the pre-period" as a
   two-step extrapolation of the treated-vs-control gap (primary), and additionally reported a
   TWFE + treated × linear-time variant (trend fitted on all periods) as a clearly labeled,
   secondary reference, since the plan's wording allowed either reading.
5. Did not run plan.md's `retprice` mechanism check (it is in Theory, not in the Test list).
6. Did not re-verify the background facts about Proposition 99 (dates) beyond the README; used
   the README's account as given.
7. Kept the 1,209 rows unfiltered throughout; no winsorizing, transformation, or re-weighting.
8. Kept California in the control pool of each placebo run (plan.md does not specify whether
   it should be removed from the pool).
9. Used classical (non-clustered) standard errors for the event-study confidence intervals
   (step 6); cluster SEs are unreliable with 1 treated unit and would be identical across all
   years, so they would not give meaningful year-by-year intervals.
10. Used the unweighted mean of the 38 control states as the comparison series for the
    trend extrapolation in step 8; no state was down-weighted or matched.

## 7. File index

| File | Script | Purpose |
|---|---|---|
| `results/workflow/did_config.json` | (written directly, step 1) | specification |
| `results/workflow/02_panel_checks.txt` | `src/workflow/01_panel_checks.py` | panel checks |
| `results/workflow/03_design_checks.txt` | `src/workflow/02_design_checks.py` | design checks |
| `results/workflow/04_raw_trends.png`, `.csv` | `src/workflow/03_raw_trends.py` | raw trends |
| `results/workflow/05_main_estimate.txt` | `src/workflow/04_main_estimate.py` | TWFE + 2×2 |
| `results/workflow/06_event_study.txt`, `.csv`, `.png` | `src/workflow/05_event_study.py` | event study |
| `results/workflow/07_placebo.txt`, `.csv` | `src/workflow/06_placebo.py` | placebo inference |
| `results/workflow/08_robustness.txt`, `.csv`, `.png` | `src/workflow/07_robustness.py` | pre-trend robustness |
