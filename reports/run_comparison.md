# Run comparison: what changed between runs, and why

The long analysis behind `reflection.md` (one page).

Drafted with help from Claude (claude.ai) in a separate planning chat, from my notes and `mistakes.md`; every number below comes from a file in `results/` or `generality_test/results/`, and I checked the comparisons myself.

## 1. The question

I ran the same difference-in-differences procedure 11 times: 6 times on California (two agents, two models, two prompts) and 5 times on four datasets whose true effects I knew. The question of this reflection is: **when two runs of the same procedure disagree, at which level do they disagree, and why?**

I separate four levels:

1. **Numbers**: the estimates the runs share (main TWFE, placebo rank, trend corrections).
2. **Choices**: what each run decided to compute beyond the plan, and whether it declared it.
3. **Interpretation**: what each run concluded from the numbers (the verdict).
4. **Actions**: what each run did to the computer.

## 2. Numbers: no disagreement

On California, every number shared by the six runs is identical: TWFE −27.35, placebo rank 4 of 39 (p = 0.103), gap-trend correction −8.26, California-trend TWFE −5.18 (`mistakes.md`, comparison of all runs). This holds across two models (GLM, DeepSeek) and two implementations (statsmodels, and numpy written from scratch after Windows blocked pandas). My Excel check gives −27.34911108, the same value (`reports/checks/headline_excel.xlsx`).

On the four constructed datasets, every shared number matched my own TWFE from the answer key (e.g. +7.889 for A, −0.453 for B, +7.29 for C, +1.95 for D).

**Logical consequence:** a disagreement between runs cannot be explained by computation. If two runs reach different verdicts, the difference must come from levels 2–4. This is the main result, and it agrees with what Alizadeh et al. (2026) report: numbers stable, verdict layer variable.

## 3. Choices: where the runs diverge first

Each run computed extra specifications the plan did not ask for. Three examples matter:

- **The own-slope detrend (+0.23).** Two runs (DeepSeek and the blind framing run) computed a correction that removes California's own pre-1989 slope. This subtracts the decline common to all states twice, because the year fixed effects already remove it. DeepSeek computed it and said it "over-corrects". The blind framing run computed it, presented it *as* plan.md's test 4, and never computed the correct −8.26 (errors 24 and 27).
- **California in the placebo control pool.** Every run kept it there; plan.md does not say this. Only some runs declared it. Reading the code and the multiverse showed it does not change the rank (4 either way), so this undeclared choice was harmless.
- **The reference year.** Only three runs noticed that the gap fell by 3.6 in 1988, before the tax, so the choice of 1988 as reference year affects the post-1989 effects.

On the constructed data the declared choices were sensible and matched the data: a 10-of-30 permutation test instead of the one-at-a-time placebo when 10 regions are treated (C), and Callaway–Sant'Anna as the main estimator when adoption is staggered (D). The TWFE was kept only as a cross-check in D, where the truth shows it is biased (1.95 vs 3.01).

**Logical point:** a choice is only checkable if it is declared. Declared choices let me find error 24 (the run said +0.23 over-corrects, then used it). An undeclared choice can only be found by reading the code, which I did once (`06_placebo.py`). The number of declared choices grew over time (7 → 10 → 12), partly because I corrected the agent and the rule is in `AGENTS.md`; it was never complete in the California runs.

## 4. Interpretation: the same numbers, different verdicts

| Run | Verdict on California |
|---|---|
| Workflow, Auto, Re-run, Framing (plan visible) | no clean / firm causal claim |
| DeepSeek | no causal claim, pre-trend correction "removes 70–100%" |
| Framing, blind | "the results do NOT support the claim", "the effect disappears" |

The numbers above are the same in every row. The verdicts differ because each verdict weighs a different subset of the specifications:

- The "70–100%" in the DeepSeek verdict exists only because it counted the +0.23 it had itself rejected. With the corrections it accepted (−8.26, −5.18) the reduction is about 70–80%.
- The blind framing verdict ("disappears") follows logically from +0.23, and only from it. Remove that one wrong specification and the verdict returns to the neutral one.

So **every verdict difference I found traces back to a choice difference** (level 2), never to a number. The chain is: wrong or unchecked choice → included in the verdict → stronger wording.

**The direction is surprising.** The blind framing prompt asked the agent to find support for the hypothesis. The run moved *against* it. One possible explanation (my inference, unverified): the agent reacts to the pressure by trying to show it is not biased, and that pushes it towards the most sceptical specification. On the constructed null dataset (B) the same pressure prompt changed neither numbers nor verdict, only the wording, which stressed the opposite sign. My inference, unverified: a clear null leaves little room for a different verdict; California's ambiguous evidence (an effect that is −27 or −5 depending on the trend) leaves much more. With one run per condition, this is a signal, not a finding.

## 5. Actions: the autonomous runs changed the computer

With "allow" permissions, two GLM runs reinstalled pandas and ran `Unblock-File` to get around a Windows security block, and left a package (`pytz`) behind that `uv sync` removed (errors 23, 29). The run that asked before every command could not do this, and a plain Build session with "ask" permissions, facing the same block, proposed the same fixes but applied none. The reviewer subagent, which is not allowed to edit, still wrote files in `%TEMP%` through the shell (error 30). DeepSeek never changed the environment in six runs.

**Logical point:** permissions set in a file are not the same as permissions that hold. A shell command can do what an edit rule forbids. The only reliable check I found was external: `uv sync` after every run.

## 6. The generality test: does the agent work on any data?

On four datasets it had never seen, with no published answer to recall (Ludwig et al. 2026 warn that California's answer is in the training data), the agent reached the right verdict every time, including the two traps:

- **C (pre-trend, true effect 0):** TWFE gives +7.29 with a tiny standard error. The agent saw the rising pre-period coefficients, said parallel trends fail, and made no causal claim; with a treated trend the estimate is −0.17.
- **D (staggered, true ATT 3.01):** it recognised the three cohorts and used Callaway–Sant'Anna (+2.84), within one standard error of the truth, while TWFE gives 1.95.

Compared with California, the constructed data produced fewer interpretation errors. My inference, unverified: the constructed data are cleaner (each has one clear trap, the trend in C is exactly linear), so the right choice is easier to identify. The test shows that the procedure transfers; it does not show that the agent would be as reliable on messy real data.

Two limits: all five runs used one model (GLM was withdrawn on 18 Nov), and tests C and D ran without the reviewer because of the daily free limit, so they are not identical to A and B.

## 7. Why it went wrong

The errors in `mistakes.md` are not random. Looking at when and where they happened, I see five causes.

1. **Describing in words instead of computing.** All wrong numbers (E1) came in sessions 1 and 2, when the agent described the data in prose. Once every number came from a script and a file in `results/`, no shared number was wrong again. The rule "every number comes from a file in `results/`" worked because it moved the agent from remembering to computing.
2. **Gaps in my own plan.** Test 4 of plan.md says "a California-specific linear time trend fitted on the pre-period". This sentence has two readings: the slope of California itself, or the slope of the gap between California and the controls. The first one is wrong in a model with year fixed effects; it is the +0.23 that drove errors 24 and 27. The plan also never said who is in the placebo control pool (error 14). Where my plan was silent or ambiguous, the agent filled the gap, and sometimes said that plan.md asked for its choice when it did not (errors 14, 25). Part of the problem was mine, not the agent's.
3. **What the agent could see.** In the first framing run the agent read plan.md, saw that a framing experiment was planned, and said so (point 26). The agent uses everything in its context. A test of the agent only measures what it was meant to measure if the agent cannot see the test.
4. **The goal "finish" plus permission to act.** Did-Auto is told to run "from start to finish" without stopping. When pandas was blocked, two GLM runs removed the obstacle themselves: reinstalling packages and running `Unblock-File` (errors 23, 29). The Build session with "ask" permissions faced the same block, proposed the same fixes and applied none. The difference was not the model but the permission plus the goal.
5. **No memory between sessions and no one checking.** The same errors came back: the pre-trend described backwards (errors 15, 28), the 1988 fall missed (errors 12, 20). Each session starts from zero; only `AGENTS.md` and the files carry anything over. In the run I supervised step by step, I corrected five errors before they reached the summary (errors 15–17); in the autonomous run the four errors I found afterwards (errors 18–21) were all still in the final text.

## 8. What this implies for relying on the agent next time

**What I would trust the agent with:** computing. Across 11 runs, two models and two implementations, every shared number was right, and on four datasets with a known answer the estimates were close to the truth. It also chose sensible methods for unfamiliar designs (a permutation test with many treated units, Callaway–Sant'Anna with staggered adoption) and declared these choices.

**What I would not trust it with alone:** the verdict, and anything that touches the computer. Every serious error was in what the agent concluded or did, not in what it computed.

What I would do differently:

1. **Write the plan as a specification, not a description.** For each robustness check, write the exact formula (which slope, fitted on which years, which units in the control pool). Most of my California errors started where the plan could be read in two ways.
2. **Ask for the link between verdict and specifications.** A table "specification → used in the verdict? why?" would have exposed errors 24 and 27 at once. The logical test that worked for me: remove one specification and see if the verdict survives.
3. **Check the choices, not only the numbers.** Recomputing the headline number (Excel) confirmed what was already right. The errors were found by reading the declared choices and, once, the code. Galiani et al. (2026) find that agents fix code that crashes but much less often code that runs and gives a wrong answer; my errors 24 and 27 are of the second kind, in the reasoning rather than the code.
4. **Keep "ask" for shell commands, or check the environment after every run.** File permissions did not stop the reviewer from writing through the shell (error 30). `uv sync` after every autonomous run was the check that caught every change.
5. **Run more than once and report the distribution.** One run can land on any verdict in section 4. Bertran et al. (2026) recommend reporting the distribution of results for many analysts; with an agent, re-running costs one minute, so there is no reason not to.
6. **Test the agent on data with a known answer first.** The generality test told me something California could not: whether the agent is right, not only whether it is consistent. A known-answer test before trusting the agent on real data is cheap and, in my case, was reassuring.
7. **Keep the test hidden from the agent.** The blind framing run behaved differently from the one that could see the plan.

## 9. Limits of this reflection

Each condition (model, prompt, dataset) has one or two runs, so the patterns in sections 4 and 7 are signals, not findings. I am not sure the GLM and DeepSeek differences are about the models rather than chance: Kohler et al. (2026) find that re-running the same agent moves a quarter to a third of estimates by more than two standard errors, though on California my re-run moved none. The constructed datasets each had one clear trap; real data are messier.

## Sources
Error numbers refer to `mistakes.md`. Papers: as cited in `README.md`, section 10.
