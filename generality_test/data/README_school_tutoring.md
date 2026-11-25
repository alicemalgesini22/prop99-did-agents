# `data/raw/school_tutoring.csv`

Yearly panel of 60 schools, 2012–2021. Some schools introduced a tutoring programme from the 2017 school year. Source: provided for this project.

| Column | Meaning | Units | Type |
|---|---|---|---|
| `school_id` | School identifier, 1–60 | — | integer |
| `year` | School year (2012–2021) | year | integer |
| `reading_score` | Average reading test score of the school | test points | float |
| `students` | Number of students enrolled | students | integer |
| `tutoring_school` | True for schools that introduced the programme, in every year | — | boolean |

Rules: one row per (`school_id`, `year`), 600 rows; `tutoring_school` is constant within a school; `reading_score` is never empty.
