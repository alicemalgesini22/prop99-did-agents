# DiD run: California Proposition 99 and per-capita cigarette sales

Run folder: `results/agent_deepseek/`, code: `src/agent_deepseek/`. Agent: `did-auto` procedure,
model DeepSeek V4.1 Flash Free, 16 Nov 2026.

## 1. Question

Did California's Proposition 99 (a 25-cent per-pack cigarette tax, effective 1 January 1989)
reduce per-capita cigarette **sales** in California, compared with what would have happened
without it? (`plan.md`, Question.)

## 2. Config — `results/agent_deepseek/did_config.json`

| Field | Value | Where it comes from, and how it was checked |
|---|---|---|
| `data_path` | `data/raw/california_tobacco.csv` | named in `plan.md` and `data/README.md` |
| `unit` | `state` | `data/README.md`, "Columns" and "Panel structure"; 39 distinct IDs, `01_panel_checks.py` |
| `time` | `year` | `data/README.md`; 31 distinct years 1970–2000, `01_panel_checks.py` |
| `outcome` | `cigsale` | `plan.md` Test 1; `data/README.md` defines it as per-capita cigarette **sales**, packs/person/year, not consumption |
| `treated_units` | `[3]` | rule: rows where the boolean `california` column is True. Checked: the column flags state 3 only, in all 31 years (`01_panel_checks.py`) |
| `treatment_start` | `1989` | `plan.md`; `data/README.md` "Treatment" (tax effective 1 January 1989) |
| `controls` | `[]` (none) | all other 38 states enter as two-way fixed effects. `plan.md` says "no covariates"; `AGENTS.md` forbids adding covariates without asking, and the three covariates are missing for all 39 states in many years (`01_panel_checks.py`) |
| `cluster` | `state` | default in the procedure; reported but flagged as unreliable (1 treated unit) |
| `mechanism_outcome` | `retprice` | `plan.md` "Theory" (mechanism check); `data/README.md`, unit unverified |

**The `after_treatment` trap, checked:** `01_panel_checks.py` confirms `after_treatment` equals
`year >= 1989` for **every** row — 468 True rows, of which **456 are not California**. It is a
calendar-year dummy, so it is not used as the treatment. Treatment is
`state == 3 AND year >= 1989` = 12 rows.

## 3. Panels and design — `01_panel_checks.py` → `results/agent_deepseek/panel_checks.json`

| Check | Result |
|---|---|
| Rows read | **1,209** |
| Units / periods | **39** states (1–39), **31** years (1970–2000) |
| Duplicate `(state, year)` pairs | **0** |
| Balance | **balanced**: every state has 31 rows |
| Rows after filters in the main specification | **1,209** — no filter, no drop |
| `cigsale` missing | **0** rows |
| `lnincome` missing | 195 rows, years **1970, 1971, 1998, 1999, 2000**, for all 39 states |
| `beer` missing | 663 rows, years **1970–1983 and 1998–2000**, for all 39 states |
| `age15to24` missing | 390 rows, years **1991–2000**, for all 39 states |
| Treated units | **1** (state 3) |
| Treatment timing | **not staggered**: one treated unit, one start date (1989) → plain TWFE is not exposed to negative-weighting/staggered-timing bias |
| Treated rows | 12 (state 3, 1989–2000); pre period 741 rows (19 years), post 468 rows (12 years) |
| Few-treated warning | **yes** — 1 treated unit, so cluster-robust SEs are not reliable; inference uses the placebo test |

`08_selfcheck.py` re-tests all seven rules in the "Rules" section of `data/README.md` in pure
Python: **7 of 7 PASS** (`results/agent_deepseek/08_selfcheck.json`).

## 4. Raw trends — `02_raw_trends.py` → `02_raw_trends.png`, `02_raw_trends.json`

Mean `cigsale` for the treated unit and for the mean of the 38 controls, line at 1989. The
treated-minus-control gap: **+2.92** in 1970, **−20.09** in 1987, **−23.72** in 1988,
**−50.53** in 2000. The pre-1989 linear slope of the gap is **−1.2317 packs/year**: the gap was
already widening long before the tax. The gap also falls **3.63 packs in 1988 alone**, the year
before the tax took effect (1987 −20.09 → 1988 −23.72) — this matters for the event study, whose
reference year is 1988.

## 5. Main estimate — `03_main_did.py` → `03_main_did.json`, `03_main_did_specs.csv`

`cigsale ~ treated + state FE + year FE`, all 1,209 rows.

| Specification | Treated coefficient | SE (classic) | SE (clustered by state, unreliable) |
|---|---|---|---|
| Pooled, no FE | −59.1301 | 9.3568 | 4.2357 |
| State FE only | −55.8605 | 7.2195 | **0.0000 (degenerate)** |
| Year FE only | −41.7081 | 8.3941 | 3.7390 |
| **State + year FE (main)** | **−27.3491** | **4.4095** | **2.8487** (G = 39, t = −9.60, p < 0.001) |

Main estimate: **−27.35 packs per person per year** (n = 1,209, k = 70, R² = 0.8776).

**Cross-check 1 (2×2 difference of means, same script):** treated unit 116.211 → 60.350
(change −55.861); controls 130.570 → 102.058 (change −28.511);
2×2 DiD = **−27.3491**, identical to the TWFE coefficient to 4 decimal places.

**Cross-check 2 (pure Python, no numpy, no regression code — `08_selfcheck.py`):** the same four
means and DiD = **−27.349111**, differing from `03_main_did.json` by −1.4×10⁻¹⁴
(`08_selfcheck.json`). The 2×2 and the TWFE coincide exactly; that is the expected identity for a
balanced panel with one treated unit and one start date, so the agreement checks the arithmetic,
not the design.

**Cross-check 3:** two-way within transformation (FWL) in `03_main_did.py` gives −27.3491110819,
differing from the dummy-variable estimate by −2.9×10⁻¹².

**Why the clustered SEs cannot be used:** with one treated unit the cluster-robust variance for
that coefficient collapses (state-FE-only row above gives a clustered SE of exactly 0.0000, i.e. a
t-statistic of 1.7×10¹⁴). The clustered SE of 2.85 in the main row must not be read as a
confidence statement.

## 6. Event study — `04_event_study.py` → `04_event_study.png`, `04_event_study.csv`

One coefficient per year, `state 3 × year` dummies, 1988 (= last pre-treatment year) as reference,
with state and year FE; 30 coefficients, n = 1,209, R² = 0.8790.

Selected coefficients (packs per person per year, relative to 1988):

| Year | 1970 | 1975 | 1980 | 1983 | 1987 | 1989 | 1990 | 1991 | 1995 | 2000 |
|---|---|---|---|---|---|---|---|---|---|---|
| Coef. | +26.64 | +13.89 | +5.83 | +3.27 | +3.64 | −3.54 | −4.14 | −11.92 | −23.03 | −26.81 |

**Pre-treatment coefficients are falling, not flat.** From 1970 (+26.64) they decline almost
monotonically to 1988 (0), a linear slope of **−1.2654 packs/year**. The decline decelerates in
the 1980s: 1983–1987 sit between +2.83 and +3.64, i.e. nearly flat against 1988.
Post-treatment, the path falls to −26.81 by 2000 (mean of the 12 post coefficients −17.98), with a
noticeable extra step down in **1991** (−4.14 → −11.92). Because 1988 is itself an unusually low
year (the gap fell 3.63 packs in 1988, §4), the 1989–1990 coefficients of −3.5 and −4.1 are
measured against a reference that is already abnormal.

## 7. Inference: placebo — `05_placebo.py` → `05_placebo.json`, `05_placebo.png`, `05_placebo.csv`

Treatment assigned in 1989 to each unit in turn, same TWFE re-estimated.

| Variant | Treated unit | Rank (1 = most negative) | Placebo p-value |
|---|---|---|---|
| A: treated unit kept in the pool (39 units, plan.md's wording) | −27.349 | **4 of 39** | **4/39 = 0.1026** |
| B: treated unit dropped from the pool for the 38 placebo runs | −27.349 | **4 of 39** | **4/39 = 0.1026** |

Placebo estimates: mean ≈ 0.00 (variant A), sd 17.85, min −61.64 (unit 22), max +27.47 (unit 32).
Three control states have **more negative** estimates than California: unit 22 (−61.64),
unit 21 (−38.58), unit 24 (−35.07). California is not the most negative.

## 8. Robustness: unit-specific pre-trend — `06_robustness.py` → `06_robustness.json`

Pre-1989 linear slopes: treated unit **−1.7795**/yr, control mean **−0.5478**/yr, gap **−1.2317**/yr.

| Specification | Estimate | Change from main |
|---|---|---|
| Main TWFE | −27.3491 | — |
| Ro1: TWFE + treated-unit-specific linear trend (whole window; trend coef −1.4305/yr) | **−5.1765** (classic SE 8.1904) | +22.17 (−81.1%) |
| Ro2: 2×2 on treated series detrended by its own pre-period slope (−1.7795/yr) | **+0.2327** | +27.58 (−100.9%) |
| Ro3: 2×2 on treated series detrended by the pre-period **gap** slope (−1.2317/yr) | **−8.2577** | +19.09 (−69.8%) |

Ro2 also removes the common national decline (controls fall 0.55/yr), so it over-corrects; Ro3 is
the fair analogue of a DiD pre-trend correction and still cuts the estimate by about 70%.

Window checks (same TWFE, rows dropped as labelled):

| Window | Treated coefficient | Rows | Pre-1989 gap slope inside the window |
|---|---|---|---|
| 1970–2000 | −27.349 | 1,209 | −1.232 |
| 1975–2000 | −23.702 | 1,014 | −0.839 |
| 1980–2000 | −21.292 | 819 | −0.422 |
| 1981–2000 | −20.976 | 780 | −0.332 |
| 1984–2000 | −20.683 | 663 | −0.701 |
| 1986–2000 | −20.140 | 585 | −1.414 |

The estimate is moderately stable at about −20 to −21 once the 1970s are dropped, i.e. when the
steep early part of the pre-trend is excluded. It is not stable across the pre-trend corrections
above, which give +0.2 to −8.3.

## 9. Mechanism — `07_mechanism_price.py` → `07_mechanism_price.png`, `07_mechanism_price.json`

Same TWFE design with `retprice` as the outcome: **+25.196** (classic SE 2.907, clustered 1.992).
The price gap (treated minus control mean) is flat before 1989 (slope −0.05/yr) and **does not
rise in 1989 itself** (−2.32 in 1989, versus −0.79 in 1988); it jumps in **1990 (+22.1)** and
**1991 (+37.2)**, then sits between **+14.8 and +37.2** from 1991 to 1999 and jumps to **+69.7** in
2000. The 2000 values are far out of line with 1999 in both series. The unit of `retprice` is unverified (`data/README.md`, caveat 4), so the
magnitude of 25.2 cannot be compared with the 25-cent tax; only the direction and timing can.

## 10. Verdict

**No causal claim.** The design does not support one, by the rule fixed in `plan.md`
("What would prove me wrong"). Two of the three disproof conditions are met:

1. **Pre-trend.** The event study (§6) shows the gap was already widening at about
   −1.27 packs/year before 1989 over the full pre-period, and accounting for the treated unit's
   own pre-trend removes 70–100% of the estimate (§8: −27.35 → −8.26 → +0.23 → −5.18).
2. **Placebo.** California ranks **4th of 39** with p = 0.103, not 1st of 39 (p = 0.026) as
   `plan.md` requires for a claim: three control states show larger declines.

The plain estimate is large and negative (−27.35 packs per person per year, §5) and the price
mechanism points the predicted way (§9), but the DiD cannot separate Proposition 99's effect from
California's own pre-existing downward trend, nor show that California's fall was unusual among
the 39 states. What the data support: California's per-capita cigarette sales fell much faster
than the control states' after 1989, the fall began from an already-steep pre-existing decline
that flattened in the 1980s, and part of the fall (roughly 20 packs, §8 window checks) survives
dropping the 1970s. Whether that residual is caused by Proposition 99 is **not identified here**.

## 11. Limits, and where I am not sure

- **One treated unit.** No credible standard errors; the clustered SE of 2.85 (§5) and the
  event-study error bars are shown for completeness only. All inference rests on one placebo
  distribution of 39 numbers.
- **I am not sure** how much weight the "flat 1983–1988" segment (§6) should get against the
  longer, steeper 1970–1982 decline. An honest reading is that the answer depends on the pre-period
  window: the estimate is −27 (1970 base), ≈ −21 (1980 base) and ≈ −8 or less once a linear
  pre-trend is extrapolated. I did not choose one window in advance; `plan.md` fixes 1970–1988,
  which is what the main estimate uses.
- **The 1988 reference year is unusual** (gap drops 3.63 packs in 1988, before the tax). I did not
  re-run the event study with another reference year; that would change the visual shape, not the
  pre-trend slope.
- **No covariates** (§2), so the comparison is between California and all 38 other states
  regardless of how similar they are; with one treated unit, a synthetic-control-type weighting
  (not in `plan.md`) could plausibly change the picture.
- **2020 data anomaly**: `retprice` jumps +69.7 in 2000 relative to controls (§9). I did not
  investigate it; it does not affect `cigsale`.
- **`cigsale` is sales, not consumption** — cross-border buying would move sales without moving
  consumption, so even a genuine effect on sales need not be an effect on consumption
  (`data/README.md`, caveat 1).
- **Environment:** `import pandas` fails on this machine (Windows application control blocks
  `pandas/_libs/window/indexers*.pyd`), and `statsmodels` fails because it imports pandas. I wrote
  OLS, the cluster-robust sandwich and the data reader by hand in numpy/scipy/csv
  (`src/agent_deepseek/did_common.py`). I checked the estimator against a two-way within
  transformation and against an independent pure-Python 2×2 (§5), but it is not the library the
  project normally uses, so a human should confirm against pandas/statsmodels elsewhere.

## 12. Files produced (this run only)

| File | Made by |
|---|---|
| `did_config.json` | written by hand from `plan.md`, `data/README.md`, checked by `01_panel_checks.py` |
| `panel_checks.json` | `01_panel_checks.py` |
| `02_raw_trends.png`, `02_raw_trends.json` | `02_raw_trends.py` |
| `03_main_did.json`, `03_main_did_specs.csv` | `03_main_did.py` |
| `04_event_study.png`, `04_event_study.csv`, `04_event_study.json` | `04_event_study.py` |
| `05_placebo.png`, `05_placebo.json`, `05_placebo_variantA.csv`, `05_placebo_variantB.csv` | `05_placebo.py` |
| `06_robustness.json` | `06_robustness.py` |
| `07_mechanism_price.png`, `07_mechanism_price.json` | `07_mechanism_price.py` |
| `08_selfcheck.json` | `08_selfcheck.py` |
| `summary.md` | this file |

Shared helper (not a numbered script): `src/agent_deepseek/did_common.py`. Every script reads
`results/agent_deepseek/did_config.json`; no column name is hard-coded.

## 13. Choices I made without asking

1. **Data reader and estimator written by hand** (no pandas, no statsmodels) because pandas is
   blocked by application control on this machine. Validated against a within transformation and a
   pure-Python 2×2.
2. **State 3 identified via the `california` boolean column** rather than typed in; the config
   records the rule and the check.
3. **No covariates** — followed `plan.md` and `AGENTS.md`; did not use `lnincome`, `beer`,
   `age15to24` because they would drop rows (195/663/390 rows missing).
4. **Placebo variant A keeps the treated unit in the control pool** (plan.md's wording), and I
   added **variant B** dropping it; both give rank 4 of 39.
5. **Reference year 1988** for the event study (last pre-treatment year, `plan.md` Test 2).
6. **Three pre-trend correction methods** (Ro1, Ro2, Ro3) rather than one; Ro2 and Ro3 differ in
   whether the common decline is removed, which changes the number a lot, so I report both.
7. **Window checks (Ro4) added** beyond `plan.md`, because the pre-trend clearly bends in the
   early 1980s and the choice of base year changes the estimate.
8. **Mechanism regression on `retprice` added** (plan.md states the mechanism but does not list it
   as a test); reported as directional only because the unit is unverified.
9. **Placebo p-value defined as rank/39**, exactly as `plan.md` states; no SE-based p-value is
   used for inference.
10. **A self-check script (`08_selfcheck.py`)** re-testing the seven `data/README.md` rules and
    recomputing the headline number in pure Python. I did not use the `.opencode` skill
    `checking-results`, because it is written to check *another* run and to write into
    `results/checks/` and `src/checks/`, which belong to a different run.
11. **No claim about Abadie et al. or any published estimate** was used; all numbers here are
    computed from `data/raw/california_tobacco.csv` in this run.
