from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from numbers import Real
from pathlib import Path
from typing import Any


def json_safe_float(value: Any) -> float | None:
    """Convert a scalar value to a finite JSON-safe float or None."""
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def json_safe_payload(value: Any) -> Any:
    """Recursively replace non-finite numeric values with None before JSON writing."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, Mapping):
        return {key: json_safe_payload(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [json_safe_payload(item) for item in value]
    if isinstance(value, Real):
        if isinstance(value, int):
            return value
        return json_safe_float(value)
    return value


def write_json_artifact(path: Path | str, payload: Mapping[str, Any]) -> None:
    """Write a strict JSON artifact while preserving default=str compatibility."""
    path = Path(path)
    with open(path, "w") as f:
        json.dump(json_safe_payload(payload), f, indent=2, default=str, allow_nan=False)
