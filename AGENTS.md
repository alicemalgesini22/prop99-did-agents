# Rules for the agent

## Starter rules
- Never modify anything in `data/raw/`.
- After every filter, merge or drop, print the number of rows and the reason.
- Every number in a write-up comes from a file in `results/`; name the script that made it.
- Follow `plan.md`. Ask before changing anything in it, and list every analysis choice you make.
- Fix random seeds, and log the prompt, output and model name of every model call.
- No causal claims unless the design supports them. Say "I am not sure" when you are not.

## Project rules
- Run Python with `uv run python`, so it uses this project's pandas and statsmodels.
- Scripts go in `src/`, numbered in run order (`01_...py`, `02_...py`); outputs go in `data/derived/` or `results/`.
- The treatment variable is `california AND year >= 1989`. `after_treatment` alone is a year dummy, not the treatment.
- `cigsale` is per-capita cigarette **sales** in packs, not consumption.
- Do not add covariates without asking: they are missing in many years and drop rows.
- Do not quote results from published papers (e.g. Abadie et al.) or facts from memory as if computed. Mark any outside fact as "from memory, unverified".
- When you report missing values, list the exact years, computed from the data.
- Read `data/README.md` before any analysis; it describes every column, its units and its source.
- When I give you a source, citation or title, copy it exactly; never replace it with another one or reword it.
- Do not add claims I did not give you and you did not compute (e.g. "consistent with the paper"); if you add one, mark it "my inference, unverified".
