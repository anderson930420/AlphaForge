"""OAP / JKP factor contract loading and validation.

Phase 12 intentionally defines a small deterministic contract layer only. It
parses a constrained YAML mapping shape used by AlphaForge's factor-contract
fixtures without adding a new dependency or ingesting real OAP / JKP data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


SUPPORTED_CONTRACT_VERSION = "alphaforge_oap_factor_contract_v0.1"
SUPPORTED_DECISION_RULE_TYPES = {"threshold"}
SUPPORTED_TARGET_WEIGHT_MODES = {"signed_unit"}
SUPPORTED_AVAILABLE_AT_POLICIES = {"next_month"}
SUPPORTED_REBALANCE_FREQUENCIES = {"monthly"}
SUPPORTED_OUTPUT_SCHEMAS = {"signal_csv_v0.2"}

REQUIRED_SECTIONS = (
    "dataset",
    "factor",
    "decision_rule",
    "weighting",
    "timing",
    "identity",
    "validation",
    "output",
)


class OAPFactorContractError(ValueError):
    """Raised when an OAP / JKP factor contract is invalid."""


@dataclass(frozen=True)
class OAPFactorContract:
    """Machine-readable OAP / JKP factor contract."""

    version: str
    dataset: dict[str, Any]
    factor: dict[str, Any]
    decision_rule: dict[str, Any]
    weighting: dict[str, Any]
    timing: dict[str, Any]
    identity: dict[str, Any]
    validation: dict[str, Any]
    output: dict[str, Any]


_KEY_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")


def _strip_inline_comment(value: str) -> str:
    """Strip YAML-style comments outside simple quoted strings."""
    in_single = False
    in_double = False
    for index, char in enumerate(value):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            if index == 0 or value[index - 1].isspace():
                return value[:index].rstrip()
    return value.strip()


def _parse_scalar(raw_value: str) -> Any:
    value = _strip_inline_comment(raw_value)
    if value == "":
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        if any(char in value for char in (".", "e", "E")):
            return float(value)
        return int(value)
    except ValueError:
        return value


def _parse_simple_yaml_mapping(text: str) -> dict[str, Any]:
    """Parse the small YAML subset used by Phase 12 contract fixtures.

    Supported shape:
    - nested mappings using two-space indentation
    - scalar string / number / boolean values
    - blank lines and comments

    Lists, anchors, multiline strings, and flow mappings are intentionally not
    supported in this dependency-free parser.
    """
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith("\t"):
            raise OAPFactorContractError(f"Tabs are not supported in contract YAML at line {line_number}")

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2 != 0:
            raise OAPFactorContractError(f"Indentation must use two-space levels at line {line_number}")

        stripped = raw_line.strip()
        if ":" not in stripped:
            raise OAPFactorContractError(f"Expected key/value mapping at line {line_number}")
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        if not key or any(char not in _KEY_CHARS for char in key):
            raise OAPFactorContractError(f"Invalid mapping key at line {line_number}: {key!r}")

        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise OAPFactorContractError(f"Invalid indentation at line {line_number}")

        parent = stack[-1][1]
        value_text = raw_value.strip()
        if value_text == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(value_text)

    return root


def _require_mapping(value: Any, section_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise OAPFactorContractError(f"Contract section `{section_name}` must be a mapping")
    return value


def _require_key(mapping: dict[str, Any], key: str, section_name: str) -> Any:
    if key not in mapping:
        raise OAPFactorContractError(f"Contract section `{section_name}` is missing required key `{key}`")
    return mapping[key]


def load_oap_factor_contract(path: str | Path) -> OAPFactorContract:
    """Load and validate an OAP / JKP factor contract from disk."""
    contract_path = Path(path)
    data = _parse_simple_yaml_mapping(contract_path.read_text(encoding="utf-8"))

    version = data.get("version")
    if not isinstance(version, str):
        raise OAPFactorContractError("Contract is missing string `version`")

    contract = OAPFactorContract(
        version=version,
        dataset=_require_mapping(data.get("dataset"), "dataset"),
        factor=_require_mapping(data.get("factor"), "factor"),
        decision_rule=_require_mapping(data.get("decision_rule"), "decision_rule"),
        weighting=_require_mapping(data.get("weighting"), "weighting"),
        timing=_require_mapping(data.get("timing"), "timing"),
        identity=_require_mapping(data.get("identity"), "identity"),
        validation=_require_mapping(data.get("validation"), "validation"),
        output=_require_mapping(data.get("output"), "output"),
    )
    validate_oap_factor_contract(contract)
    return contract


def validate_oap_factor_contract(contract: OAPFactorContract) -> None:
    """Validate the Phase 12 OAP / JKP factor contract subset."""
    if contract.version != SUPPORTED_CONTRACT_VERSION:
        raise OAPFactorContractError(
            f"Unsupported OAP factor contract version: {contract.version!r}; "
            f"expected {SUPPORTED_CONTRACT_VERSION!r}"
        )

    for section_name in REQUIRED_SECTIONS:
        _require_mapping(getattr(contract, section_name), section_name)

    _validate_dataset(contract.dataset)
    _validate_factor(contract.factor)
    _validate_threshold_decision_rule(contract.decision_rule)
    _validate_signed_unit_weighting(contract.weighting)
    _validate_timing(contract.timing)
    _validate_identity(contract.identity)
    _validate_validation(contract.validation)
    _validate_output(contract.output)


def _validate_dataset(dataset: dict[str, Any]) -> None:
    for key in ("name", "provider", "release", "frequency"):
        value = _require_key(dataset, key, "dataset")
        if not isinstance(value, str) or not value:
            raise OAPFactorContractError(f"dataset.{key} must be a non-empty string")
    if dataset["frequency"] != "monthly":
        raise OAPFactorContractError("Only monthly OAP / JKP factor contracts are supported in Phase 12")


def _validate_factor(factor: dict[str, Any]) -> None:
    for key in ("name", "raw_column", "value_column"):
        value = _require_key(factor, key, "factor")
        if not isinstance(value, str) or not value:
            raise OAPFactorContractError(f"factor.{key} must be a non-empty string")
    if not isinstance(_require_key(factor, "higher_is_better", "factor"), bool):
        raise OAPFactorContractError("factor.higher_is_better must be a boolean")


def _validate_threshold_decision_rule(decision_rule: dict[str, Any]) -> None:
    rule_type = _require_key(decision_rule, "type", "decision_rule")
    if rule_type not in SUPPORTED_DECISION_RULE_TYPES:
        raise OAPFactorContractError(f"Unsupported decision_rule.type: {rule_type!r}")

    long_threshold = _require_key(decision_rule, "long_threshold", "decision_rule")
    short_threshold = _require_key(decision_rule, "short_threshold", "decision_rule")
    if not isinstance(long_threshold, (int, float)):
        raise OAPFactorContractError("decision_rule.long_threshold must be numeric")
    if not isinstance(short_threshold, (int, float)):
        raise OAPFactorContractError("decision_rule.short_threshold must be numeric")

    long_when = _require_key(decision_rule, "long_when", "decision_rule")
    short_when = _require_key(decision_rule, "short_when", "decision_rule")
    if long_when != "greater_than":
        raise OAPFactorContractError("decision_rule.long_when must be `greater_than`")
    if short_when != "less_than":
        raise OAPFactorContractError("decision_rule.short_when must be `less_than`")


def _validate_signed_unit_weighting(weighting: dict[str, Any]) -> None:
    mode = _require_key(weighting, "target_weight_mode", "weighting")
    if mode not in SUPPORTED_TARGET_WEIGHT_MODES:
        raise OAPFactorContractError(f"Unsupported weighting.target_weight_mode: {mode!r}")

    long_weight = _require_key(weighting, "long_weight", "weighting")
    short_weight = _require_key(weighting, "short_weight", "weighting")
    neutral_weight = _require_key(weighting, "neutral_weight", "weighting")

    for key, value in (
        ("long_weight", long_weight),
        ("short_weight", short_weight),
        ("neutral_weight", neutral_weight),
    ):
        if not isinstance(value, (int, float)):
            raise OAPFactorContractError(f"weighting.{key} must be numeric")

    if not 0 < float(long_weight) <= 1:
        raise OAPFactorContractError("weighting.long_weight must be positive and <= 1")
    if not -1 <= float(short_weight) < 0:
        raise OAPFactorContractError("weighting.short_weight must be negative and >= -1")
    if float(neutral_weight) != 0:
        raise OAPFactorContractError("weighting.neutral_weight must equal 0")


def _validate_timing(timing: dict[str, Any]) -> None:
    datetime_col = _require_key(timing, "datetime_col", "timing")
    if not isinstance(datetime_col, str) or not datetime_col:
        raise OAPFactorContractError("timing.datetime_col must be a non-empty string")

    available_at_policy = _require_key(timing, "available_at_policy", "timing")
    if available_at_policy not in SUPPORTED_AVAILABLE_AT_POLICIES:
        raise OAPFactorContractError(f"Unsupported timing.available_at_policy: {available_at_policy!r}")

    rebalance_frequency = _require_key(timing, "rebalance_frequency", "timing")
    if rebalance_frequency not in SUPPORTED_REBALANCE_FREQUENCIES:
        raise OAPFactorContractError(f"Unsupported timing.rebalance_frequency: {rebalance_frequency!r}")


def _validate_identity(identity: dict[str, Any]) -> None:
    for key in ("asset_id_col", "symbol_col"):
        value = _require_key(identity, key, "identity")
        if not isinstance(value, str) or not value:
            raise OAPFactorContractError(f"identity.{key} must be a non-empty string")


def _validate_validation(validation: dict[str, Any]) -> None:
    for key in ("require_unique_datetime_symbol", "allow_missing_factor_value", "allow_missing_return"):
        if not isinstance(_require_key(validation, key, "validation"), bool):
            raise OAPFactorContractError(f"validation.{key} must be a boolean")


def _validate_output(output: dict[str, Any]) -> None:
    schema = _require_key(output, "schema", "output")
    if schema not in SUPPORTED_OUTPUT_SCHEMAS:
        raise OAPFactorContractError(f"Unsupported output.schema: {schema!r}")
