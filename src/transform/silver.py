"""
SILVER LAYER — Cleaning & standardisation
──────────────────────────────────────────
Goal  : Produce a clean, fully-typed, analytics-ready DataFrame.
Rules : All business rules belong here.
        - Parse dates, fix dirty strings, cast types
        - Derive simple flags (is_default, risk_band)
        - Drop/impute nulls with documented rationale
        - NO aggregation — that belongs in Gold

Input : data/bronze/loans_raw.parquet
Output: data/silver/loans_clean.parquet
"""
from __future__ import annotations

import pandas as pd

from config.settings import (
    BRONZE_FILE,
    DEFAULT_STATUSES,
    PAID_STATUSES,
    SILVER_FILE,
)
from src.utils.io_helpers import profile_nulls, read_parquet, write_parquet
from src.utils.logger import get_logger

log = get_logger("silver")


# ─── public entry-point ──────────────────────────────────────────────────────

def run() -> pd.DataFrame:
    log.info("=" * 60)
    log.info("SILVER — starting cleaning")

    df = read_parquet(BRONZE_FILE)
    rows_in = len(df)

    df = (
        df
        .pipe(_clean_strings)
        .pipe(_parse_percentages)
        .pipe(_parse_dates)
        .pipe(_encode_emp_length)
        .pipe(_encode_term)
        .pipe(_derive_target)
        .pipe(_derive_fico_mid)
        .pipe(_derive_risk_band)
        .pipe(_drop_unusable_rows)
        .pipe(_impute_numerics)
        .pipe(_cast_categoricals)
    )

    rows_out = len(df)
    log.info(f"Rows in: {rows_in:,} → Rows out: {rows_out:,} (dropped {rows_in - rows_out:,})")
    profile_nulls(df, label="silver")

    write_parquet(df, SILVER_FILE)
    log.info("SILVER — done ✓")
    return df


# ─── transformation steps (each is independently testable) ───────────────────

def _clean_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from all object columns."""
    obj_cols = df.select_dtypes(include="object").columns
    df[obj_cols] = df[obj_cols].apply(lambda s: s.str.strip())
    return df


def _parse_percentages(df: pd.DataFrame) -> pd.DataFrame:
    """
    int_rate and revol_util are stored as '10.5%' strings in the raw data.
    Convert to float values (10.5, not 0.105).
    """
    for col in ("int_rate", "revol_util"):
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col]
                .astype(str)
                .str.replace("%", "", regex=False)
                .str.strip()
                .replace({"nan": None, "None": None, "<NA>": None}),
                errors="coerce",
            ).astype("float32")
            log.debug(f"Parsed percentage column: {col}")
    return df


def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Lending Club dates are in 'Mon-YYYY' format (e.g. 'Jan-2015').
    Parse and extract year / quarter / month features.
    """
    date_cols = ["issue_d", "last_pymnt_d", "last_credit_pull_d", "earliest_cr_line"]
    for col in date_cols:
        if col not in df.columns:
            continue
        df[col] = pd.to_datetime(df[col], format="%b-%Y", errors="coerce")
        log.debug(f"Parsed date column: {col}")

    if "issue_d" in df.columns:
        df["issue_year"]    = df["issue_d"].dt.year.astype("Int16")
        df["issue_quarter"] = df["issue_d"].dt.quarter.astype("Int8")
        df["issue_month"]   = df["issue_d"].dt.month.astype("Int8")

    if "earliest_cr_line" in df.columns and "issue_d" in df.columns:
        df["credit_history_months"] = (
            (df["issue_d"] - df["earliest_cr_line"]) / pd.Timedelta(days=30)
        ).round().astype("Int16")

    return df


def _encode_emp_length(df: pd.DataFrame) -> pd.DataFrame:
    """Map employment length strings to integers (0–10)."""
    if "emp_length" not in df.columns:
        return df
    mapping = {
        "< 1 year": 0, "1 year": 1, "2 years": 2, "3 years": 3,
        "4 years": 4,  "5 years": 5, "6 years": 6, "7 years": 7,
        "8 years": 8,  "9 years": 9, "10+ years": 10,
    }
    df["emp_length_num"] = df["emp_length"].map(mapping).astype("Int8")
    return df


def _encode_term(df: pd.DataFrame) -> pd.DataFrame:
    """'36 months' / '60 months' → integer 36 / 60."""
    if "term" not in df.columns:
        return df
    df["term_months"] = (
        df["term"]
        .str.extract(r"(\d+)")
        .astype("Int8")
    )
    return df


def _derive_target(df: pd.DataFrame) -> pd.DataFrame:
    """
    Binary default flag used as the primary KPI across all Gold marts.
      1 = charged-off / defaulted
      0 = fully paid
      NaN = still active (excluded from default-rate calculations)
    """
    if "loan_status" not in df.columns:
        return df
    df["is_default"] = None
    df.loc[df["loan_status"].isin(DEFAULT_STATUSES), "is_default"] = 1
    df.loc[df["loan_status"].isin(PAID_STATUSES),   "is_default"] = 0
    df["is_default"] = df["is_default"].astype("Int8")
    log.debug(
        f"Default flag: {df['is_default'].value_counts(dropna=False).to_dict()}"
    )
    return df


def _derive_fico_mid(df: pd.DataFrame) -> pd.DataFrame:
    """Midpoint FICO score from the low/high band."""
    if "fico_range_low" in df.columns and "fico_range_high" in df.columns:
        df["fico_mid"] = (
            (df["fico_range_low"] + df["fico_range_high"]) / 2
        ).astype("float32")
    return df


def _derive_risk_band(df: pd.DataFrame) -> pd.DataFrame:
    """
    Segment loans into 4 risk tiers based on FICO midpoint.
    Thresholds follow standard US credit scoring conventions.
    """
    if "fico_mid" not in df.columns:
        return df
    bins   = [0, 629, 689, 719, 850]
    labels = ["Poor (<630)", "Fair (630–689)", "Good (690–719)", "Excellent (720+)"]
    df["risk_band"] = pd.cut(df["fico_mid"], bins=bins, labels=labels, right=True)
    return df


def _drop_unusable_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop rows that cannot be used in any analysis:
    - No loan amount (impossible to compute LTV or exposure)
    - No loan status (impossible to compute default rate)
    - No issue date (impossible to build vintages)
    """
    before = len(df)
    df = df.dropna(subset=["loan_amnt", "loan_status", "issue_d"])
    after = len(df)
    log.info(f"Dropped {before - after:,} rows missing critical fields")
    return df


def _impute_numerics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Conservative median imputation for numeric columns with < 5% nulls.
    Columns with > 5% nulls are left as-is (handled per-mart in Gold).
    """
    num_cols = df.select_dtypes(include=["float32", "float64", "Int8", "Int16"]).columns
    for col in num_cols:
        null_pct = df[col].isna().mean()
        if 0 < null_pct <= 0.05:
            median = df[col].median()
            df[col] = df[col].fillna(median)
            log.debug(f"Imputed {col} with median={median:.2f} (was {null_pct:.1%} null)")
    return df


def _cast_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cast low-cardinality string columns to Categorical.
    This reduces memory significantly and speeds up groupby operations.
    """
    cat_cols = [
        "grade", "sub_grade", "home_ownership", "verification_status",
        "purpose", "loan_status", "application_type",
    ]
    for col in cat_cols:
        if col in df.columns:
            df[col] = df[col].astype("category")
    return df


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run()
