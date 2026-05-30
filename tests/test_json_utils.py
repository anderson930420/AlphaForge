from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from alphaforge.json_utils import json_safe_float, json_safe_payload, write_json_artifact


def test_json_safe_float_converts_non_finite_values_to_none() -> None:
    assert json_safe_float(float("nan")) is None
    assert json_safe_float(float("inf")) is None
    assert json_safe_float(float("-inf")) is None
    assert json_safe_float(1.25) == 1.25


def test_json_safe_payload_recursively_converts_non_finite_values() -> None:
    payload = {
        "ok": 1.0,
        "bad": float("nan"),
        "nested": [float("inf"), {"neg_inf": float("-inf")}],
        "timestamp": pd.Timestamp("2024-01-31"),
    }

    safe = json_safe_payload(payload)

    assert safe["ok"] == 1.0
    assert safe["bad"] is None
    assert safe["nested"] == [None, {"neg_inf": None}]
    assert safe["timestamp"] == pd.Timestamp("2024-01-31")


def test_write_json_artifact_writes_strict_json_without_nan(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    write_json_artifact(
        path,
        {
            "nan": float("nan"),
            "inf": math.inf,
            "timestamp": pd.Timestamp("2024-01-31"),
        },
    )

    raw = path.read_text()
    assert "NaN" not in raw
    assert "Infinity" not in raw

    loaded = json.loads(raw)
    assert loaded["nan"] is None
    assert loaded["inf"] is None
    assert loaded["timestamp"] == "2024-01-31 00:00:00"
