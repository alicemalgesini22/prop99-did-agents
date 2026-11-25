# Generality test: the DiD agent on four datasets with known answers

This folder is a separate OpenCode project (originally `policy-panels`), copied here after all runs were done. It has its own generic rules and agents, with no California rules, so the agent could not reuse anything from the main analysis.

| Path | Contents |
|---|---|
| `AGENTS.md`, `opencode.json`, `.opencode/` | rules, permissions and agents used in these runs |
| `data/raw/` | the four datasets; `data/README_*.md` describe them as the agent saw them |
| `plans/` | one plan per dataset |
| `src/<dataset>/`, `results/<dataset>/` | code and outputs written by the agent; `summary.md` in each results folder |
| `results/school_support/` | the run with the "find support" prompt on the schools data |
| `answer_key/` | `make_data.py` (generates the data, seed 20261121) and `ANSWERS.md` (true effects). Kept outside the project until all runs were done |
| `pyproject.toml`, `uv.lock` | the Python environment (`uv sync`) |

Prompts: `../reports/prompts.md`, prompts 17–21. Comparison with the truth and errors: `../mistakes.md`, session 5; summary in `../README.md`, section 8.
