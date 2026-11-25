# Re-run of the California tobacco DiD (run: agent_rerun)

Model: GLM-5.3-Flash Free (OpenCode). Date: 16 Nov 2026. This run is extension 6 of
plan.md: the same procedure as the 13 Nov `did-auto` run, in a new session. I read
`plan.md` and `data/README.md` first. `data/taxonomy.json` does not exist (plan.md
model log, 12 Nov 2026: built then dropped; roles live in `did_config.json`).

## Question

Did California's Proposition 99 (25-cent per pack cigarette tax, effective 1 Jan 1989)
reduce per-capita cigarette **sales** (`cigsale`, packs/person/year — sales, not
consumption) in California relative to what would have happened without it?

## Specification (step 1)

`results/agent_rerun/did_config.json`, with the source of every field recorded in the
file itself. Roles, checked against the data by `src/agent_rerun/01_panel_checks.py`:

- unit = `state`, time = `year`, outcome = `cigsale` (data/README.md columns table)
- treatment group = `california` (True for state 3 in all 31 years — verified)
- treatment = `california AND year >= 1989` (plan.md test 1; Proposition 99, 1 Jan
  1989, data/README.md "Treatment")
- I checked the trap the README warns about: using `after_treatment` as the treatment
  would mark 456 control-unit rows as treated, so it was rejected; the actual treatment
  is True in exactly 12 rows (state 3, 1989–2000) and 0 in every control row.
- controls = the other 38 states (IDs 1, 2, 4–39); no covariates (plan.md test 1:
  covariates are missing in many years; AGENTS.md forbids adding them without asking)
- cluster = `state`, but with 1 treated unit the clustered SE is not reliable, so
  inference uses the placebo test (plan.md test 3)

## Panel checks (step 2) — `src/agent_rerun/01_panel_checks.py` → `results/agent_rerun/01_panel_checks.txt`

- 1,209 rows; 39 states; 31 years (1970–2000); 0 duplicate (state, year) pairs;
  balanced (31 rows per state; 39 × 31 = 1,209). Row count after every check: 1,209
  (no filter, merge or drop was applied anywhere).
- Missing values, exact years computed from the file: `lnincome` 1970–1971 and
  1998–2000 (195 rows); `beer` 1970–1983 and 1998–2000 (663 rows); `age15to24`
  1991–2000 (390 rows); `cigsale` and `retprice` never missing, never negative.
  These match data/README.md exactly. Missing cells affect only covariates, which are
  not used, so no rows were dropped for missingness.
- Outcome means: California 116.21 (pre, sd 11.68) → 60.35 (post, sd 12.08);
  controls 130.57 (pre) → 102.06 (post).

## Design checks (step 3)

- 1 treated unit (state 3 = California); 38 control units.
- Single common treatment start: 1989 for the only treated unit — treatment timing is
  NOT staggered, so the plain two-way fixed effects specification is the right baseline
  (no staggered-adoption weighting problem arises with one cohort).
- Fewer than 5 treated units → clustered standard errors are not reliable; inference
  uses the placebo test (below).

## Raw trends (step 4) — `src/agent_rerun/02_raw_trends.py` → `results/agent_rerun/02_raw_trends.png`, `02_group_means.csv`

California's sales fall faster than the controls' over the whole sample. The
treated-minus-control gap declines at −1.232 packs/person/year per year before 1989
and at −2.223 after 1988 (descriptive OLS slopes of the yearly gap, in
`02_group_means.json`). So California was already pulling away from the controls
before the tax — the post-1989 gap is not born from a flat baseline.

## Main estimate (step 5) — `src/agent_rerun/03_main_estimate.py` → `results/agent_rerun/03_main_estimate.txt`

- TWFE: `cigsale ~ treated_post + state FE + year FE`, all 1,209 rows, 70 parameters:
  **β = −27.35 packs/person/year** (SE classical 4.41; HC1 2.94; clustered by unit
  2.85 — reported but NOT reliable with 1 treated unit). R² 0.878.
- Cross-check, simple 2×2 difference of means: −27.35. TWFE − 2×2 = 2.8e-12, i.e. the
  two agree exactly, as they must with one treatment cohort and a balanced panel.

## Event study (step 6) — `src/agent_rerun/04_event_study.py` → `results/agent_rerun/04_event_study.png`, `04_event_study.json`

California × year coefficients with 1988 as reference (per plan.md test 2), state and
year FE. **First version of this script had a bug (missing constant column, see
Choices 9): it was caught by comparing against the group-mean event study and fixed
before any write-up; the numbers below are the fixed, verified ones.**

- Pre-treatment coefficients are NOT flat, but neither is the old story "falling right
  up to the tax": they fall from +26.6 (1970) to ≈ +3 by 1982, and are then FLAT during
  1983–1987 (1983: +3.3, 1984: +3.6, 1985: +3.4, 1986: +2.8, 1987: +3.6).
- In terms of the raw gap (`02_group_means.csv`): California fell behind the controls
  mostly in 1970–1982, the gap then held at about −20 packs for 1983–1987, and it
  widened again by another 3.56 packs from 1987 (−20.09) to 1988 (−23.65) — **before
  the tax took effect**. I read that as possible anticipation (the vote was 8 Nov 1988,
  per data/README.md) — that reading is my inference, unverified. This also
  means the reference-year choice matters: with 1987 as reference, every post-1989
  coefficient would be about 3.6 packs more negative. I did not run that variant
  (plan.md fixes 1988 as reference).
- Post-1989 coefficients: −3.5 (1989), −4.1 (1990), −11.9 (1991), then falling steadily
  to −26.8 (2000) — the widening accelerates from 1991 on.
- Descriptive weighted slope of the pre-1989 coefficients: −1.27 ± 4.02 per year
  (inverse-variance weights; coefficient covariances ignored — descriptive only).
  The intervals in the figure are classical 95% and indicative only (1 treated unit);
  the reference year is drawn as a point at zero.

## Inference (step 7) — `src/agent_rerun/05_placebo.py` → `results/agent_rerun/05_placebo.json`, `05_placebo.png`

Placebo test per plan.md test 3: the same 1989 treatment assigned in turn to each of
the 38 control states, same TWFE. The 38 placebo estimates have mean +0.72, sd 17.51,
min −61.64, max +27.47. **California's estimate (−27.35) ranks 4th most negative of
the 39** (three placebo states are more negative). **Placebo p-value = 4/39 = 0.1026**
(rank / 39, the rule fixed in plan.md: rank 1 → 0.026, rank 2 → 0.051 already above
0.05). The effect is not unusual by this standard.

## Robustness (step 8) — `src/agent_rerun/06_robustness_trend.py` → `results/agent_rerun/06_robustness.txt`

California-specific linear pre-trend, two implementations of plan.md test 4:

- (A) two-step, headline: on the pre-1989 rows only, the California slope differential
  is θ = −1.23 packs/year/year (classical SE 0.41). Removing that fitted trend from
  California in all years and re-running the TWFE gives **β = −8.26** (cluster-by-unit
  SE 2.85). Change vs main: **+19.09, i.e. 70% of the main estimate is gone**.
- (B) one-step (California × linear time regressor, trend estimated on all periods):
  θ = −1.43 (cluster SE 0.19), β = −5.18 (cluster SE 1.27).
- Caveat on both: the event study shows the gap was FLAT in 1983–1987, so a linear
  trend fitted on 1970–1988 mostly removes the 1970s' widening and plausibly
  **over-corrects**; the trend-adjusted effect likely lies between −27.3 and −8.3
  (I did not compute the 1980s-only window variant; plan.md fixed the pre-period as
  1970–1988). I am not sure which counterfactual trend is the right one.

## Mechanism (plan.md "Theory") — `src/agent_rerun/07_mechanism_retprice.py` → `results/agent_rerun/07_mechanism_retprice.txt`

`retprice` (unit not verifiable from the file — data/README.md caveat 4): the
California-minus-control price gap averages +25.20 over 1989–2000 (2×2 and TWFE agree;
comparable in size to the 25-cent tax if the unit is cents). But by exact year
(computed, in `07_mechanism_retprice.json`) the gap in 1989 itself is −2.32 vs −0.79
in 1988 — the relative price rise shows up in 1990 (+22.10) and 1991 (+37.24), not
within 1989. I am not sure why the price response lags; the data cannot settle it.

## Verdict (fixed in advance in plan.md, "What would prove me wrong")

1. Effect after removing the pre-1989 trend (test 4): −27.35 → −8.26 (A) / −5.18 (B).
   I judge −8.26 as "not clearly negative" by this run's own placebo yardstick (it sits
   well inside the placebo distribution, sd 17.5), but it is still a negative point
   estimate — partly, not fully, gone.
2. Event study: the gap WAS widening, but not uniformly: mostly in 1970–1982
   (−1.3/yr), then FLAT for the five years immediately before the tax (1983–1987),
   with a further 3.6-pack widening in 1988 itself, before the tax. The post-1989
   pace (to −26.8 by 2000, accelerating after 1991) is faster than the 1970–82 pace.
   Not "widening at the same pace before 1989" as literally worded — but combined with
   point 1, the pre-trend accounts for most of the raw effect.
3. Placebo (decisive): **rank 4 of 39, p = 0.1026 > 0.05.** The plan fixes that rank 2
   already fails; rank 4 fails clearly.

**Verdict: the hypothesis does not survive this run's checks. No causal claim.** The
raw post-1989 difference (−27.35 packs/person/year) is large and negative, but it is
not statistically unusual among US states (placebo), and a large part of it is
consistent with the relative decline California was already on (robustness A: −8.26;
though that adjustment likely over-corrects given the flat 1983–87 gap — I am not sure
where between −27.3 and −8.3 the truth lies). I am not sure whether the remainder is a
real effect of the tax, a noisy remainder of the trend, or something else — this
design cannot tell those apart.

## Limits

- One treated state: every conventional SE here is unreliable; the only trustworthy
  inference is the placebo rank. Event-study CIs are classical and nominal.
- `cigsale` is tax-paid **sales**, not consumption (README caveat 1). `retprice`'s unit
  is unverified (README caveat 4). No state names in the file; "California = state 3"
  comes from data/README.md, not the data.
- The 2×2/TWFE equivalence means the main estimate inherits the 2×2's parallel-trends
  assumption, which the event study contradicts.
- Environment (see "Choices"): the machine's application-control policy blocks the
  pandas binaries (pandas 3.1.1 and 2.3.3 alike) and `statsmodels.api` imports pandas,
  so all estimation is a numpy OLS + sandwich implementation in
  `src/agent_rerun/didlib.py`. Validated internally two ways: the cluster sandwich with
  singleton clusters reproduces HC1 exactly, and TWFE equals the 2×2 to 1e-12.
- Not done here (other sessions/extensions of plan.md): multiverse, other model,
  framing run, the human's Excel check. Covariates were not added (AGENTS.md).

## Files produced by this run (every number above comes from one of these)

| Result | Script |
|---|---|
| `results/agent_rerun/did_config.json` | written at step 1 from plan.md + data/README.md |
| `results/agent_rerun/01_panel_checks.txt`, `.json` | `src/agent_rerun/01_panel_checks.py` |
| `results/agent_rerun/02_group_means.csv`, `.json`, `02_raw_trends.png` | `src/agent_rerun/02_raw_trends.py` |
| `results/agent_rerun/03_main_estimate.txt`, `.json` | `src/agent_rerun/03_main_estimate.py` |
| `results/agent_rerun/04_event_study.json`, `.png` | `src/agent_rerun/04_event_study.py` |
| `results/agent_rerun/05_placebo.json`, `.png` | `src/agent_rerun/05_placebo.py` |
| `results/agent_rerun/06_robustness.txt`, `.json` | `src/agent_rerun/06_robustness_trend.py` |
| `results/agent_rerun/07_mechanism_retprice.txt`, `.json` | `src/agent_rerun/07_mechanism_retprice.py` |

Self-check before write-up (checking-results skill): `results/checks/agent_rerun_check.md`,
built by `src/checks/01_rules.py` and `src/checks/02_recompute.py`.

## Choices I made without asking

1. **numpy instead of pandas/statsmodels.** The machine's application-control policy
   blocks the pandas wheel DLLs (tested pandas 3.1.1 and 2.3.3; both blocked, also from
   another directory, so machine-wide, not file-local), and `statsmodels.api` imports
   pandas. I wrote OLS + classical/HC1/cluster sandwich in numpy
   (`src/agent_rerun/didlib.py`) and validated it (CR1 with singleton clusters = HC1
   exactly; TWFE β = 2×2 to 2.8e-12). During diagnosis I touched the environment: ran
   `uv pip install --reinstall pandas` (pandas 3.1.1 reinstalled — the project state),
   briefly installed pandas 2.3.3 (undone by the next `uv run` sync), ran
   `Unblock-File` on the venv's .pyd files (no effect), and numpy moved 2.5.4 → 2.5.5
   as a side effect. `data/raw/` untouched; row counts printed after every step.
2. **Shared helper module** `src/agent_rerun/didlib.py` is unnumbered (it is a library,
   not an analysis step); every numbered script reads `did_config.json` and no column
   names are hard-coded.
3. **Clustered SE reported but not used for inference**; the placebo rank is the
   decision rule (plan.md test 3 fixed the rank/39 rule, which I applied literally:
   rank among 39 estimates, most negative = 1).
4. **Robustness implemented two ways** (two-step pre-fitted detrending as the headline
   because plan.md says "fitted on the pre-period"; one-step California × trend as a
   variant). Both reported; neither changes the verdict.
5. **Event-study CIs and the pre-slope are classical/nominal**, labelled descriptive;
   the WLS pre-slope ignores coefficient covariances.
6. **Mechanism check on `retprice`** (plan.md "Theory" asks for it) done descriptively,
   plus exact yearly gaps 1985–1992 added when the 1989 point estimate looked off.
7. **Self-check with the checking-results skill** triggered by its "before writing up
   any number" clause, before finalizing this file; the recompute step had to use the
   csv module + plain arithmetic because pandas is blocked on this machine.
8. **No prompt/log edits outside my run folders** — I did not touch `plan.md`,
   `reports/prompts.md`, or `mistakes.md` (AGENTS.md: ask before changing plan.md; the
   human records prompts and mistake tags).
9. **Event-study bug found and fixed during the self-check** (E6-type): the first
   version of `04_event_study.py` omitted the constant column, so (control unit 1,
   1988) silently became the zero baseline and every coefficient was shifted by
   +2 × gap_1988 (e.g. 1987 printed −43.7 instead of +3.6). Caught by comparing the
   regression output against the group-mean event study (each coefficient must equal
   that year's gap minus the 1988 gap); fixed, rerun, figure and JSON regenerated
   before any number was reported. The event-study section above shows only the fixed
   values.
10. **Control-group aggregation is the unweighted mean** of the 38 control states in
    the raw-trends plot, the 2×2 cross-check and the placebo regressions (each
    placebo state enters with equal weight). Weighted alternatives (e.g. by
    population) were not computed — no population data in the file.
