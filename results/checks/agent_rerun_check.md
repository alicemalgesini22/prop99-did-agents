# Check of run `agent_rerun` (self-check before write-up, checking-results skill)

Checked by: the run's own agent (GLM-5.3-Flash Free), 16 Nov 2026, at the skill's
"before writing up any number" trigger. No file of the run was changed by the check
scripts; the run's `summary.md` was corrected once during the check (event-study bug,
see "Problems found", P1) and the correction is reproduced in this report.

## 1. Rules (data/README.md "Rules" 1–7) — `src/checks/01_rules.py`

| Rule | Result |
|---|---|
| 1. 39 × 31 = 1,209 rows, no duplicate (state, year) | PASS (1,209 rows, 39 states, 31 years, 0 duplicates) |
| 2. `california` True for state 3 only, all 31 years | PASS (31 rows, all state 3) |
| 3. treatment True in exactly 12 rows (state 3, 1989–2000) | PASS |
| 4. `after_treatment` ⇔ year ≥ 1989, 468 rows | PASS |
| 5. `cigsale`, `retprice` never empty, never negative | PASS |
| 6. empty `lnincome`/`beer`/`age15to24` = missing, not zero | PASS (195 / 663 / 390 empty; exact years as in README; zero non-empty zeros) |
| 7. no row dropped; counts printed | PASS (main estimate n_rows = 1,209; 01 prints 1,209 at every stage; code read: no script subsets rows) |

**7/7 PASS.**

## 2. Recomputed headline — `src/checks/02_recompute.py`

The skill says to recompute the 2×2 "using only pandas". **Pandas is blocked on this
machine by an application-control policy** (tested with pandas 3.1.1 and 2.3.3, and
from a different directory; the run's summary, Choices 1, documents this). The
recompute uses the `csv` module + plain arithmetic instead: same independence from the
run's code (it imports nothing from `src/agent_rerun/`), one dependency less.

Four means (n = 19 / 12 / 722 / 456): 116.2105, 60.3500, 130.5695, 102.0581.
2×2 DiD = (60.3500 − 116.2105) − (102.0581 − 130.5695) = **−27.3491**.

## 3. Number-by-number comparison (SAME = equal to the rounding shown)

| summary.md number | Run value | Recomputed | Verdict |
|---|---|---|---|
| California pre mean | 116.21 | 116.2105 | SAME |
| California post mean | 60.35 | 60.3500 | SAME |
| Controls pre mean | 130.57 | 130.5695 | SAME |
| Controls post mean | 102.06 | 102.0581 | SAME |
| Main TWFE β (= 2×2) | −27.3491 | −27.3491 | SAME |
| Raw-gap slope pre-1989 | −1.2317 | −1.2317 | SAME |
| Raw-gap slope post-1988 | −2.2228 | −2.2228 | SAME |
| Event study (all 30 coefficients) | regression output | group-mean gaps − gap(1988): max deviation 2.8e-11 | SAME |
| retprice 2×2 | +25.1956 | +25.1956 | SAME |
| retprice gap 1988 / 1989 / 1990 | −0.79 / −2.32 / +22.10 | −0.7895 / −2.3237 / +22.1000 | SAME |
| California placebo estimate | −27.3491 | −27.3491 | SAME |

**13/13 SAME.** Not recomputed here (they need regression code, only group means were
recomputed): trend-adjusted β (A) −8.2577, one-step β (B) −5.1765, placebo p 0.1026
(rank 4 of 39). These match the human's independent calculations of the earlier runs
recorded in `mistakes.md` (session 3 table: −8.258, −5.177/−5.18, rank 4, p = 0.103).

## 4. Choices made by the run that are not in plan.md

All are in the run's "Choices I made without asking" (declared):

| Choice | Status |
|---|---|
| numpy implementation (pandas blocked by machine policy); validated CR1=HC1 at G=N and TWFE=2×2 | declared (choice 1) |
| unnumbered shared module `didlib.py`; every script reads `did_config.json` | declared (choice 2) |
| cluster SE reported but not used for inference; placebo rank/39 is the rule | declared (choice 3) |
| robustness implemented two ways (two-step pre-fitted; one-step CA×t) | declared (choice 4) |
| classical event-study CIs, labelled indicative; WLS pre-slope ignores covariances | declared (choice 5) |
| mechanism check on `retprice` + yearly gaps 1985–1992 | declared (choice 6) |
| self-check (this file) triggered before write-up; recompute without pandas | declared (choice 7) |
| no edits to plan.md / reports/prompts.md / mistakes.md | declared (choice 8) |
| event-study bug found and fixed during the check (P1 below) | declared (choice 9) |
| unweighted mean of the 38 control states as the comparison aggregate | declared (choice 10) |
| California kept in the 39-estimate placebo pool | **not a choice**: plan.md test 3 fixes "ranks among the 39" = 38 placebos + California |
| reference year 1988; pre-period 1970–1988; no covariates | not choices: fixed in plan.md tests 1–2 |

Nothing found that is missing from the list. (E5 check)

## 5. Claims audit (facts stated that the run did not compute and were not given)

- "Proposition 99, a 25-cent per pack tax, effective 1 January 1989" — given
  (plan.md, data/README.md). OK.
- "the vote was 8 Nov 1988, per data/README.md" — given. The added reading
  "possible anticipation" is the run's own inference and is now marked "my inference,
  unverified" in summary.md. Fixed during the check (was unmarked when first written —
  E2-type, corrected).
- "comparable in size to the 25-cent tax if the unit is cents" — the +25.20 is
  computed; the unit premise is unverified and flagged (README caveat 4). OK as stated.
- "plan.md fixes 1988 as reference / fixes the rank/39 rule / fixes the pre-period
  1970–1988" — verified against plan.md. OK.
- No sentence quotes numbers from papers or memory as if computed. (E2 check)

## 6. Problems found (tagged per mistakes.md E1–E7)

- **P1 (E6 Code bug, fixed):** the first `04_event_study.py` omitted the constant
  column; with drop-first dummies this made (control unit 1, 1988) the silent zero
  baseline and shifted every event-study coefficient by +2 × gap(1988) = +47.30
  (e.g. 1987 printed −43.668 instead of +3.637). Found by the skill's independent
  recompute path: group-mean event study vs regression output disagreed by exactly a
  constant. Fixed (constant added), rerun, and the fixed coefficients now match the
  group-mean computation to 2.8e-11 (max over all 30 years). The bug affected only the
  event-study outputs; the shape of the figure (falling, then flat 1983–87, then
  falling) was unchanged because the shift is constant, but every printed level was
  wrong. Caught before any number reached the final summary beyond the first draft of
  this run's own summary.md, which was rewritten with the corrected values.
- **P2 (E4-type, avoided, recorded for the pattern file):** the mechanism check
  reproduces the earlier runs' trap — the average post-1989 price gap (+25.2) looks
  clean, but the 1989 gap itself (−2.32) shows no relative price rise in the first
  treatment year; the run reports both plus the yearly table 1985–1992.
- No E1, E3, E5 or E7 problems found in the final summary.md: every number traces to a
  results file; "widening/narrowing" is used consistently with the gap's direction
  (gap = California − controls; falling gap value = widening shortfall); the 1988
  pre-tax 3.6-pack widening is reported (the E7 pattern of both earlier runs); the
  choice list covers every departure found by this audit.

## 7. Verdict of the check

The run's numbers are reproducible from the raw file by an independent path (13/13
SAME; rules 7/7 PASS). The one code bug (P1) was found and fixed before final
write-up. The run's verdict — "the hypothesis does not survive this run's checks; no
causal claim" — follows the plan's fixed falsification rule (placebo rank 4 of 39,
p = 0.1026 > 0.05, plus 70% of the estimate absorbed by the pre-trend adjustment).
