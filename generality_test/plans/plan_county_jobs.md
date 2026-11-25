# Plan: county_jobs

## Question
Did the job-placement programme change counties' employment rate?

## Data
`data/raw/county_jobs.csv`, described in `data/README_county_jobs.md`.

## Test
1. Main specification: a difference-in-differences design suited to the timing of treatment, with county and year fixed effects, all rows, no covariates.
2. Event study, relative to the last period before treatment.
3. Inference suited to the number of treated units.
4. Robustness: one check that addresses the main threat you find in the data.

## What would prove me wrong
- The estimate is close to zero, or its sign changes across the tests; or
- The event study shows clear differences in trends before treatment; or
- The inference does not reject a zero effect at the 5% level.
