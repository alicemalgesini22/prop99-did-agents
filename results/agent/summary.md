# DiD summary — California Proposition 99 and per-capita cigarette sales

Run: 13 Nov 2026, agent GLM-5.3-Flash Free (OpenCode), following `plan.md`.
All numbers below come from files in `results/agent/`, produced by scripts in
`src/agent/` (numbers in parentheses = producing script and output file).

## Question

Did California's Proposition 99 (25-cent/pack cigarette tax, effective 1 Jan 1989)
reduce per-capita cigarette **sales** (`cigsale`, packs/person/year) in California
relative to what would have happened without it, compared with 38 control states?
(Data: `data/raw/california_tobacco.csv`, 1,209 rows, 39 states x 31 years, 1970–2000.)

## Config (`did_config.json`, written by hand from `data/README.md` + `plan.md`)

- `data_path`: data/raw/california_tobacco.csv
- unit: `state`; time: `year`; outcome: `cigsale`
- treated unit: state 3 (California, the only unit with `california == True`)
- treatment rule: `(state == 3) & (year >= 1989)` — **not** `after_treatment`
- treatment start: 1989; event-study reference: 1988; cluster: `state`
- covariates: none (`plan.md` test 1; AGENTS.md forbids adding them without asking)

## 1. Panel checks (01_checks.py → panel_checks.txt)

- 1,209 rows after load; **no rows dropped at any point** (no filter needed).
- 39 units x 31 years, **balanced** (39/39 units have all 31 periods), **0 duplicate**
  (state, year) pairs.
- Missing values, exact years (rows are missing for all 39 states in those years):
  `lnincome`: 1970, 1971, 1998–2000 (195 rows); `beer`: 1970–1983 and 1998–2000
  (663 rows); `age15to24`: 1991–2000 (390 rows). **`cigsale` and `retprice` have no
  missing values**, so the analysis loses nothing by using no covariates.
- Design check: `california == True` marks exactly state 3 (31 rows).
  `after_treatment` is 1 in 468 rows = 39 units x 12 years and is constant within
  each year — it is a **year dummy, not the treatment**; 456 of its rows are
  control units. The constructed treatment has exactly 12 treated state-year rows
  (state 3, 1989–2000) and is 0 for all 19 California pre-1989 rows.
- Design: **1 treated unit**; treatment timing is common (1989), so the design is
  not staggered; with fewer than 5 treated units, clustered standard errors are
  not reliable and inference uses the placebo test (below).

## 2. Raw trends (02_trends.py → raw_trends.png, raw_trends.csv)

California's sales fall faster than the control mean after 1989, but the
California-minus-control gap was **already negative and falling before 1989**
(gap 1970 +2.9 packs, 1988 −23.7 packs). Not a clean common trend.

**Mechanism check** (`mechanism_retprice.csv`): the `retprice` gap
(California − control mean) jumps after the tax: −0.79 in 1988 → +22.2 in 1990,
mean +2.16 (1980–1988) vs +27.33 (1989–2000). Consistent with the price mechanism
(verify: `retprice` units are "probably cents", unverified per data/README.md).

## 3. Main estimate (03_did_eventstudy.py → main_did.txt)

TWFE `cigsale ~ treat_ + C(state) + C(year)`, N = 1,209, R² = 0.8776:

- **treat_ coefficient = −27.35 packs/person/year** (conventional SE 4.41,
  95% CI [−36.00, −18.70]; SE clustered by state 2.85 — unreliable with 1 treated
  unit, reported for reference only).
- 2×2 cross-check: California 116.21 (pre) → 60.35 (post); control mean 130.57 →
  102.06; **2×2 DiD = −27.35** — identical to the TWFE estimate (balanced panel).

## 4. Event study (03_did_eventstudy.py → event_study.csv, event_study.png)

1988 reference, HC1 SEs. **Pre-treatment coefficients are NOT flat.** Relative to
1988, the gap falls steadily from +26.6 (1970) to ≈ +3 by 1984–1987; OLS slope of
the 18 pre-period coefficients on relative year = **−1.27 packs/yr**, i.e. the
California-vs-control gap was already widening before the tax. However, the last
5 pre-treatment coefficients (1984–1988) are roughly flat (+3.6, +3.4, +2.8, +3.6,
reference 1988). Post-period coefficients fall progressively: −3.5 (1989) →
−26.8 (2000).

## 5. Inference: in-space placebo test (04_placebo.py → placebo_test.txt,
placebo_estimates.csv, placebo_hist.png)

Placebo treatment `(state == s) & (year >= 1989)` for each of the 38 control
states, same TWFE. California's real estimate −27.35 ranks **4th of 39** (most
negative = 1st); three placebo states give larger negative estimates (−61.6,
−38.6, −35.1). **Placebo p-value = 4/39 = 0.103 — not below 0.05.**

## 6. Robustness: California-specific linear pre-trend (05_robustness.py →
robustness_trend.txt)

- (a) TWFE + treated-unit trend `(state==3)*(year−1970)` (slope fitted on all
  years, post jump absorbed by the dummy): slope −1.43 packs/yr, **average
  post-period effect −5.18** (change vs baseline +22.17). Caveat: this slope
  pools the pre-trend with any trend in the post-period effect itself.
- (b) Pre-period-only extrapolation (plan.md test 4): pre-period gap trend
  (1970–1988) = −1.23 packs/yr; trend correction −19.09; **trend-adjusted 2×2
  effect = −8.26** (vs −27.35 unadjusted).
- The pre-trend is **not linear**: last-5-years (1984–1988) slope −0.70 packs/yr
  vs −1.23 over the full pre-period, so a linear adjustment is itself an
  approximation ("I am not sure" which correction is the right one).

## Conclusion

I make **no firm causal claim**. The unadjusted DiD is a large, precisely
estimated −27.35 packs/person/year, and the price mechanism moves as the plan
predicts. But the falsification checks in `plan.md` ("What would prove me
wrong") partly trigger:

1. The event-study pre-period is not flat (slope −1.27 packs/yr over 1970–1987,
   though roughly flat over 1984–1988), and accounting for a linear pre-trend
   shrinks the estimate to about **−5 to −8 packs** — roughly 70–80% of the raw
   effect is attributable to the pre-existing downward gap trend. The remaining
   effect is still clearly negative, but the trend adjustment is sensitive to
   the assumed trend shape.
2. California's estimate is **not** the most negative of the 39 (rank 4/39,
   placebo p = 0.103 > 0.05), so the rank test does not reject at 5%.

Descriptive statement I am confident in: California's per-capita cigarette sales
fell about 27 packs/person/year more than the control states after 1989, and
California's retail price rose sharply relative to control states at the same
time. Whether the extra decline beyond the pre-existing trend (about 5–8 packs,
my trend-adjusted estimates) is a causal effect of Proposition 99 is
**uncertain** under this design (1 treated unit, non-flat pre-trends).

## Limits

- 1 treated unit: no reliable SE; inference rests on the placebo rank test,
  which has only 39 support points.
- `cigsale` is sales, not consumption (per data/README.md).
- `retprice` units unverified; the price gap uses the unweighted control mean.
- No covariates (per plan.md); state IDs have no names in the file.
- Linear pre-trend adjustment is an approximation; the pre-trend flattens in
  1984–1988, which would imply a larger trend-adjusted effect than (b).
- The pre-period slope correction extrapolates a fit from 1970–1988 over
  1989–2000; any non-linearity in the counterfactual is untestable here.
- Numbers in summary table files are rounded for display only (float32
  artifacts in the raw file, per data/README.md caveat 7).

## Choices I made without asking

1. No `data/taxonomy.json` exists; roles (unit, time, outcome, treated unit,
   treatment start) were taken from `data/README.md` and `plan.md`, and each was
   checked against the data in 01_checks.py.
2. Placed `did_config.json` and all outputs of this run in `results/agent/`
   (scripts in `src/agent/`) so as not to overwrite other runs.
3. Kept `plan.md`'s no-covariates choice (AGENTS.md forbids adding covariates
   without asking; they would also drop rows because of missing years).
4. Did **not** use `after_treatment` as the treatment; verified numerically that
   it is a year dummy and constructed `treat_ = (state==3) & (year>=1989)`.
5. Reported both conventional (iid) and state-clustered SEs for the main
   estimate, flagging the clustered ones as unreliable (1 treated unit); used
   HC1 SEs for event-study confidence intervals.
6. Implemented robustness (a) as a regression with the treated-unit trend
   interacted with the treated unit over all years AND (b) the pre-period-only
   extrapolation that plan.md test 4 literally asks for; report both because (a)
   pools the post-period effect trend into the slope. My first version of (a)
   interacted the trend with the *post dummy* instead of the *unit* — that made
   the "adjustment" vacuous (exact reparametrization of the constant post
   effect); I caught and fixed it before relying on any numbers from it.
7. Added the `retprice` mechanism check as a second panel in the trends plot
   (plan.md asks for it); grouped by unit, not by treatment status, so the
   pre-1989 price gap is defined.
8. Did not modify `plan.md` (AGENTS.md: ask before changing it), so the model
   log at the end of plan.md was not updated with this session; this summary
   records the model instead: GLM-5.3-Flash Free (OpenCode), 13 Nov 2026.
9. Placebo ranking uses strict "<" (no ties occurred in the 39 estimates).
