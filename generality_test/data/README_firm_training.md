# `data/raw/firm_training.csv`

Monthly panel of 50 firms over 48 months. Some firms joined a management training programme, which was launched in month 25. Source: provided for this project.

| Column | Meaning | Units | Type |
|---|---|---|---|
| `firm_id` | Firm identifier, 1–50 | — | integer |
| `month` | Month, 1–48 | month | integer |
| `revenue` | Monthly revenue | thousand euro | float |
| `employees` | Number of employees | people | float; empty in some months |
| `joined_training` | True for firms that joined the programme, in every month | — | boolean |
| `after_launch` | True for months 25 and later, for every firm | — | boolean |

Rules: one row per (`firm_id`, `month`), 2,400 rows; `joined_training` is constant within a firm; `revenue` is never empty.
