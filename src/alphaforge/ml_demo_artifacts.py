from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from alphaforge.ml_diagnostics import (
    run_ml_prediction_diagnostics,
    write_ml_prediction_diagnostics,
)


DEFAULT_MONTHS = 12
DEFAULT_ASSETS = 20


def build_synthetic_prediction_demo(
    *,
    months: int = DEFAULT_MONTHS,
    assets: int = DEFAULT_ASSETS,
    start: str = "2020-01-31",
) -> pd.DataFrame:
    """Build a deterministic synthetic prediction panel for dashboard/demo smoke.

    The data is intentionally artificial. It creates enough cross-sectional
    dispersion per date for IC, Rank IC, quantile returns, and long-short spread
    diagnostics to be non-empty and visually inspectable. The deterministic
    month-varying noise avoids a degenerate demo where every monthly IC is
    exactly identical.
    """
    if months < 1:
        raise ValueError("months must be at least 1")
    if assets < 2:
        raise ValueError("assets must be at least 2")

    dates = pd.date_range(pd.Timestamp(start), periods=months, freq="ME")
    center = (assets - 1) / 2
    rows = []

    for month_index, date in enumerate(dates):
        market_component = ((month_index % 4) - 1.5) * 0.0015
        regime_component = 0.0004 * ((month_index % 3) - 1)
        month_noise_scale = 0.00025 + 0.00008 * (month_index % 5)
        for asset_index in range(assets):
            asset_id = f"SYN{asset_index + 1:03d}"
            cross_sectional_rank = (asset_index - center) / assets
            base_noise = ((asset_index % 5) - 2) * 0.00035
            rotating_noise = (((asset_index * (month_index + 3)) % 7) - 3) * month_noise_scale
            predicted_return = 0.008 + 0.020 * cross_sectional_rank + market_component
            realized_forward_return = (
                0.006
                + 0.015 * cross_sectional_rank
                + 0.45 * market_component
                + regime_component
                + base_noise
                + rotating_noise
            )
            rows.append({
                "asset_id": asset_id,
                "date": date.strftime("%Y-%m-%d"),
                "predicted_return": predicted_return,
                "ret_fwd_1m": realized_forward_return,
                "source": "synthetic_prediction_demo",
            })

    return pd.DataFrame(rows)


def write_synthetic_prediction_demo_artifacts(
    output_dir: Path | str,
    *,
    months: int = DEFAULT_MONTHS,
    assets: int = DEFAULT_ASSETS,
    quantiles: int = 5,
) -> dict[str, str | dict[str, object]]:
    """Write synthetic predictions and Phase 30 diagnostics artifacts."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    predictions = build_synthetic_prediction_demo(months=months, assets=assets)
    predictions_path = output_dir / "predictions.csv"
    predictions.to_csv(predictions_path, index=False)

    diagnostics_dir = output_dir / "ml_prediction_diagnostics"
    result = run_ml_prediction_diagnostics(predictions, quantiles=quantiles)
    diagnostics_paths = write_ml_prediction_diagnostics(result, diagnostics_dir)

    summary = {
        "status": "ok",
        "months": months,
        "assets": assets,
        "prediction_rows": int(len(predictions)),
        "quantiles": quantiles,
        "predictions_path": str(predictions_path),
        "diagnostics_dir": str(diagnostics_dir),
        "diagnostics_summary": result.summary,
    }
    summary_path = output_dir / "synthetic_prediction_demo_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    return {
        "predictions": str(predictions_path),
        "summary": str(summary_path),
        "diagnostics_dir": str(diagnostics_dir),
        "diagnostics_paths": diagnostics_paths,
    }
