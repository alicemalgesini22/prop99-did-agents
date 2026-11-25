---
name: checking-results
description: Checks a difference-in-differences run before its results are reported. Recomputes the headline estimate with a separate short script, runs the rules in data/README.md, and lists every choice not in plan.md. Use when asked to check, verify or audit results, or before writing up any number.
---

# Checking results

The human tells you which run to check (for example `results/workflow/` or `results/agent/`). Do not change any file of that run. Write your own files to `results/checks/` and your own code to `src/checks/`.

1. Read `plan.md`, `data/README.md` and the run's `did_config.json` and `summary.md`.
2. **Rules.** Write `src/checks/01_rules.py`, which tests every rule in the "Rules" section of `data/README.md` on `data/raw/california_tobacco.csv`. Print PASS or FAIL for each rule, with the number that decides it.
3. **Headline number.** Write `src/checks/02_recompute.py`, which recomputes the main estimate as a 2×2 difference of means (treated pre and post, controls pre and post) using only pandas, without statsmodels and without any code from the run. Print the four means and the difference.
4. **Compare.** Put every number from the run's `summary.md` that you recomputed next to your value. Mark each one SAME (equal to the rounding shown) or DIFFERENT.
5. **Choices.** List every analysis choice the run made that is not written in `plan.md`. Mark each one "declared" (it is in the run's "Choices I made without asking") or "not declared".
6. **Claims.** List every sentence in `summary.md` that states a fact the run did not compute and the human did not give (sources, dates, methods, "as plan.md specifies"). Quote it and say where it should come from.
7. Write everything to `results/checks/<run name>_check.md`. Tag each problem with an error type from the "Error types" table in `mistakes.md` (E1–E7). Do not edit `mistakes.md` yourself; the human adds the entries.

Rules: run Python with `uv run python`. Never modify `data/raw/`. If a number differs, say so and stop guessing why; report both values.
