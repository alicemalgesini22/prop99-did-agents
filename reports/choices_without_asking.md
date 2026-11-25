# Choices the agent made without asking

Session 3 output (brief: "A list of the choices the agent made without asking you").
Model: GLM-5.3-Flash Free in OpenCode. Two runs of the same procedure:
- **Workflow run** (agent `did-analyst`, 12 Nov 2026): every action approved by me, agent stopped after each step.
- **Autonomous run** (agent `did-auto`, 13 Nov 2026): no approvals, no stops.

"Declared" = the agent listed it itself under "Choices I made without asking". "Found by me" = the agent made the choice but did not list it (or attributed it to plan.md).

| # | Choice | Workflow run | Autonomous run |
|---|---|---|---|
| 1 | Took the column roles from data/README.md (no taxonomy file) and checked them against the data | Declared | Declared |
| 2 | Put each run's outputs in its own folder (`results/workflow/`, `results/agent/`) | Declared | Declared |
| 3 | No covariates, no filtering, all 1,209 rows | Declared | Declared |
| 4 | Built the treatment as `california AND year >= 1989`, not `after_treatment` | Checked in step 1, confirmed by me | Declared |
| 5 | Reported classical and clustered SEs for the main estimate, relied on neither | Declared | Declared |
| 6 | Type of SE for the event-study confidence intervals | Classical. **Found by me**, then added after my correction | HC1. Declared |
| 7 | Kept California in the control pool of the placebo runs | **Found by me**; first attributed to plan.md, then added after my correction | **Found by me**; not declared |
| 8 | Robustness: two-step pre-period extrapolation as primary, TWFE with California trend as secondary | Declared | Declared (with the first, wrong version of the regression) |
| 9 | Unweighted mean of the 38 control states as the comparison series | **Found by me**, then added after my correction | **Found by me**; mentioned only under limits |
| 10 | `retprice` mechanism check | Skipped. Declared (but should have asked: it is in plan.md) | Run. Declared. **1989 left out of the reported numbers (found by me)** |
| 11 | Did not re-verify Proposition 99 dates beyond the README | Declared | — |
| 12 | Did not update the model log in plan.md (would need my permission) | — | Declared |
| 13 | Placebo ranking with strict "<" (no ties) | — | Declared |

**Summary:** in both runs the agent declared most of its choices, but not all of them. The ones it missed are exactly the ones that affect inference (placebo control pool, type of standard errors, comparison series). In the workflow run I found them and had them added; in the autonomous run they stayed undeclared.
