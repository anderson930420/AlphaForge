from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from alphaforge import oap_multifactor as mf
from alphaforge.custom_signal import V2_SIGNAL_COLUMNS


FIXTURES = Path(__file__).parent / "fixtures" / "oap_multifactor"


class TestConfigLoading:
    def test_load_equal_weight_yaml(self) -> None:
        config = mf.OAPMultiFactorConfig.from_yaml(FIXTURES / "equal_weight.yaml")
        assert config.signal_name == "oap_multifactor_score"
        assert config.date_col == "date"
        assert config.asset_id_col == "asset_id"
        assert len(config.features) == 3
        assert config.features[0].name == "Mom12m"
        assert config.features[0].weight == 1.0
        assert config.features[0].higher_is_better is True
        assert config.features[2].name == "Investment"
        assert config.features[2].higher_is_better is False
        assert config.long_quantile == 0.8
        assert config.short_quantile == 0.2
        assert config.gross_long_weight == 1.0
        assert config.gross_short_weight == -1.0
        assert config.missing_policy == "ignore_feature"
        assert config.normalization == "zscore_by_date"

    def test_missing_feature_raises(self) -> None:
        config = mf.OAPMultiFactorConfig(
            signal_name="test",
            features=[mf.FeatureSpec(name="NonExistent")],
        )
        df = pd.DataFrame({"asset_id": ["A"], "date": ["2024-01-31"]})
        with pytest.raises(ValueError, match="not found in feature panel"):
            mf.build_multifactor_signal(df, config)


class TestInputFormats:
    def test_csv_input(self, tmp_path: Path) -> None:
        csv_path = FIXTURES / "features.csv"
        config = mf.OAPMultiFactorConfig.from_yaml(FIXTURES / "equal_weight.yaml")
        df = mf.load_feature_panel(csv_path)
        assert "asset_id" in df.columns
        assert "date" in df.columns
        signal = mf.build_multifactor_signal(df, config)
        assert len(signal) > 0
        assert signal["signal_name"].iloc[0] == "oap_multifactor_score"

    def test_parquet_input(self, tmp_path: Path) -> None:
        parquet_path = FIXTURES / "features.parquet"
        config = mf.OAPMultiFactorConfig.from_yaml(FIXTURES / "equal_weight.yaml")
        df = mf.load_feature_panel(parquet_path)
        signal = mf.build_multifactor_signal(df, config)
        assert len(signal) > 0


class TestHigherIsBetterInversion:
    def test_invert_feature_in_score(self, tmp_path: Path) -> None:
        df = pd.DataFrame({
            "asset_id": ["A", "B", "C"],
            "date": ["2024-01-31"] * 3,
            "Mom12m": [1.0, 2.0, 3.0],
            "Investment": [1.0, 2.0, 3.0],
        })
        config_normal = mf.OAPMultiFactorConfig(
            signal_name="test",
            features=[mf.FeatureSpec(name="Investment", weight=1.0, higher_is_better=True)],
        )
        config_inverted = mf.OAPMultiFactorConfig(
            signal_name="test",
            features=[mf.FeatureSpec(name="Investment", weight=1.0, higher_is_better=False)],
        )
        sig_normal = mf.build_multifactor_signal(df.copy(), config_normal)
        sig_inverted = mf.build_multifactor_signal(df.copy(), config_inverted)

        normal_scores = sig_normal.set_index("asset_id")["score"]
        inverted_scores = sig_inverted.set_index("asset_id")["score"]
        assert (normal_scores["A"] < normal_scores["C"])
        assert (inverted_scores["A"] > inverted_scores["C"])


class TestZscoreNormalization:
    def test_zscore_by_date_not_global(self, tmp_path: Path) -> None:
        df = pd.DataFrame({
            "asset_id": ["A", "B", "C", "D"],
            "date": ["2024-01-31"] * 2 + ["2024-02-29"] * 2,
            "Mom12m": [1.0, 2.0, 100.0, 200.0],
        })
        config = mf.OAPMultiFactorConfig(
            signal_name="test",
            features=[mf.FeatureSpec(name="Mom12m", weight=1.0, higher_is_better=True)],
        )
        signal = mf.build_multifactor_signal(df, config)
        jan = signal[signal["datetime"] == pd.Timestamp("2024-01-31")].set_index("asset_id")
        feb = signal[signal["datetime"] == pd.Timestamp("2024-02-29")].set_index("asset_id")
        assert jan.loc["A", "score"] != jan.loc["B", "score"]
        assert feb.loc["C", "score"] != feb.loc["D", "score"]


class TestLongShortNeutral:
    def test_quantile_weights(self, tmp_path: Path) -> None:
        df = pd.DataFrame({
            "asset_id": list("ABCDE"),
            "date": ["2024-01-31"] * 5,
            "Mom12m": [1.0, 2.0, 3.0, 4.0, 5.0],
            "BM": [5.0, 4.0, 3.0, 2.0, 1.0],
        })
        config = mf.OAPMultiFactorConfig(
            signal_name="test",
            features=[mf.FeatureSpec(name="Mom12m", weight=1.0, higher_is_better=True)],
            long_quantile=0.8,
            short_quantile=0.2,
            gross_long_weight=1.0,
            gross_short_weight=-1.0,
        )
        signal = mf.build_multifactor_signal(df, config)
        long_assets = signal[signal["direction"] == 1]["symbol"].tolist()
        short_assets = signal[signal["direction"] == -1]["symbol"].tolist()
        neutral_assets = signal[signal["direction"] == 0]["symbol"].tolist()
        assert len(long_assets) == 1
        assert len(short_assets) == 1
        assert len(neutral_assets) == 3
        long_tw = signal.loc[signal["direction"] == 1, "target_weight"].sum()
        short_tw = signal.loc[signal["direction"] == -1, "target_weight"].sum()
        assert long_tw == pytest.approx(1.0)
        assert short_tw == pytest.approx(-1.0)


class TestMissingValues:
    def test_ignore_feature_missing_policy(self, tmp_path: Path) -> None:
        df = pd.DataFrame({
            "asset_id": list("ABC"),
            "date": ["2024-01-31"] * 3,
            "Mom12m": [1.0, None, 3.0],
            "BM": [None, 2.0, None],
        })
        config = mf.OAPMultiFactorConfig(
            signal_name="test",
            features=[
                mf.FeatureSpec(name="Mom12m", weight=1.0, higher_is_better=True),
                mf.FeatureSpec(name="BM", weight=1.0, higher_is_better=True),
            ],
            missing_policy="ignore_feature",
        )
        signal = mf.build_multifactor_signal(df, config)
        assert len(signal) == 3
        assert signal["direction"].isin([-1, 0, 1]).all()

    def test_all_missing_row_gets_neutral(self, tmp_path: Path) -> None:
        df = pd.DataFrame({
            "asset_id": list("ABC"),
            "date": ["2024-01-31"] * 3,
            "Mom12m": [1.0, None, 3.0],
            "BM": [None, None, None],
        })
        config = mf.OAPMultiFactorConfig(
            signal_name="test",
            features=[
                mf.FeatureSpec(name="Mom12m", weight=1.0, higher_is_better=True),
                mf.FeatureSpec(name="BM", weight=1.0, higher_is_better=True),
            ],
            missing_policy="ignore_feature",
        )
        signal = mf.build_multifactor_signal(df, config)
        b_row = signal[signal["symbol"] == "B"]
        assert len(b_row) == 1
        assert b_row["direction"].iloc[0] == 0
        assert b_row["target_weight"].iloc[0] == 0.0


class TestOutputSchema:
    def test_v02_schema(self, tmp_path: Path) -> None:
        df = pd.DataFrame({
            "asset_id": list("ABC"),
            "date": ["2024-01-31"] * 3,
            "Mom12m": [1.0, 2.0, 3.0],
        })
        config = mf.OAPMultiFactorConfig(
            signal_name="test_signal",
            features=[mf.FeatureSpec(name="Mom12m", weight=1.0, higher_is_better=True)],
        )
        signal = mf.build_multifactor_signal(df, config)
        for col in V2_SIGNAL_COLUMNS:
            assert col in signal.columns, f"Missing column: {col}"
        assert signal["direction"].isin([-1, 0, 1]).all()
        assert (signal["target_weight"].abs() <= 1.0).all()

    def test_asset_id_preserved(self, tmp_path: Path) -> None:
        df = pd.DataFrame({
            "asset_id": ["PERMNO_A", "PERMNO_B"],
            "date": ["2024-01-31"] * 2,
            "Mom12m": [1.0, 2.0],
        })
        config = mf.OAPMultiFactorConfig(
            signal_name="test",
            features=[mf.FeatureSpec(name="Mom12m", weight=1.0, higher_is_better=True)],
        )
        signal = mf.build_multifactor_signal(df, config)
        assert "asset_id" in signal.columns
        assert signal["asset_id"].iloc[0] == "PERMNO_A"


class TestCLI:
    def test_build_oap_multifactor_signal_cli(self, tmp_path: Path, monkeypatch, capsys) -> None:
        from alphaforge.cli import main

        output_path = tmp_path / "signal.csv"
        monkeypatch.setattr(
            "sys.argv",
            [
                "alphaforge",
                "build-oap-multifactor-signal",
                "--features",
                str(FIXTURES / "features.csv"),
                "--config",
                str(FIXTURES / "equal_weight.yaml"),
                "--output",
                str(output_path),
            ],
        )
        main()
        assert output_path.exists()
        signal = pd.read_csv(output_path)
        for col in V2_SIGNAL_COLUMNS:
            assert col in signal.columns, f"Missing column: {col}"
        assert "Wrote" in capsys.readouterr().out


class TestDeterminism:
    def test_rerun_produces_same_output(self, tmp_path: Path) -> None:
        df = pd.DataFrame({
            "asset_id": list("ABCDE"),
            "date": ["2024-01-31"] * 5,
            "Mom12m": [1.0, 2.0, 3.0, 4.0, 5.0],
            "BM": [5.0, 4.0, 3.0, 2.0, 1.0],
        })
        config = mf.OAPMultiFactorConfig(
            signal_name="test",
            features=[
                mf.FeatureSpec(name="Mom12m", weight=1.0, higher_is_better=True),
                mf.FeatureSpec(name="BM", weight=1.0, higher_is_better=True),
            ],
        )
        sig1 = mf.build_multifactor_signal(df.copy(), config)
        sig2 = mf.build_multifactor_signal(df.copy(), config)
        pd.testing.assert_frame_equal(sig1.sort_values(["datetime", "symbol"]).reset_index(drop=True),
                                      sig2.sort_values(["datetime", "symbol"]).reset_index(drop=True))
