"""
BRONZE LAYER — Raw ingestion
────────────────────────────
Goal  : Read the raw CSV, keep only the relevant columns, persist as Parquet.
Rules : NO business logic here. Data is stored exactly as received.
        Only structural operations are allowed (column selection, dtype cast
        for memory, row sampling).

Output: data/bronze/loans_raw.parquet
        data/bronze/ingestion_metadata.json
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config.settings import (
    BRONZE_COLUMNS,
    BRONZE_FILE,
    BRONZE_METADATA,
    RAW_CSV,
    SAMPLE_SIZE,
)
from src.utils.io_helpers import profile_nulls, write_parquet
from src.utils.logger import get_logger

log = get_logger("bronze")


# ─── public entry-point ──────────────────────────────────────────────────────

def run(source_path: Path = RAW_CSV) -> pd.DataFrame:
    """
    Ingest raw CSV → Bronze parquet.

    Parameters
    ----------
    source_path : override the source CSV (useful for tests with small fixtures).

    Returns
    -------
    DataFrame stored in the bronze layer.
    """
    log.info("=" * 60)
    log.info("BRONZE — starting ingestion")
    log.info(f"Source : {source_path}")
    log.info(f"Sample : {SAMPLE_SIZE or 'full dataset'}")

    # ── 1. Read ──────────────────────────────────────────────────────────────
    df = _read_csv(source_path)

    # ── 2. Column selection ──────────────────────────────────────────────────
    available = [c for c in BRONZE_COLUMNS if c in df.columns]
    missing   = [c for c in BRONZE_COLUMNS if c not in df.columns]
    if missing:
        log.warning(f"Columns not found in source (skipped): {missing}")
    df = df[available].copy()
    log.info(f"Columns kept: {len(available)}")

    # ── 3. Minimal memory optimisation (no business logic) ───────────────────
    df = _downcast_numerics(df)

    # ── 4. Persist ───────────────────────────────────────────────────────────
    write_parquet(df, BRONZE_FILE)
    _write_metadata(source_path, df)

    # ── 5. Quality snapshot ──────────────────────────────────────────────────
    profile_nulls(df, label="bronze")

    log.info("BRONZE — done ✓")
    return df


# ─── private helpers ─────────────────────────────────────────────────────────


def _read_csv(path: Path) -> pd.DataFrame:
    """Stream-read the CSV, optionally sampling the first N rows."""
    if not path.exists():
        raise FileNotFoundError(
            f"Raw CSV not found at {path}.\n"
            "Download it from: https://www.kaggle.com/datasets/wordsforthewise/lending-club"
        )

    log.info(f"Reading CSV (nrows={SAMPLE_SIZE or 'all'}) …")
    if SAMPLE_SIZE:
    # Development mode: read only the first N rows
        df = pd.read_csv(
            path,
            nrows=SAMPLE_SIZE,
            low_memory=False,
        )
    else:
        # Full dataset: skip the two summary rows at the end
        df = pd.read_csv(
            path,
            low_memory=False,
            skipfooter=2,
            engine="python",
        )
    log.info(f"Raw shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
    return df


def _downcast_numerics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Downcast float64 → float32 where precision loss is acceptable.
    No string coercion, no business mapping — that belongs in Silver.
    """
    float_cols = df.select_dtypes(include="float64").columns
    df[float_cols] = df[float_cols].astype("float32")
    return df


def _write_metadata(source_path: Path, df: pd.DataFrame) -> None:
    """Persist ingestion metadata as JSON for lineage tracking."""
    BRONZE_METADATA.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(source_path),
        "rows": len(df),
        "columns": list(df.columns),
        "sample_size": SAMPLE_SIZE,
        "bronze_parquet": str(BRONZE_FILE),
    }
    BRONZE_METADATA.write_text(json.dumps(meta, indent=2))
    log.info(f"Metadata written → {BRONZE_METADATA}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run()
