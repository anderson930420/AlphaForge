from __future__ import annotations

import pandas as pd
import pytest

from alphaforge.cli import main
from alphaforge.open_asset_pricing import OAP_SIGNAL_COLUMNS


def test_build_oap_signal_cli_writes_v02_signal_csv(tmp_path, monkeypatch, capsys) -> None:
    input_path = tmp_path / "oap.csv"
    output_path = tmp_path / "signal.csv"
    pd.DataFrame(
        {
            "date": ["2024-01-31"] * 5,
            "permno": ["A", "B", "C", "D", "E"],
            "BM": [1.0, 2.0, 3.0, 4.0, 5.0],
        }
    ).to_csv(input_path, index=False)

    monkeypatch.setattr(
        "sys.argv",
        [
            "alphaforge",
            "build-oap-signal",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--characteristic",
            "BM",
            "--asset-id-col",
            "permno",
        ],
    )

    main()

    output = pd.read_csv(output_path)
    assert output.columns.tolist() == list(OAP_SIGNAL_COLUMNS)
    assert output.shape[0] == 5
    assert output.set_index("symbol").loc["A", "direction"] == -1
    assert output.set_index("symbol").loc["E", "direction"] == 1
    assert "Wrote 5 v0.2 signal rows" in capsys.readouterr().out


def test_build_oap_signal_cli_supports_policy_arguments(tmp_path, monkeypatch) -> None:
    input_path = tmp_path / "oap.csv"
    output_path = tmp_path / "signal.csv"
    pd.DataFrame(
        {
            "date": ["2024-01-31"] * 5,
            "permno": ["A", "B", "C", "D", "E"],
            "BM": [1.0, 2.0, 3.0, 4.0, 5.0],
        }
    ).to_csv(input_path, index=False)

    monkeypatch.setattr(
        "sys.argv",
        [
            "alphaforge",
            "build-oap-signal",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--characteristic",
            "BM",
            "--asset-id-col",
            "permno",
            "--long-quantile",
            "0.6",
            "--short-quantile",
            "0.4",
            "--gross-long-weight",
            "0.5",
            "--gross-short-weight",
            "-0.5",
            "--invert-score",
            "--signal-name",
            "oap_bm_inverted",
            "--source",
            "test-oap",
        ],
    )

    main()

    output = pd.read_csv(output_path)
    assert output["signal_name"].unique().tolist() == ["oap_bm_inverted"]
    assert output["source"].unique().tolist() == ["test-oap"]
    assert output.loc[output["direction"].eq(1), "target_weight"].sum() == pytest.approx(0.5)
    assert output.loc[output["direction"].eq(-1), "target_weight"].sum() == pytest.approx(-0.5)
    assert output.set_index("symbol").loc["A", "direction"] == 1
    assert output.set_index("symbol").loc["E", "direction"] == -1
