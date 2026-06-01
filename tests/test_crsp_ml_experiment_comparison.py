from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from alphaforge.crsp_ml_experiment_comparison import (
    build_crsp_ml_experiment_comparison,
    build_crsp_ml_experiment_comparison_payload,
    build_interpretation,
    build_ranking_summary,
    load_ml_experiment,
    load_mom12m_benchmark,
    parse_experiment_arg,
    render_crsp_ml_experiment_comparison_markdown,
    write_crsp_ml_experiment_comparison,
)


def test_parse_experiment_arg() -> None:
    name, path = parse_experiment_arg("raw_ridge=artifacts/raw")

    assert name == "raw_ridge"
    assert path == Path("artifacts/raw")


def test_parse_experiment_arg_rejects_invalid_value() -> None:
    try:
        parse_experiment_arg("raw_ridge")
    except ValueError as exc:
        assert "NAME=DIR" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError")


def test_load_one_ml_experiment_summary(tmp_path: Path) -> None:
    experiment_dir = _write_ml_experiment(
        tmp_path,
        "raw_ridge",
        rank_ic=-0.02,
        cumulative_return=-0.2,
    )

    experiment = load_ml_experiment("raw_ridge", experiment_dir)

    assert experiment["name"] == "raw_ridge"
    assert experiment["kind"] == "ml"
    assert experiment["model"] == "ridge"
    assert experiment["feature_set"] == "raw"
    assert experiment["average_prediction_rank_ic"] == -0.02
    assert experiment["cumulative_return"] == -0.2
    assert experiment["portfolio_rows"] == 3


def test_load_multiple_ml_experiment_summaries(tmp_path: Path) -> None:
    raw_dir = _write_ml_experiment(tmp_path, "raw_ridge", rank_ic=-0.01, cumulative_return=-0.3)
    xrank_dir = _write_ml_experiment(tmp_path, "xrank_ridge", rank_ic=0.02, cumulative_return=-0.1)

    comparison = build_crsp_ml_experiment_comparison(
        [("raw_ridge", raw_dir), ("xrank_ridge", xrank_dir)]
    )

    assert comparison["experiment_count"] == 2
    assert comparison["ranking"]["best_by_rank_ic"] == "xrank_ridge"
    assert comparison["ranking"]["best_ml_by_cumulative_return"] == "xrank_ridge"


def test_load_optional_mom12m_benchmark(tmp_path: Path) -> None:
    mom_dir = _write_mom12m_benchmark(tmp_path, cumulative_return=0.05)

    benchmark = load_mom12m_benchmark(mom_dir)

    assert benchmark["name"] == "mom12m"
    assert benchmark["kind"] == "benchmark"
    assert benchmark["cumulative_return"] == 0.05
    assert benchmark["portfolio_rows"] == 3


def test_missing_optional_benchmark_still_works(tmp_path: Path) -> None:
    raw_dir = _write_ml_experiment(tmp_path, "raw_ridge", rank_ic=0.01, cumulative_return=0.01)

    comparison = build_crsp_ml_experiment_comparison([("raw_ridge", raw_dir)])

    assert comparison["benchmark"] is None
    assert comparison["ranking"]["best_by_rank_ic"] == "raw_ridge"


def test_comparison_json_payload_schema_is_stable() -> None:
    payload = build_crsp_ml_experiment_comparison_payload(
        [
            {
                "name": "raw_ridge",
                "kind": "ml",
                "model": "ridge",
                "feature_set": "raw",
                "average_prediction_ic": 0.001,
                "average_prediction_rank_ic": -0.01,
                "cumulative_return": -0.2,
                "annualized_return": None,
                "annualized_volatility": None,
                "sharpe": None,
                "max_drawdown": -0.3,
                "portfolio_rows": 12,
                "date_min": "2006-01-31",
                "date_max": "2006-12-31",
                "source_dir": "artifacts/raw",
            }
        ],
        output_dir="artifacts/comparison",
    )

    assert list(payload.keys()) == [
        "report_type",
        "title",
        "generated_at",
        "experiment_count",
        "experiments",
        "benchmark",
        "ranking",
        "interpretation",
        "limitations",
        "next_steps",
        "output_paths",
    ]
    assert payload["report_type"] == "crsp_ml_experiment_comparison"
    assert payload["output_paths"]["comparison_json"] == "artifacts/comparison/comparison.json"


def test_markdown_report_renders_key_sections() -> None:
    payload = build_crsp_ml_experiment_comparison_payload(
        [
            {
                "name": "raw_ridge",
                "kind": "ml",
                "model": "ridge",
                "feature_set": "raw",
                "average_prediction_ic": 0.001,
                "average_prediction_rank_ic": -0.01,
                "cumulative_return": -0.2,
            }
        ]
    )

    markdown = render_crsp_ml_experiment_comparison_markdown(payload)

    assert "# CRSP ML Experiment Comparison" in markdown
    assert "## Experiments Compared" in markdown
    assert "## Benchmark" in markdown
    assert "## Research Interpretation" in markdown
    assert "| raw_ridge | raw | ridge |" in markdown


def test_ranking_logic_includes_benchmark_for_cumulative_return() -> None:
    ranking = build_ranking_summary(
        [
            {"name": "raw_ridge", "average_prediction_rank_ic": -0.01, "cumulative_return": -0.2},
            {"name": "xrank_ridge", "average_prediction_rank_ic": 0.02, "cumulative_return": -0.1},
        ],
        benchmark={"name": "mom12m", "cumulative_return": 0.05},
    )

    assert ranking["best_by_rank_ic"] == "xrank_ridge"
    assert ranking["best_ml_by_cumulative_return"] == "xrank_ridge"
    assert ranking["best_by_cumulative_return"] == "mom12m"


def test_interpretation_logic_for_raw_vs_xrank_improvement() -> None:
    interpretation = build_interpretation(
        [
            {
                "name": "raw_ridge",
                "feature_set": "raw",
                "average_prediction_rank_ic": -0.02,
                "cumulative_return": -0.3,
            },
            {
                "name": "xrank_ridge",
                "feature_set": "xrank",
                "average_prediction_rank_ic": 0.01,
                "cumulative_return": -0.1,
            },
        ],
        benchmark={"name": "mom12m", "cumulative_return": 0.05},
        ranking={"best_by_rank_ic": "xrank_ridge", "best_by_cumulative_return": "mom12m"},
    )

    joined = "\n".join(interpretation)
    assert "rank preprocessing improved prediction Rank IC" in joined
    assert "did not outperform the Mom12m benchmark" in joined
    assert "not strong enough to claim robust alpha" in joined


def test_write_comparison_artifacts(tmp_path: Path) -> None:
    raw_dir = _write_ml_experiment(tmp_path, "raw_ridge", rank_ic=-0.02, cumulative_return=-0.3)
    xrank_dir = _write_ml_experiment(tmp_path, "xrank_ridge", rank_ic=0.01, cumulative_return=-0.1)
    mom_dir = _write_mom12m_benchmark(tmp_path, cumulative_return=0.05)
    output_dir = tmp_path / "comparison"

    write_crsp_ml_experiment_comparison(
        [("raw_ridge", raw_dir), ("xrank_ridge", xrank_dir)],
        mom12m_dir=mom_dir,
        output_dir=output_dir,
    )

    payload = json.loads((output_dir / "comparison.json").read_text(encoding="utf-8"))
    markdown = (output_dir / "comparison.md").read_text(encoding="utf-8")
    assert payload["ranking"]["best_by_cumulative_return"] == "mom12m"
    assert "Mom12m" in markdown or "mom12m" in markdown


def test_cli_smoke_writes_comparison_json_and_md(tmp_path: Path) -> None:
    raw_dir = _write_ml_experiment(tmp_path, "raw_ridge", rank_ic=-0.02, cumulative_return=-0.3)
    xrank_dir = _write_ml_experiment(tmp_path, "xrank_ridge", rank_ic=0.01, cumulative_return=-0.1)
    mom_dir = _write_mom12m_benchmark(tmp_path, cumulative_return=0.05)
    output_dir = tmp_path / "comparison"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_crsp_ml_experiment_comparison.py",
            "--experiment",
            f"raw_ridge={raw_dir}",
            "--experiment",
            f"xrank_ridge={xrank_dir}",
            "--mom12m-dir",
            str(mom_dir),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        cwd=Path.cwd(),
        env={"PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )

    assert "crsp_ml_experiment_comparison" in result.stdout
    assert (output_dir / "comparison.json").exists()
    assert (output_dir / "comparison.md").exists()


def _write_ml_experiment(
    tmp_path: Path,
    name: str,
    *,
    rank_ic: float,
    cumulative_return: float,
) -> Path:
    experiment_dir = tmp_path / name
    experiment_dir.mkdir(parents=True)
    feature_cols = ["mom12_1", "mom6_1"]
    if "xrank" in name:
        feature_cols = ["mom12_1_xrank", "mom6_1_xrank"]
    summary = {
        "model_name": "ridge",
        "feature_cols": feature_cols,
        "average_prediction_ic": rank_ic / 2,
        "average_prediction_rank_ic": rank_ic,
        "cumulative_return": cumulative_return,
        "annualized_return": cumulative_return / 3,
        "annualized_volatility": 0.1,
        "sharpe": cumulative_return,
        "max_drawdown": min(cumulative_return, 0.0),
        "portfolio_rows": 3,
        "date_min": "2006-01-31",
        "date_max": "2006-03-31",
    }
    (experiment_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2006-01-31", "2006-02-28", "2006-03-31"]),
            "long_short_ret": [0.01, -0.02, cumulative_return],
        }
    ).to_parquet(experiment_dir / "prediction_portfolio_returns.parquet", index=False)
    return experiment_dir


def _write_mom12m_benchmark(tmp_path: Path, *, cumulative_return: float) -> Path:
    benchmark_dir = tmp_path / "mom12m"
    benchmark_dir.mkdir(parents=True)
    summary = {
        "cumulative_return": cumulative_return,
        "annualized_return": cumulative_return / 3,
        "annualized_volatility": 0.1,
        "sharpe": cumulative_return,
        "max_drawdown": -0.02,
        "portfolio_rows": 3,
        "date_min": "2006-01-31",
        "date_max": "2006-03-31",
    }
    (benchmark_dir / "momentum_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2006-01-31", "2006-02-28", "2006-03-31"]),
            "long_short_ret": [0.01, 0.02, cumulative_return],
        }
    ).to_parquet(benchmark_dir / "momentum_portfolio_returns.parquet", index=False)
    return benchmark_dir
