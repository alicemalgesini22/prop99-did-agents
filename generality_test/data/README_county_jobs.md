# `data/raw/county_jobs.csv`

Yearly panel of 45 counties, 2004–2019. Some counties started a job-placement programme; counties started it in different years, and some never did. Source: provided for this project.

| Column | Meaning | Units | Type |
|---|---|---|---|
| `county` | County identifier, 1–45 | — | integer |
| `year` | Calendar year | year | integer |
| `employment_rate` | Employment rate | percent | float |
| `program_start` | Year the county started the programme; empty if it never did | year | integer or empty |

Rules: one row per (`county`, `year`), 720 rows; `program_start` is constant within a county; a county is in the programme in a year if `program_start` is not empty and `year >= program_start`; `employment_rate` is never empty.
