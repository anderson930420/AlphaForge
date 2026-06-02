# CRSP ML E2E Walk-Forward Window Semantics

This note explains how to interpret the dates shown in the CRSP ML E2E report, especially the difference between the full dataset coverage and the first out-of-sample test window.

## Key distinction

The CRSP ML dataset can begin in an earlier year, for example 1996, while the first reported walk-forward test window can begin later, for example 2006.

That is expected when the walk-forward split uses a fixed training lookback.

Example:

- Full ML dataset coverage: 1996–2023
- Train years: 10
- Test years: 1
- Step years: 1
- First window: `train_1996-2005_test_2006`

In this setup, 1996–2005 are not missing. They are used as the training period for the first out-of-sample test year, 2006.

## How to read a window id

A window id such as:

```text
train_1996-2005_test_2006
```

means:

| Segment | Meaning |
| --- | --- |
| `train_1996-2005` | The model is fitted on observations from 1996 through 2005. |
| `test_2006` | The model is evaluated out-of-sample on observations from 2006. |

Therefore, if the report says the worst window is `train_1996-2005_test_2006`, it does not mean the dataset starts in 2006. It means 2006 is the first out-of-sample evaluation period after using the initial 10-year training window.

## Why this matters

For time-series ML validation, the first several years are often consumed by the initial training window. The evaluation series starts only after enough history is available to train the model.

This design avoids look-ahead bias:

1. Train only on data available before the test period.
2. Predict the next out-of-sample period.
3. Roll the window forward.
4. Repeat until the final test period.

## Interview-safe wording

A precise way to explain the report is:

> The raw CRSP ML dataset starts in 1996, but the out-of-sample walk-forward diagnostics start in 2006 because the first 10 years are used as the initial training window. A worst window labeled `train_1996-2005_test_2006` means the 2006 OOS evaluation performed worst; it does not imply that earlier data were absent.

## Report interpretation rule

When reading best/worst windows in the CRSP ML E2E report:

- Use `dataset_date_min` and `dataset_date_max` to describe full data coverage.
- Use `train_*` in the window id to describe the in-sample fitting period.
- Use `test_*` in the window id to describe the out-of-sample evaluation period.
- Do not interpret the first test year as the beginning of the dataset.
