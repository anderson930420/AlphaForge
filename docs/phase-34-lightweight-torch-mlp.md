# Phase 34: Lightweight PyTorch MLP Baseline

## Goal

Add a lightweight optional PyTorch MLP (Multi-Layer Perceptron) regression baseline
for supervised tabular asset-pricing experiments. The MLP serves as a CPU-friendly
deep learning alternative to the closed-form ridge baseline and the sklearn model
adapters, without requiring GPU acceleration, classification models, or complex
neural network architectures.

## Boundary

This phase adds a lightweight optional PyTorch MLP regression baseline for
supervised tabular asset-pricing experiments. It does not claim profitability,
run live trading, use GPU-specific training, implement classification, or replace
sklearn/tree baselines.

## Limitations

- CPU-only training by default. No CUDA or MPS device selection is implemented.
- No hyperparameter search (grid/random/Bayesian).
- No early stopping, learning rate scheduling, or validation split.
- No batch normalization, residual connections, or advanced architectures.
- No feature importance extraction (importance_type = not_available_for_torch_mlp).
- No classification support (binary, multiclass, or multilabel).
- No LSTM, Transformer, or attention-based architectures.
- The MLP is intended as a research baseline, not a production model.
- Training is inherently stochastic; different seeds produce different predictions.
- Small batch sizes and few epochs are expected for fixture-sized panels.

## Optional Installation

PyTorch is an optional dependency. The core AlphaForge package and existing test
suite do not require torch.

```bash
python3 -m pip install -e ".[torch]"
```

If torch is not installed and a torch MLP function is invoked, the error is:

```
PyTorch is required for torch MLP models.
Install with: python3 -m pip install -e ".[torch]"
```

Tests gracefully skip when torch is unavailable. The full test suite must pass
regardless of torch installation status.

## Input Format

The model accepts the same supervised feature-label panel as the sklearn model
adapters and the baseline ridge regressor:

```csv
asset_id,date,Mom12m,BM,Investment,ret_fwd_1m
A,2024-01-15,0.10,0.50,1000,0.02
A,2024-02-20,0.11,0.51,1100,-0.01
...
```

Required columns: `asset_id`, `date`, at least one numeric feature column, and a
numeric label column.

## Model Architecture

```
Linear(input_dim, hidden_dim)
ReLU
Dropout(dropout)
Linear(hidden_dim, hidden_dim // 2)
ReLU
Linear(hidden_dim // 2, 1)
```

### Default Hyperparameters

| Parameter      | Default |
|----------------|---------|
| hidden_dim     | 64      |
| dropout        | 0.2     |
| epochs         | 20      |
| batch_size     | 32      |
| learning_rate  | 0.001   |
| weight_decay   | 0.0001  |
| seed           | 42      |

### Loss and Optimizer

- Loss: `MSELoss`
- Optimizer: `Adam`

### Device

CPU only by default. CUDA is not required.

## Feature Handling

- Median imputation for missing numeric features (computed from training set).
- Standard scaling (z-score, using training set means and standard deviations).
- Time-based train/test split (no random shuffling).
- Feature columns can be explicitly provided via `--feature-cols` or auto-inferred.

### Auto-Inference Rules

When `--feature-cols` is omitted, numeric columns are auto-inferred while excluding:
- `asset_id`, `date`, and the label column
- `target_date`, `horizon_months`, `source`
- Any column starting with `ret_fwd`
- Any column starting with `prediction` or `output`

## Example Command

```bash
python3 -m pip install -e ".[torch]"

PYTHONPATH=src python3 scripts/run_torch_mlp_baseline.py \
  --panel tests/fixtures/ml_baseline/supervised_panel.csv \
  --output-dir artifacts/phase34/torch_mlp_demo \
  --label-col ret_fwd_1m \
  --train-end 2024-03-31 \
  --feature-cols Mom12m,BM,Investment \
  --epochs 5 \
  --batch-size 4 \
  --hidden-dim 32 \
  --learning-rate 0.001 \
  --weight-decay 0.0001 \
  --dropout 0.1 \
  --seed 42
```

### CLI Arguments

| Argument       | Required | Default       | Description                              |
|----------------|----------|---------------|------------------------------------------|
| --panel        | yes      | —             | Path to supervised panel CSV             |
| --output-dir   | yes      | —             | Output directory for artifacts           |
| --label-col    | no       | ret_fwd_1m    | Name of label column                     |
| --train-end    | yes      | —             | Train/test split date (YYYY-MM-DD)       |
| --feature-cols | no       | auto-inferred | Comma-separated feature column names     |
| --asset-id-col | no       | asset_id      | Asset identifier column                  |
| --date-col     | no       | date          | Date column                              |
| --epochs       | no       | 20            | Number of training epochs                |
| --batch-size   | no       | 32            | SGD batch size                           |
| --hidden-dim   | no       | 64            | Hidden layer dimension                   |
| --learning-rate| no       | 0.001         | Adam learning rate                       |
| --weight-decay | no       | 0.0001        | Adam weight decay                        |
| --dropout      | no       | 0.2           | Dropout probability                      |
| --seed         | no       | 42            | Random seed for reproducibility          |

## Output Artifacts

All artifacts are written to `--output-dir`:

| File                  | Description                                         |
|-----------------------|-----------------------------------------------------|
| train_config.json     | CLI arguments and configuration                     |
| model_summary.json    | Model metadata (architecture, hyperparams, counts)  |
| training_history.csv  | Per-epoch training loss (epoch, train_loss)         |
| predictions.csv       | Predicted returns and realized labels               |
| metrics.json          | MSE, MAE, correlation, row counts                   |
| feature_importance.csv| Feature names with null importance                   |

### predictions.csv Columns

| Column            | Description                    |
|-------------------|--------------------------------|
| asset_id          | Asset identifier               |
| date              | Date (month-end aligned)       |
| predicted_return  | Model prediction               |
| ret_fwd_1m        | Realized forward return label  |
| model_name        | Always "torch_mlp_regressor"   |

This predictions.csv is compatible with Phase 30 ML prediction diagnostics.

### metrics.json Fields

| Field                         | Description                               |
|-------------------------------|-------------------------------------------|
| row_count                     | Number of rows with valid prediction+label |
| train_row_count               | Number of training rows                     |
| test_row_count                | Number of test rows                         |
| mse                           | Mean squared error                         |
| mae                           | Mean absolute error                        |
| mean_prediction               | Mean of predicted values                   |
| mean_label                    | Mean of label values                       |
| prediction_label_correlation  | Correlation (if computable)                 |

### model_summary.json Fields

| Field           | Value                       |
|-----------------|-----------------------------|
| model_name      | torch_mlp_regressor         |
| model_type      | torch_mlp_regressor         |
| feature_cols    | List of feature column names|
| label_col       | Label column name           |
| train_end       | Train/test split date       |
| train_row_count | Training set size           |
| test_row_count  | Test set size               |
| hidden_dim      | Hidden layer dimension      |
| dropout         | Dropout probability         |
| epochs          | Number of epochs            |
| batch_size      | SGD batch size              |
| learning_rate   | Adam learning rate          |
| weight_decay    | Adam weight decay           |
| seed            | Random seed                 |
| torch_required  | true                        |

### feature_importance.csv

| Column           | Value                        |
|------------------|------------------------------|
| feature          | Feature column name          |
| importance       | null                         |
| importance_type  | not_available_for_torch_mlp  |

## Running Phase 30 Diagnostics on predictions.csv

The predictions output is compatible with Phase 30 ML prediction diagnostics:

```bash
PYTHONPATH=src python3 scripts/run_ml_prediction_diagnostics.py \
  --predictions artifacts/phase34/torch_mlp_demo/predictions.csv \
  --output-dir artifacts/phase34/torch_mlp_demo/ml_prediction_diagnostics \
  --prediction-col predicted_return \
  --label-col ret_fwd_1m \
  --quantiles 2
```

## Testing

```bash
# Unit tests (skips gracefully if torch not installed)
PYTHONPATH=src python3 -m pytest tests/test_ml_torch.py -q

# CLI integration tests
PYTHONPATH=src python3 -m pytest tests/test_run_torch_mlp_baseline.py -q

# Full suite (must pass regardless of torch installation)
PYTHONPATH=src python3 -m pytest -q
```

Tests that require PyTorch use `pytest.importorskip("torch")` internally or
`@pytest.mark.skipif(not TORCH_AVAILABLE, ...)` at the class level. Utility
tests (feature inference, preprocessing, evaluation, time split) do not
require torch and always run.

## Validation Commands

```bash
git diff --check

PYTHONPATH=src python3 -m pytest tests/test_ml_torch.py -q
PYTHONPATH=src python3 -m pytest tests/test_run_torch_mlp_baseline.py -q
PYTHONPATH=src python3 -m pytest -q
```

## Manual Smoke

```bash
python3 -m pip install -e ".[torch]"

PYTHONPATH=src python3 scripts/run_torch_mlp_baseline.py \
  --panel tests/fixtures/ml_baseline/supervised_panel.csv \
  --output-dir artifacts/phase34/torch_mlp_demo \
  --label-col ret_fwd_1m \
  --train-end 2024-03-31 \
  --feature-cols Mom12m,BM,Investment \
  --epochs 5 \
  --batch-size 4 \
  --hidden-dim 32 \
  --learning-rate 0.001 \
  --weight-decay 0.0001 \
  --dropout 0.1 \
  --seed 42

PYTHONPATH=src python3 scripts/run_ml_prediction_diagnostics.py \
  --predictions artifacts/phase34/torch_mlp_demo/predictions.csv \
  --output-dir artifacts/phase34/torch_mlp_demo/ml_prediction_diagnostics \
  --prediction-col predicted_return \
  --label-col ret_fwd_1m \
  --quantiles 2
```
