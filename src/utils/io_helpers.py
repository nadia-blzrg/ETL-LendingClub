"""
Shared I/O helpers used by all three layers.
Centralises read/write so compression and engine choices are consistent.
"""
from pathlib import Path

import pandas as pd

from src.utils.logger import get_logger

log = get_logger("io_helpers")


def read_parquet(path: Path) -> pd.DataFrame:
    """Read a parquet file and log basic shape info."""
    log.info(f"Reading parquet: {path}")
    df = pd.read_parquet(path, engine="pyarrow")
    log.info(f"Loaded {len(df):,} rows × {df.shape[1]} columns")
    return df


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame to parquet with snappy compression."""
    path.parent.mkdir(parents=True, exist_ok=True)
    log.info(f"Writing {len(df):,} rows → {path}")
    df.to_parquet(path, engine="pyarrow", compression="snappy", index=False)
    size_mb = path.stat().st_size / 1_048_576
    log.info(f"Saved {size_mb:.1f} MB")


def profile_nulls(df: pd.DataFrame, label: str = "") -> pd.DataFrame:
    """Return a DataFrame with null counts and % per column (useful for docs)."""
    total = len(df)
    stats = (
        df.isnull()
        .sum()
        .reset_index()
        .rename(columns={"index": "column", 0: "null_count"})
    )
    stats["null_pct"] = (stats["null_count"] / total * 100).round(2)
    stats = stats[stats["null_count"] > 0].sort_values("null_pct", ascending=False)
    if label:
        log.debug(f"Null profile [{label}]:\n{stats.to_string(index=False)}")
    return stats
