# `data/raw/region_subsidy.csv`

Quarterly panel of 30 regions over 24 quarters. Some regions received an investment subsidy from quarter 13. Source: provided for this project.

| Column | Meaning | Units | Type |
|---|---|---|---|
| `region_id` | Region identifier, 1–30 | — | integer |
| `quarter` | Quarter, 1–24 | quarter | integer |
| `investment` | Private investment in the region | million euro | float |
| `subsidy_region` | True for regions that received the subsidy, in every quarter | — | boolean |

Rules: one row per (`region_id`, `quarter`), 720 rows; `subsidy_region` is constant within a region; `investment` is never empty.
