# data/

This folder holds the data for the California tobacco analysis.

- `raw/` — the original file, untouched. Nothing in `data/raw/` may be modified.
- `derived/` — outputs of scripts in `src/` (currently empty).

Every number below was computed from `data/raw/california_tobacco.csv` (no outside facts used except where explicitly marked).

## Source

File: `data/raw/california_tobacco.csv`, from the **CausalReasoningBenchmark**
(Sawarni, Tan & Syrgkanis, 2026), <https://huggingface.co/datasets/syrgkanislab/CausalReasoningBenchmark>,
question 158, folder `data/ds_0123`, downloaded November 2026.
The file was renamed by hand from `california_tobacco.csv.csv` (content unchanged).

Original data: **Abadie, Diamond & Hainmueller (2010)**, *"Synthetic Control Methods for
Comparative Case Studies: Estimating the Effect of California's Tobacco Control Program"*.

Note: the benchmark's `metadata.txt` lists a column `Unnamed: 0`, but the benchmark's `data.csv` does
not contain it; this file matches `data.csv`.

## Panel structure

- **1,209 rows**, one row per state–year.
- **39 states**, numeric IDs `1`–`39` (no state names in the file).
- **31 years**, `1970`–`2000`.
- **Balanced panel**: every state has exactly 31 rows; 39 × 31 = 1,209 = number of rows;
  1,209 unique `(state, year)` pairs, so no duplicates.
- No resampling, filtering, merging or dropping has been applied; row count after these checks is unchanged at 1,209.

## Columns

| Column | Meaning | Units | Type | Range (from file) | Missing years | Source of the definition |
|---|---|---|---|---|---|---|
| `state` | Numeric state ID | — | integer | 1–39 (39 distinct IDs) | none | benchmark `metadata.txt`; Abadie et al. NBER w12831 Appendix A |
| `year` | Calendar year | years | integer | 1970–2000 | none | benchmark `metadata.txt` |
| `cigsale` | Per-capita cigarette **sales**, packs per person per year, based on tax-paid sales. Measures sales, not consumption. | packs/person/year | float | 40.7–296.2 | none | benchmark `metadata.txt`; Abadie et al. Appendix A |
| `lnincome` | Natural log of real per-capita personal income (paper: converted to 1997 dollars). The paper's Table 1 labels it "Ln(GDP per capita)", which is inconsistent with its own appendix. | log (real) | float | 9.397–10.487 | 1970–1971, 1998–2000 (195 rows = 5 years × 39 states) | benchmark `metadata.txt`; Abadie et al. Appendix A |
| `beer` | Per-capita beer consumption. Unit stated in the paper as gallons but **not stated in the metadata**. | gallons/person/year (paper's stated unit) | float | 2.5–40.4 | 1970–1983, 1998–2000 (663 rows = 17 years × 39 states) | benchmark `metadata.txt`; Abadie et al. Appendix A |
| `age15to24` | Proportion (0–1) of the population aged 15–24. The paper says "percent", but the values are fractions. | proportion (0–1) | float | 0.129–0.204 | 1991–2000 (390 rows = 10 years × 39 states) | benchmark `metadata.txt`; Abadie et al. Appendix A |
| `retprice` | Average retail price per pack, including state sales taxes. Unit **not stated in either source**; probably cents — marked **unverified**. The paper's 1989 range ($1.16–$1.74) does not match this file's 1989 range (103.8–152.5). | cents/pack (unverified) | float | 27.3–351.2 | none | benchmark `metadata.txt`; Abadie et al. Appendix A |
| `california` | `True` for California (state 3), `False` otherwise. | — | boolean | — | none (31 `True` rows, all state 3) | benchmark `metadata.txt` |
| `after_treatment` | `True` for years `>= 1989`, for **every** state. It is a **year dummy**, NOT the treatment. | — | boolean | — | none (468 `True` rows = 39 states × 12 years, 1989–2000) | benchmark `metadata.txt` |

## Treatment

Treatment = `california AND year >= 1989`, i.e. 12 treated state-year rows
(state 3, 1989–2000). `after_treatment` **alone is not** the treatment: it is 1 in 456
rows that are post-1988 but not California — using it as the treatment variable would
be wrong. In California's 19 pre-1989 rows both are `False`, so they agree there.

Background (source: LAO 1990, *"Proposition 99: An Update"*, pp. 310–311; Wikipedia —
verified by hand): the treatment is **Proposition 99**, the California tobacco tax
initiative approved by voters on 8 November 1988, with a 25-cent-per-pack tax effective
1 January 1989.

## Caveats

1. **`cigsale` is sales, not consumption** — per-capita packs, tax-paid. Do not describe it as cigarette consumption.
2. **`after_treatment` is a calendar-year dummy** (`year >= 1989` for all 39 states), not the treatment variable. Only the interaction `california & (year >= 1989)` identifies the treated state-years.
3. **Missing data, exact years (computed from the file)** — each affected year is missing for all 39 states:
   - `lnincome`: 1970, 1971, 1998, 1999, 2000 (195 rows)
   - `beer`: 1970–1983 and 1998–2000 (17 years, 663 rows)
   - `age15to24`: 1991–2000 (390 rows)
   - `cigsale` and `retprice`: no missing values anywhere.
4. **Units partly unverifiable from the file alone.** `retprice` unit is not stated in the
   benchmark metadata or the paper's appendix ("probably cents", unverified), and the paper's
   1989 range does not match the file — hence "unverified". `age15to24` is a fraction despite
   the paper saying "percent". `beer`'s stated unit comes from the paper, not the metadata.
5. **`lnincome` labeling inconsistency.** The paper's Table 1 calls it "Ln(GDP per capita)"
   while its appendix says real per-capita personal income; file values are consistent with
   a log scale (9.397–10.487) either way, but two of three sources (the paper's appendix and
   the benchmark metadata) say real per-capita personal income, so that definition is used here.
6. **No state names.** The file only has numeric IDs (1–39); California is state 3. Mapping
   IDs to names requires the external state list from the original dataset.
7. **Float32 artifacts.** Many values carry single-precision representation artifacts
   (e.g. `89.8000030517578` for what is clearly 89.8), inherited from the benchmark file.
   Round only for display; do not "clean" the raw file.
8. The raw file was not modified while preparing this README; all summaries here were read
   from it directly.

## Ontology: things, relations and rules

### Questions the agent must be able to answer
1. Which state is treated, and from which year?
2. How did California's cigarette sales change after 1989 compared with the other 38 states?
3. Were California and the other states on parallel trends before 1989?
4. Is California's change unusual compared with the same estimate for each untreated state (placebo)?
5. Did California's cigarette price rise relative to the other states after the tax (the mechanism)?

### Things
- **State:** a US state, identified by `state` (1–39). One of them, state 3, is California.
- **Year:** a calendar year, `year` (1970–2000).
- **Observation:** one state in one year; one row of the file. Properties: `cigsale` (outcome), `retprice` (price, the mechanism), `lnincome`, `beer`, `age15to24` (covariates, not used).
- **Treatment:** Proposition 99, a 25-cent per pack tax in California from 1 January 1989.
- **Group:** treated (California) or control (the other 38 states).
- **Period:** pre (1970–1988) or post (1989–2000).

### Relations
- Each observation belongs to exactly one state and one year.
- Each state belongs to exactly one group, the same in every year.
- An observation is **treated** if its state is in the treated group **and** its year is in the post period.
- `after_treatment` marks the post period for every state; it is not the treatment.

### Rules (each one is a check that can be run)
1. One row per state–year: 39 × 31 = 1,209 rows, no duplicate (`state`, `year`) pairs.
2. `california` is True for state 3 only, in all 31 years.
3. The treatment (`california` AND `year >= 1989`) is True in exactly 12 rows (state 3, 1989–2000).
4. `after_treatment` is True exactly when `year >= 1989`, for all 39 states (468 rows).
5. `cigsale` and `retprice` are never empty and never negative.
6. An empty cell in `lnincome`, `beer` or `age15to24` means missing, not zero.
7. No row is dropped in the main analysis; if one is, the number of rows and the reason are printed.

### The theory as a DAG (the arrows are "causes")
```
Proposition 99 (tax, 1989) ──▶ retprice in California ──▶ cigsale in California
                                                              ▲
California's own pre-1989 downward trend ─────────────────────┘
(other forces: anti-smoking attitudes, cross-border buying, other policies)
```
The DiD design can test the arrow from Proposition 99 to `cigsale` only if the pre-1989 trend is handled (event study, trend adjustment). `retprice` lets the agent check the middle link.
