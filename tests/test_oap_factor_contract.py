from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from alphaforge.oap_factor_contract import (
    OAPFactorContract,
    OAPFactorContractError,
    load_oap_factor_contract,
    validate_oap_factor_contract,
)


FIXTURE = Path("tests/fixtures/oap_factor_contracts/mom12m_threshold.yaml")


def test_load_valid_mom12m_threshold_contract() -> None:
    contract = load_oap_factor_contract(FIXTURE)

    assert contract.version == "alphaforge_oap_factor_contract_v0.1"
    assert contract.dataset["name"] == "open_asset_pricing"
    assert contract.dataset["provider"] == "jkp"
    assert contract.factor["name"] == "Mom12m"
    assert contract.factor["raw_column"] == "Mom12m"
    assert contract.factor["value_column"] == "factor_value"
    assert contract.factor["higher_is_better"] is True
    assert contract.decision_rule == {
        "type": "threshold",
        "long_threshold": 0.0,
        "short_threshold": 0.0,
        "long_when": "greater_than",
        "short_when": "less_than",
    }
    assert contract.weighting == {
        "target_weight_mode": "signed_unit",
        "long_weight": 1.0,
        "short_weight": -1.0,
        "neutral_weight": 0.0,
    }
    assert contract.timing["available_at_policy"] == "next_month"
    assert contract.timing["rebalance_frequency"] == "monthly"
    assert contract.output["schema"] == "signal_csv_v0.2"


def test_rejects_missing_required_section() -> None:
    valid = load_oap_factor_contract(FIXTURE)
    invalid = OAPFactorContract(
        version=valid.version,
        dataset=valid.dataset,
        factor=valid.factor,
        decision_rule=valid.decision_rule,
        weighting=valid.weighting,
        timing=valid.timing,
        identity=valid.identity,
        validation=valid.validation,
        output=None,  # type: ignore[arg-type]
    )

    with pytest.raises(OAPFactorContractError, match="output.*mapping"):
        validate_oap_factor_contract(invalid)


def test_rejects_unsupported_decision_rule_type() -> None:
    valid = load_oap_factor_contract(FIXTURE)
    invalid = replace(valid, decision_rule={**valid.decision_rule, "type": "cross_sectional_rank"})

    with pytest.raises(OAPFactorContractError, match="Unsupported decision_rule.type"):
        validate_oap_factor_contract(invalid)


def test_rejects_unsupported_weighting_mode() -> None:
    valid = load_oap_factor_contract(FIXTURE)
    invalid = replace(valid, weighting={**valid.weighting, "target_weight_mode": "gross_normalized"})

    with pytest.raises(OAPFactorContractError, match="Unsupported weighting.target_weight_mode"):
        validate_oap_factor_contract(invalid)


def test_rejects_unsupported_available_at_policy() -> None:
    valid = load_oap_factor_contract(FIXTURE)
    invalid = replace(valid, timing={**valid.timing, "available_at_policy": "same_day"})

    with pytest.raises(OAPFactorContractError, match="Unsupported timing.available_at_policy"):
        validate_oap_factor_contract(invalid)


def test_rejects_invalid_threshold_direction() -> None:
    valid = load_oap_factor_contract(FIXTURE)
    invalid_long = replace(valid, decision_rule={**valid.decision_rule, "long_when": "greater_or_equal"})
    invalid_short = replace(valid, decision_rule={**valid.decision_rule, "short_when": "less_or_equal"})

    with pytest.raises(OAPFactorContractError, match="long_when"):
        validate_oap_factor_contract(invalid_long)
    with pytest.raises(OAPFactorContractError, match="short_when"):
        validate_oap_factor_contract(invalid_short)


def test_rejects_invalid_signed_unit_weights() -> None:
    valid = load_oap_factor_contract(FIXTURE)
    cases = [
        ({**valid.weighting, "long_weight": 0.0}, "long_weight"),
        ({**valid.weighting, "long_weight": 1.5}, "long_weight"),
        ({**valid.weighting, "short_weight": 0.0}, "short_weight"),
        ({**valid.weighting, "short_weight": -1.5}, "short_weight"),
        ({**valid.weighting, "neutral_weight": 0.25}, "neutral_weight"),
    ]

    for weighting, message in cases:
        with pytest.raises(OAPFactorContractError, match=message):
            validate_oap_factor_contract(replace(valid, weighting=weighting))


def test_rejects_wrong_output_schema() -> None:
    valid = load_oap_factor_contract(FIXTURE)
    invalid = replace(valid, output={**valid.output, "schema": "signal_csv_v0.3"})

    with pytest.raises(OAPFactorContractError, match="Unsupported output.schema"):
        validate_oap_factor_contract(invalid)


def test_rejects_missing_threshold_field() -> None:
    valid = load_oap_factor_contract(FIXTURE)
    decision_rule = dict(valid.decision_rule)
    decision_rule.pop("long_threshold")

    with pytest.raises(OAPFactorContractError, match="long_threshold"):
        validate_oap_factor_contract(replace(valid, decision_rule=decision_rule))


def test_rejects_unsupported_rebalance_frequency() -> None:
    valid = load_oap_factor_contract(FIXTURE)
    invalid = replace(valid, timing={**valid.timing, "rebalance_frequency": "daily"})

    with pytest.raises(OAPFactorContractError, match="Unsupported timing.rebalance_frequency"):
        validate_oap_factor_contract(invalid)
