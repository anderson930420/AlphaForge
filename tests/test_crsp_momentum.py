from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from alphaforge.crsp_momentum import (
    build_momentum_portfolio_returns,
    compute_mom12_1,
    summarize_momentum_returns,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_crsp_mom12m_baseline.py"


def _make_asset_rows(
    asset_id: str,
    permno: int,
    ticker: str,
    returns: list[float | None],
    *,
    common: bool = True,
    primary: bool = True,
    market_cap_start: float = 1000.0,
    price_start: float = 10.0,
) -> list[dict[str, object]]:
    dates = pd.date_range("2020-01-31", periods=len(returns), freq="ME")
    rows: list[dict[str, object]] = []
    for index, (date_value, total_ret) in enumerate(zip(dates, returns)):
        market_cap = market_cap_start + (index * 100.0)
        rows.append(
            {
                "date": date_value,
                "asset_id": asset_id,
                "permno": permno,
                "permco": permno + 10000,
                "ticker": ticker,
                "cusip": f"{permno:08d}",
                "ncusip": f"{permno:08d}",
                "exchcd": 1,
                "shrcd": 10,
                "siccd": 1234,
                "price": price_start + index,
                "ret": total_ret,
                "retx": total_ret,
                "dlret": None,
                "volume": 1000.0 + index,
                "shares_out": 100.0,
                "market_cap": market_cap,
                "lag_market_cap": market_cap - 10.0,
                "total_ret": total_ret,
                "is_common_share": common,
                "is_primary_us_exchange": primary,
                "daily_obs_count": 20,
                "first_trading_date": "2010-01-31",
                "last_trading_date": date_value,
            }
        )
    return rows


def _canonical_panel() -> pd.DataFrame:
    b_returns = [0.01] * 11 + [0.50, 0.01, 0.10, 0.03, 0.05]
    c_returns = [0.02] * 11 + [0.50, 0.02, 0.20, 0.04, 0.06]
    a_returns = [0.03] * 15
    rows = []
    rows.extend(_make_asset_rows("A", 10001, "AAA", a_returns, common=False, primary=False, market_cap_start=500.0))
    rows.extend(_make_asset_rows("B", 10002, "BBB", b_returns, common=True, primary=True, market_cap_start=1000.0))
    rows.extend(_make_asset_rows("C", 10003, "CCC", c_returns, common=True, primary=True, market_cap_start=3000.0))
    return pd.DataFrame(rows)


class TestComputeMom12_1:
    def test_compounds_t_minus_12_through_t_minus_2_and_skips_t_minus_1(self) -> None:
        panel = pd.DataFrame(
            _make_asset_rows(
                "A",
                10001,
                "AAA",
                [0.01] * 11 + [0.50, 0.02],
            )
        )

        result = compute_mom12_1(panel)

        assert result.columns.tolist() == [
            "date",
            "asset_id",
            "permno",
            "ticker",
            "total_ret",
            "market_cap",
            "lag_market_cap",
            "mom12_1",
        ]
        target = result.loc[result["date"] == pd.Timestamp("2021-01-31"), "mom12_1"].iloc[0]
        assert target == pytest.approx((1.01 ** 11) - 1.0)

    def test_does_not_look_ahead(self) -> None:
        base_panel = pd.DataFrame(
            _make_asset_rows(
                "A",
                10001,
                "AAA",
                [0.01] * 11 + [0.50, 0.02],
            )
        )
        future_shifted_panel = pd.DataFrame(
            _make_asset_rows(
                "A",
                10001,
                "AAA",
                [0.01] * 11 + [0.50, 0.99],
            )
        )

        base_result = compute_mom12_1(base_panel)
        shifted_result = compute_mom12_1(future_shifted_panel)

        base_value = base_result.loc[base_result["date"] == pd.Timestamp("2021-01-31"), "mom12_1"].iloc[0]
        shifted_value = shifted_result.loc[shifted_result["date"] == pd.Timestamp("2021-01-31"), "mom12_1"].iloc[0]
        assert shifted_value == pytest.approx(base_value)

    def test_min_obs_threshold_controls_nan_output(self) -> None:
        panel = pd.DataFrame(
            _make_asset_rows(
                "A",
                10001,
                "AAA",
                [0.01] * 8 + [None, None, None, 0.50, 0.02],
            )
        )

        low_threshold = compute_mom12_1(panel, min_obs=8)
        high_threshold = compute_mom12_1(panel, min_obs=9)

        target_low = low_threshold.loc[low_threshold["date"] == pd.Timestamp("2021-01-31"), "mom12_1"].iloc[0]
        target_high = high_threshold.loc[high_threshold["date"] == pd.Timestamp("2021-01-31"), "mom12_1"].iloc[0]

        assert target_low == pytest.approx((1.01 ** 8) - 1.0)
        assert pd.isna(target_high)


class TestMomentumPortfolioReturns:
    def test_forward_return_alignment_and_equal_weight_long_short(self) -> None:
        panel = _canonical_panel().loc[:, [
            "date",
            "asset_id",
            "permno",
            "ticker",
            "total_ret",
            "market_cap",
            "lag_market_cap",
        ]]

        signal_panel = compute_mom12_1(panel, min_obs=8)
        signal_panel["forward_1m_total_ret"] = signal_panel.groupby("asset_id", sort=False)["total_ret"].shift(-1)
        signal_panel = signal_panel.loc[signal_panel["asset_id"].isin(["B", "C"])].reset_index(drop=True)
        signal_panel = signal_panel.loc[
            (signal_panel["date"] >= pd.Timestamp("2021-01-31"))
            & (signal_panel["date"] <= pd.Timestamp("2021-02-28"))
        ].reset_index(drop=True)

        portfolio_returns = build_momentum_portfolio_returns(
            signal_panel,
            quantile=0.5,
            weighting="equal",
        )

        assert portfolio_returns.columns.tolist() == [
            "date",
            "long_ret",
            "short_ret",
            "long_short_ret",
            "long_count",
            "short_count",
            "weighting",
            "quantile",
        ]
        assert portfolio_returns["date"].tolist() == [pd.Timestamp("2021-01-31"), pd.Timestamp("2021-02-28")]

        first_row = portfolio_returns.iloc[0]
        second_row = portfolio_returns.iloc[1]
        assert first_row["long_ret"] == pytest.approx(0.20)
        assert first_row["short_ret"] == pytest.approx(0.10)
        assert first_row["long_short_ret"] == pytest.approx(0.10)
        assert first_row["long_count"] == 1
        assert first_row["short_count"] == 1

        assert second_row["long_ret"] == pytest.approx(0.04)
        assert second_row["short_ret"] == pytest.approx(0.03)
        assert second_row["long_short_ret"] == pytest.approx(0.01)
        assert second_row["long_count"] == 1
        assert second_row["short_count"] == 1

    def test_value_weighting_uses_lag_market_cap(self) -> None:
        panel = pd.DataFrame(
            {
                "date": [pd.Timestamp("2021-01-31")] * 4,
                "asset_id": ["A", "B", "C", "D"],
                "mom12_1": [0.1, 0.2, 0.3, 0.4],
                "forward_1m_total_ret": [0.01, 0.02, 0.03, 0.04],
                "lag_market_cap": [100.0, 200.0, 300.0, 700.0],
            }
        )

        portfolio_returns = build_momentum_portfolio_returns(
            panel,
            quantile=0.5,
            weighting="value",
        )

        assert len(portfolio_returns) == 1
        row = portfolio_returns.iloc[0]
        assert row["long_ret"] == pytest.approx((0.03 * 300.0 + 0.04 * 700.0) / 1000.0)
        assert row["short_ret"] == pytest.approx((0.01 * 100.0 + 0.02 * 200.0) / 300.0)
        assert row["long_short_ret"] == pytest.approx(row["long_ret"] - row["short_ret"])
        assert row["long_count"] == 2
        assert row["short_count"] == 2


class TestMomentumSummary:
    def test_summary_metrics_are_deterministic(self) -> None:
        portfolio_returns = pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-01-31"), pd.Timestamp("2024-02-29")],
                "long_short_ret": [0.10, 0.05],
            }
        )

        summary = summarize_momentum_returns(portfolio_returns)

        cumulative_factor = (1.10 * 1.05)
        expected_std = pd.Series([0.10, 0.05]).std(ddof=1)
        expected_annualized_return = cumulative_factor ** (12.0 / 2.0) - 1.0
        expected_annualized_volatility = expected_std * (12.0 ** 0.5)

        assert summary["rows"] == 2
        assert summary["date_min"] == "2024-01-31"
        assert summary["date_max"] == "2024-02-29"
        assert summary["cumulative_return"] == pytest.approx(cumulative_factor - 1.0)
        assert summary["annualized_return"] == pytest.approx(expected_annualized_return)
        assert summary["annualized_volatility"] == pytest.approx(expected_annualized_volatility)
        assert summary["sharpe"] == pytest.approx(expected_annualized_return / expected_annualized_volatility)
        assert summary["mean_monthly_return"] == pytest.approx(0.075)
        assert summary["std_monthly_return"] == pytest.approx(expected_std)
        assert summary["positive_month_ratio"] == pytest.approx(1.0)
        assert summary["worst_month"] == pytest.approx(0.05)
        assert summary["best_month"] == pytest.approx(0.10)


def test_cli_smoke_writes_expected_artifacts(tmp_path: Path) -> None:
    input_path = tmp_path / "crsp_monthly.parquet"
    output_dir = tmp_path / "mom12m_out"
    _canonical_panel().to_parquet(input_path, index=False)

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(input_path),
            "--output-dir",
            str(output_dir),
            "--start-date",
            "2021-01-31",
            "--end-date",
            "2021-02-28",
            "--quantile",
            "0.5",
            "--min-obs",
            "8",
            "--weighting",
            "equal",
            "--common-shares-only",
            "--primary-exchange-only",
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr

    signal_panel_path = output_dir / "momentum_signal_panel.parquet"
    portfolio_returns_path = output_dir / "momentum_portfolio_returns.parquet"
    summary_path = output_dir / "momentum_summary.json"

    assert signal_panel_path.exists()
    assert portfolio_returns_path.exists()
    assert summary_path.exists()

    stdout_summary = json.loads(result.stdout)
    file_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert stdout_summary == file_summary
    assert stdout_summary["status"] == "ok"
    assert stdout_summary["signal_panel_rows"] == 4
    assert stdout_summary["portfolio_rows"] == 2
    assert stdout_summary["rows"] == 2
    assert stdout_summary["weighting"] == "equal"
    assert stdout_summary["quantile"] == 0.5
    assert stdout_summary["date_min"] == "2021-01-31"
    assert stdout_summary["date_max"] == "2021-02-28"

    signal_panel = pd.read_parquet(signal_panel_path)
    assert signal_panel.columns.tolist() == [
        "date",
        "asset_id",
        "permno",
        "ticker",
        "total_ret",
        "market_cap",
        "lag_market_cap",
        "mom12_1",
        "forward_1m_total_ret",
    ]
    assert len(signal_panel) == 4
    assert signal_panel.loc[
        (signal_panel["date"] == pd.Timestamp("2021-01-31")) & (signal_panel["asset_id"] == "B"),
        "forward_1m_total_ret",
    ].iloc[0] == pytest.approx(0.10)
    assert signal_panel.loc[
        (signal_panel["date"] == pd.Timestamp("2021-01-31")) & (signal_panel["asset_id"] == "C"),
        "forward_1m_total_ret",
    ].iloc[0] == pytest.approx(0.20)

    portfolio_returns = pd.read_parquet(portfolio_returns_path)
    assert portfolio_returns["date"].tolist() == [pd.Timestamp("2021-01-31"), pd.Timestamp("2021-02-28")]
    assert portfolio_returns["long_short_ret"].tolist() == pytest.approx([0.10, 0.01])
