from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .ml_dataset import build_ml_dataset, time_train_test_split

_METADATA_EXCLUDE = {"asset_id", "date", "target_date", "horizon_months", "source"}
_PREDICTION_EXCLUDE = {"prediction", "predicted", "output"}


def _require_torch() -> None:
    try:
        import torch  # noqa: F401
    except ImportError:
        raise ImportError(
            "PyTorch is required for torch MLP models.\n"
            'Install with: python3 -m pip install -e ".[torch]"'
        ) from None


def _infer_feature_cols(
    panel_df: pd.DataFrame,
    *,
    asset_id_col: str,
    date_col: str,
    label_col: str,
) -> list[str]:
    exclude = _METADATA_EXCLUDE | {label_col, asset_id_col, date_col}
    return [
        c for c in panel_df.columns
        if c not in exclude
        and not c.startswith("ret_fwd")
        and not any(
            c.lower().startswith(p) for p in _PREDICTION_EXCLUDE
        )
        and pd.api.types.is_numeric_dtype(panel_df[c])
    ]


def _preprocess(
    train_df: pd.DataFrame,
    *,
    feature_cols: list[str],
    label_col: str,
) -> dict:
    X_train = train_df[feature_cols].copy().astype(float)
    y_train = train_df[label_col].copy().astype(float)

    medians = X_train.median().fillna(0.0)
    X_filled = X_train.fillna(medians)

    means = X_filled.mean().fillna(0.0)
    stds = X_filled.std(ddof=0).replace(0.0, 1.0).fillna(1.0)

    X_proc = ((X_filled - means) / stds).values.astype(np.float32)
    y_proc = y_train.values.astype(np.float32)

    if np.isnan(y_proc).any():
        y_proc = np.nan_to_num(y_proc, nan=0.0)

    return {
        "X": X_proc,
        "y": y_proc,
        "medians": medians,
        "means": means,
        "stds": stds,
        "input_dim": len(feature_cols),
    }


def _preprocess_predict(
    df: pd.DataFrame,
    *,
    feature_cols: list[str],
    preproc: dict,
) -> np.ndarray:
    X = df[feature_cols].copy().astype(float)
    X_filled = X.fillna(preproc["medians"])
    X_proc = ((X_filled - preproc["means"]) / preproc["stds"]).values.astype(np.float32)
    return X_proc


def _build_mlp(
    input_dim: int,
    hidden_dim: int = 64,
    dropout: float = 0.2,
) -> object:
    import torch.nn as nn

    return nn.Sequential(
        nn.Linear(input_dim, hidden_dim),
        nn.ReLU(),
        nn.Dropout(dropout),
        nn.Linear(hidden_dim, hidden_dim // 2),
        nn.ReLU(),
        nn.Linear(hidden_dim // 2, 1),
    )


def _train_epoch(
    model: object,
    optimizer: object,
    criterion: object,
    X: np.ndarray,
    y: np.ndarray,
    batch_size: int,
) -> float:
    import torch

    model.train()
    n = len(X)
    perm = torch.randperm(n)
    total_loss = 0.0
    n_batches = 0

    for i in range(0, n, batch_size):
        indices = perm[i : i + batch_size]
        x_batch = torch.tensor(X[indices], dtype=torch.float32)
        y_batch = torch.tensor(y[indices], dtype=torch.float32).view(-1, 1)

        optimizer.zero_grad()
        pred = model(x_batch)
        loss = criterion(pred, y_batch)
        loss.backward()
        optimizer.step()

        total_loss += float(loss.item()) * len(indices)
        n_batches += 1

    if n_batches == 0:
        return 0.0
    return total_loss / n


def _eval_loss(
    model: object,
    criterion: object,
    X: np.ndarray,
    y: np.ndarray,
    batch_size: int,
) -> float:
    import torch

    model.eval()
    total_loss = 0.0
    n = len(X)

    with torch.no_grad():
        for i in range(0, n, batch_size):
            x_batch = torch.tensor(X[i : i + batch_size], dtype=torch.float32)
            y_batch = torch.tensor(y[i : i + batch_size], dtype=torch.float32).view(-1, 1)
            pred = model(x_batch)
            loss = criterion(pred, y_batch)
            total_loss += float(loss.item()) * len(x_batch)

    return total_loss / n if n > 0 else 0.0


def fit_torch_mlp(
    train_df: pd.DataFrame,
    *,
    feature_cols: list[str],
    label_col: str,
    hidden_dim: int = 64,
    dropout: float = 0.2,
    epochs: int = 20,
    batch_size: int = 32,
    learning_rate: float = 0.001,
    weight_decay: float = 0.0001,
    seed: int = 42,
) -> dict:
    _require_torch()
    import torch

    torch.manual_seed(seed)
    if hasattr(torch, "set_num_threads"):
        torch.set_num_threads(1)

    preproc = _preprocess(
        train_df,
        feature_cols=feature_cols,
        label_col=label_col,
    )

    model = _build_mlp(
        input_dim=preproc["input_dim"],
        hidden_dim=hidden_dim,
        dropout=dropout,
    )

    criterion = torch.nn.MSELoss()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=learning_rate,
        weight_decay=weight_decay,
    )

    history: list[dict] = []

    X_train = preproc["X"]
    y_train = preproc["y"]

    for epoch in range(1, epochs + 1):
        train_loss = _train_epoch(
            model, optimizer, criterion,
            X_train, y_train, batch_size,
        )
        history.append({"epoch": epoch, "train_loss": round(train_loss, 8)})

    return {
        "model": model,
        "model_name": "torch_mlp_regressor",
        "feature_cols": feature_cols,
        "label_col": label_col,
        "preproc": preproc,
        "train_row_count": int(len(train_df)),
        "hidden_dim": hidden_dim,
        "dropout": dropout,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "weight_decay": weight_decay,
        "seed": seed,
        "history": history,
    }


def predict_torch_mlp(
    model_pack: dict,
    dataset_df: pd.DataFrame,
    *,
    prediction_col: str = "predicted_return",
    asset_id_col: str = "asset_id",
    date_col: str = "date",
) -> pd.DataFrame:
    import torch

    feature_cols = model_pack["feature_cols"]
    preproc = model_pack["preproc"]

    X_pred = _preprocess_predict(dataset_df, feature_cols=feature_cols, preproc=preproc)

    model = model_pack["model"]
    model.eval()
    with torch.no_grad():
        x_tensor = torch.tensor(X_pred, dtype=torch.float32)
        predictions = model(x_tensor).numpy().flatten()

    label_col = model_pack.get("label_col", "ret_fwd_1m")
    result = pd.DataFrame({
        "asset_id": dataset_df[asset_id_col].values,
        "date": dataset_df[date_col].values,
        prediction_col: predictions,
        "model_name": model_pack["model_name"],
    })

    if label_col in dataset_df.columns:
        result[label_col] = dataset_df[label_col].values

    return result


def evaluate_torch_predictions(
    predictions_df: pd.DataFrame,
    *,
    label_col: str = "ret_fwd_1m",
    prediction_col: str = "predicted_return",
) -> dict:
    if label_col not in predictions_df.columns:
        return {
            "row_count": len(predictions_df),
            "error": f"label column '{label_col}' not found in predictions",
        }

    y_true = pd.to_numeric(predictions_df[label_col], errors="coerce")
    y_pred = pd.to_numeric(predictions_df[prediction_col], errors="coerce")
    mask = y_true.notna() & y_pred.notna()
    y_true = y_true[mask].values
    y_pred = y_pred[mask].values
    row_count = len(y_true)

    result: dict = {
        "row_count": int(row_count),
        "mean_prediction": float(np.nanmean(predictions_df[prediction_col]) if len(predictions_df) > 0 else np.nan),
        "mean_label": float(np.nanmean(predictions_df[label_col]) if len(predictions_df) > 0 else np.nan),
    }

    if row_count == 0:
        return result

    errors = y_true - y_pred
    result["mse"] = float(np.mean(errors ** 2))
    result["mae"] = float(np.mean(np.abs(errors)))

    if row_count >= 2:
        std_pred = np.std(y_pred, ddof=0)
        std_true = np.std(y_true, ddof=0)
        if std_pred > 0 and std_true > 0:
            result["prediction_label_correlation"] = float(np.corrcoef(y_pred, y_true)[0, 1])

    return result


def write_torch_artifacts(
    output_dir: Path,
    *,
    model_pack: dict,
    predictions: pd.DataFrame,
    metrics: dict,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    train_config: dict,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    predictions_path = output_dir / "predictions.csv"
    predictions.to_csv(predictions_path, index=False)

    metrics_path = output_dir / "metrics.json"
    metrics_full = {
        **metrics,
        "train_row_count": model_pack["train_row_count"],
        "test_row_count": int(len(test_df)),
    }
    with open(metrics_path, "w") as f:
        json.dump(metrics_full, f, indent=2, default=str)

    history = model_pack.get("history", [])
    history_path = output_dir / "training_history.csv"
    pd.DataFrame(history).to_csv(history_path, index=False)

    fi_rows = [
        {"feature": f, "importance": None, "importance_type": "not_available_for_torch_mlp"}
        for f in model_pack["feature_cols"]
    ]
    fi_df = pd.DataFrame(fi_rows)
    fi_path = output_dir / "feature_importance.csv"
    fi_df.to_csv(fi_path, index=False)

    summary = {
        "model_name": model_pack["model_name"],
        "model_type": model_pack["model_name"],
        "feature_cols": model_pack["feature_cols"],
        "label_col": model_pack["label_col"],
        "train_end": train_config.get("train_end", None),
        "train_row_count": model_pack["train_row_count"],
        "test_row_count": int(len(test_df)),
        "hidden_dim": model_pack["hidden_dim"],
        "dropout": model_pack["dropout"],
        "epochs": model_pack["epochs"],
        "batch_size": model_pack["batch_size"],
        "learning_rate": model_pack["learning_rate"],
        "weight_decay": model_pack["weight_decay"],
        "seed": model_pack["seed"],
        "torch_required": True,
    }
    summary_path = output_dir / "model_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    config_path = output_dir / "train_config.json"
    with open(config_path, "w") as f:
        json.dump(train_config, f, indent=2, default=str)

    return {
        "predictions": predictions_path,
        "metrics": metrics_path,
        "training_history": history_path,
        "feature_importance": fi_path,
        "model_summary": summary_path,
        "train_config": config_path,
    }


def run_torch_mlp(
    panel_df: pd.DataFrame,
    *,
    output_dir: Path,
    label_col: str = "ret_fwd_1m",
    train_end: str,
    feature_cols: list[str] | None = None,
    asset_id_col: str = "asset_id",
    date_col: str = "date",
    hidden_dim: int = 64,
    dropout: float = 0.2,
    epochs: int = 20,
    batch_size: int = 32,
    learning_rate: float = 0.001,
    weight_decay: float = 0.0001,
    seed: int = 42,
) -> dict[str, Path]:
    _require_torch()

    if feature_cols is None:
        feature_cols = _infer_feature_cols(
            panel_df,
            asset_id_col=asset_id_col,
            date_col=date_col,
            label_col=label_col,
        )

    dataset = build_ml_dataset(
        panel_df,
        asset_id_col=asset_id_col,
        date_col=date_col,
        label_col=label_col,
        feature_cols=feature_cols,
        drop_missing_label=True,
        drop_missing_features=False,
    )

    if feature_cols is None or len(feature_cols) == 0:
        used_feature_cols = [
            c for c in dataset.columns
            if c not in (asset_id_col, date_col, label_col)
        ]
    else:
        used_feature_cols = feature_cols

    train_df, test_df = time_train_test_split(
        dataset,
        date_col=date_col,
        train_end=train_end,
    )

    model_pack = fit_torch_mlp(
        train_df,
        feature_cols=used_feature_cols,
        label_col=label_col,
        hidden_dim=hidden_dim,
        dropout=dropout,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        weight_decay=weight_decay,
        seed=seed,
    )

    predictions = predict_torch_mlp(
        model_pack,
        test_df,
        asset_id_col=asset_id_col,
        date_col=date_col,
    )

    metrics = evaluate_torch_predictions(
        predictions,
        label_col=label_col,
    )

    train_config = {
        "model_name": "torch_mlp_regressor",
        "label_col": label_col,
        "train_end": train_end,
        "feature_cols": used_feature_cols,
        "asset_id_col": asset_id_col,
        "date_col": date_col,
        "hidden_dim": hidden_dim,
        "dropout": dropout,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "weight_decay": weight_decay,
        "seed": seed,
    }

    return write_torch_artifacts(
        output_dir,
        model_pack=model_pack,
        predictions=predictions,
        metrics=metrics,
        train_df=train_df,
        test_df=test_df,
        train_config=train_config,
    )
