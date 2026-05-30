from __future__ import annotations

from pathlib import Path

import pandas as pd

_PARQUET_INSTALL_MESSAGE = (
    "Parquet support requires pyarrow. Install AlphaForge with its standard "
    "dependencies: python3 -m pip install -e ."
)


def read_parquet_artifact(path: Path | str) -> pd.DataFrame:
    """Read a Parquet artifact with an AlphaForge-specific dependency message."""
    try:
        return pd.read_parquet(path)
    except ImportError as exc:
        raise ImportError(_PARQUET_INSTALL_MESSAGE) from exc


def write_parquet_artifact(
    frame: pd.DataFrame,
    path: Path | str,
    *,
    index: bool = False,
) -> None:
    """Write a Parquet artifact with an AlphaForge-specific dependency message."""
    try:
        frame.to_parquet(path, index=index)
    except ImportError as exc:
        raise ImportError(_PARQUET_INSTALL_MESSAGE) from exc
