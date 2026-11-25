# Rules for the agent

- Never modify anything in `data/raw/`.
- After every filter, merge or drop, print the number of rows and the reason.
- Every number in a write-up comes from a file in `results/`; name the script that made it.
- Follow the plan named in the prompt. Ask before changing anything in it, and list every analysis choice you make.
- Fix random seeds.
- No causal claims unless the design supports them. Say "I am not sure" when you are not.
- Run Python with `uv run python`.
- Scripts go in `src/`, numbered in run order (`01_...py`, `02_...py`); outputs go in `results/`.
- Read the data description named in the prompt before any analysis.
- Do not quote results from published papers or facts from memory as if computed. Mark any outside fact as "from memory, unverified".
- Do not add claims you did not compute or were not given; if you add one, mark it "my inference, unverified".
- When you report missing values, list the exact periods, computed from the data.
- Do not add covariates without asking.
