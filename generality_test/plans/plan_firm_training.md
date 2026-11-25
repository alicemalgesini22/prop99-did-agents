# Plan: firm_training

## Question
Did joining the training programme change firms' monthly revenue?

## Data
`data/raw/firm_training.csv`, described in `data/README_firm_training.md`.

## Test
1. Main specification: a difference-in-differences design suited to the timing of treatment, with firm and month fixed effects, all rows, no covariates.
2. Event study, relative to the last period before treatment.
3. Inference suited to the number of treated units.
4. Robustness: one check that addresses the main threat you find in the data.

## What would prove me wrong
- The estimate is close to zero, or its sign changes across the tests; or
- The event study shows clear differences in trends before treatment; or
- The inference does not reject a zero effect at the 5% level.
