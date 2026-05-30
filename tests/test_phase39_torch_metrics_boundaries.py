from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.metrics import compute_metrics
from alphaforge.ml_torch import _validate_torch_mlp_config, run_torch_mlp
from alphaforge.schemas import MetricReport
from alphaforge.scoring import UNDEFINED_ANNUALIZED_RETURN_SCORE_COMPONENT, score_metrics


FIXTURES = Path(__file__).parent / "fixtures" / "ml_baseline"


def _valid_torch_config_kwargs() -> dict:
    return {
        "feature_cols": ["Mom12m", "BM"],
        "hidden_dim": 8,
        "dropout": 0.2,
        "epochs": 2,
        "batch_size": 4,
        "learning_rate": 0.001,
        "weight_decay": 0.0001,
    }


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"feature_cols": []}, "At least one ML feature column is required"),
        ({"hidden_dim": 1}, "hidden_dim must be >= 2"),
        ({"dropout": -0.1}, "dropout must be in \\[0, 1\\)"),
        ({"dropout": 1.0}, "dropout must be in \\[0, 1\\)"),
        ({"epochs": 0}, "epochs must be >= 1"),
        ({"batch_size": 0}, "batch_size must be >= 1"),
        ({"learning_rate": 0.0}, "learning_rate must be > 0"),
        ({"weight_decay": -0.1}, "weight_decay must be >= 0"),
    ],
)
def test_validate_torch_mlp_config_rejects_invalid_values(override: dict, match: str) -> None:
    kwargs = _valid_torch_config_kwargs()
    kwargs.update(override)

    with pytest.raises(ValueError, match=match):
        _validate_torch_mlp_config(**kwargs)


def test_run_torch_mlp_validates_config_before_requiring_torch(tmp_path: Path) -> None:
    panel = pd.read_csv(FIXTURES / "supervised_panel.csv")

    with pytest.raises(ValueError, match="hidden_dim must be >= 2"):
        run_torch_mlp(
            panel,
            output_dir=tmp_path / "torch_out",
            label_col="ret_fwd_1m",
            train_end="2024-03-31",
            feature_cols=["Mom12m", "BM", "Investment"],
            hidden_dim=1,
            epochs=1,
            batch_size=4,
        )


def test_compute_metrics_reports_ok_annualized_return_status() -> None:
    equity_curve = pd.DataFrame(
        {
            "strategy_return": [0.0, 0.01],
            "equity": [100.0, 101.0],
            "turnover": [0.0, 1.0],
        }
    )
    trades = pd.DataFrame({"trade_net_return": [0.01]})

    metrics = compute_metrics(equity_curve, trades, annualization_factor=252)

    assert metrics.annualized_return is not None
    assert metrics.annualized_return_status == "ok"


def test_compute_metrics_marks_non_positive_ending_equity_annualized_return_undefined() -> None:
    equity_curve = pd.DataFrame(
        {
            "strategy_return": [0.0, -1.0],
            "equity": [100.0, 0.0],
            "turnover": [0.0, 1.0],
        }
    )
    trades = pd.DataFrame({"trade_net_return": [-1.0]})

    metrics = compute_metrics(equity_curve, trades, annualization_factor=252)

    assert metrics.total_return == -1.0
    assert metrics.annualized_return is None
    assert metrics.annualized_return_status == "undefined_non_positive_ending_equity"
    assert metrics.sharpe_ratio == 0.0
    assert metrics.max_drawdown == -1.0


def test_compute_metrics_marks_non_positive_initial_equity_without_division_error() -> None:
    equity_curve = pd.DataFrame(
        {
            "strategy_return": [0.0, 0.0],
            "equity": [0.0, 10.0],
            "turnover": [0.0, 1.0],
        }
    )
    trades = pd.DataFrame({"trade_net_return": [0.0]})

    metrics = compute_metrics(equity_curve, trades, annualization_factor=252)

    assert math.isnan(metrics.total_return)
    assert metrics.annualized_return is None
    assert metrics.annualized_return_status == "undefined_non_positive_initial_equity"


def test_score_metrics_penalizes_undefined_annualized_return_without_type_error() -> None:
    metrics = MetricReport(
        total_return=-1.0,
        annualized_return=None,
        annualized_return_status="undefined_non_positive_ending_equity",
        sharpe_ratio=0.0,
        max_drawdown=-1.0,
        win_rate=0.0,
        turnover=1.0,
        trade_count=1,
        bar_count=2,
    )

    expected = UNDEFINED_ANNUALIZED_RETURN_SCORE_COMPONENT - 2.0 - 0.005

    assert score_metrics(metrics) == expected
