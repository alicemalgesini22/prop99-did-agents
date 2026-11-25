# Plan

## Question
Did California's Proposition 99 (a 25-cent per pack cigarette tax increase, effective 1 January 1989) reduce per-capita cigarette sales in California, compared with what would have happened without it?

## Data
`data/raw/california_tobacco.csv` (renamed by hand on 6 Nov 2026 from `california_tobacco.csv.csv` to remove the doubled extension; content unchanged): 39 US states x 31 years (1970–2000), 1,209 rows.
- Treated unit: California (`state` = 3, `california` = True).
- Controls: the other 38 states (IDs 1, 2, 4–39).
- Pre-period: 1970–1988 (19 years). Post-period: 1989–2000 (12 years).
- Outcome: `cigsale` = per-capita cigarette **sales** in packs (not consumption).
- Note: `after_treatment` is a year dummy (year >= 1989) for **every** state. The treatment variable is `treated = california AND year >= 1989`.

## Theory
The tax raises the retail price of cigarettes in California. Demand for cigarettes falls when price rises, so per-capita sales in California should fall relative to the control states after 1989, and the gap should grow over time as the anti-smoking programmes funded by the tax take effect.
Mechanism check: `retprice` in California should rise relative to the control states in 1989.

## Test
1. **Main specification:** two-way fixed effects DiD: `cigsale ~ treated + state FE + year FE`, all 1,209 rows, no covariates (covariates are missing in many years; see data report).
2. **Pre-trends:** event study with one coefficient per year, 1988 as the reference year, plotted with the pre-period coefficients.
3. **Inference:** with only one treated state, standard errors are not reliable. Placebo test: assign the treatment in 1989 to each of the 38 control states in turn, re-estimate, and report where California's estimate ranks among the 39.
4. **Robustness:** the same DiD with a California-specific linear time trend fitted on the pre-period.

## Extensions (added 16 Nov 2026)
5. **Multiverse** (Bertran, Fogliato & Wu 2026): report the estimate under every reasonable choice (pre-period, reference year, trend window, placebo control pool), not one number. Script: `src/checks/multiverse.py`, written outside the project agents and run by hand.
6. **Re-run** (Kohler et al. 2026): run `did-auto` again with the same model (GLM-5.3-Flash Free) and the same prompt in a new session. Outputs in `results/agent_rerun/`.
7. **Other model** (brief, session 4; Bertran et al. 2026): run `did-auto` with DeepSeek V4.1 Flash Free, same prompt. Outputs in `results/agent_deepseek/`.
8. **Framing** (Alizadeh, Gilardi, Mosleh & Kasneci 2026; Bertran et al. 2026): run `did-auto` with GLM-5.3-Flash Free and a prompt that asks it to find support for the hypothesis. Outputs in `results/agent_framing/`. Compare the numbers and, above all, the verdict with the neutral run.
9. **Independent check of the headline number** (brief, session 4; Galiani, López & Sosa 2026): recompute the 2×2 DiD by hand in Excel.
10. **Generality test** (does the agent work on any data?): run `did-auto` on four datasets whose true effects I know but the agent does not, in a separate project folder (`policy-panels`) with generic rules only. The data descriptions do not say the data are constructed; the generating script and the true effects are kept outside the folder until all runs are done. Datasets: `firm_training` (common timing, true effect +8), `school_tutoring` (no effect; run twice, neutral and with the "find support" prompt), `region_subsidy` (no effect, but treated units on a steeper pre-trend), `county_jobs` (staggered adoption, effects that differ by cohort). Outputs and code copied to `generality_test/`.

The verdict rule for every run is fixed in advance: the "What would prove me wrong" section above. Every prompt given to an agent is recorded word for word in `reports/prompts.md`.

## Prediction
A negative effect: California's per-capita sales fall by more than the control states after 1989.

## What would prove me wrong
- The effect disappears (close to zero, or not clearly negative) once California's pre-1989 trend is accounted for (test 4); or
- The event study shows the gap was already widening at the same pace before 1989, so the post-1989 gap is just the old trend continuing; or
- California's estimate is not the most negative of the 39 in the placebo distribution. Placebo p-value = California's rank / 39: rank 1 gives p = 1/39 ≈ 0.026; rank 2 already gives p = 2/39 ≈ 0.051, above 0.05.

## Model log
Agent model: GLM-5.3-Flash Free in OpenCode (session 1, 5 Nov 2026). Record any model change here with the date.
- 6 Nov 2026: new session, Plan mode, AGENTS.md test. The agent restated all rules and the plan correctly and ran nothing.
- 12 Nov 2026: `opencode.json` set to ask before every edit and every shell command ("manual mode"). Built three agents in `.opencode/agent/`: `did-analyst` (step by step, asks for approval), `did-auto` (same procedure, no approvals, no stops), `did-reviewer` (read-only). A column taxonomy (`data/taxonomy.json`) was built and then dropped: the data are numeric, and the column roles are set in `did_config.json`, confirmed by hand.
- 12 Nov 2026: workflow run with `did-analyst`, GLM-5.3-Flash Free. Outputs in `results/workflow/`, code in `src/workflow/`.
- 13 Nov 2026: autonomous run with `did-auto`, GLM-5.3-Flash Free. Outputs in `results/agent/`, code in `src/agent/`.
- 13 Nov 2026: after the lecture "Knowledge for agents": added an ontology (questions, things, relations, rules, DAG) to `data/README.md`; added error types E1–E7 to `mistakes.md` and tagged every mistake; created the skill `.opencode/skills/checking-results/SKILL.md` (tested: OpenCode lists it).
- 16 Nov 2026: added extensions 5–9 (multiverse, re-run, other model, framing, Excel check); `did-auto` now saves to the folder named in the prompt; all prompts recorded in `reports/prompts.md`.
- 16 Nov 2026: re-run (GLM), DeepSeek run and two framing runs (the second one blind, with a copy of plan.md without the "Extensions" section) done with `did-auto`; pandas blocked by Windows application control in all of them, so the agents wrote the estimation in numpy. Outputs in `results/agent_rerun/`, `results/agent_deepseek/`, `results/agent_framing/`, `results/agent_run5/`. `uv sync` run after each autonomous run.
- 17 Nov 2026: generality test prepared: AGENTS.md split into rules for every dataset and California-only rules; the agents now use the plan and data description named in the prompt; two constructed test datasets with descriptions and plans added.
- 18 Nov 2026: GLM-5.3-Flash Free withdrawn from OpenCode (opencode.ai/docs/zen). From here on all runs use DeepSeek V4.1 Flash Free.
- 21 Nov 2026: generality test redesigned: four datasets in a separate folder (`policy-panels`), no hint that the data are constructed, answer key outside the folder. The earlier two-dataset version (17 Nov) was never run and was deleted.
- 21–25 Nov 2026: five runs with `did-auto` and DeepSeek V4.1 Flash Free. Tests 4 and 5 add "Do not call the reviewer and do not add checks beyond the plan" to the prompt, because of the daily free limit. `uv sync` changed nothing after any run. Compared with the answer key on 25 Nov: verdict right in all four datasets (see `mistakes.md`, session 5).
