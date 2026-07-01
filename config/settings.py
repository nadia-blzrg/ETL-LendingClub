"""
Central configuration for the Lending Club ETL pipeline.
All paths, constants, and column definitions live here.
"""
from pathlib import Path

# ── Root paths ──────────────────────────────────────────────────────────────
ROOT_DIR   = Path(__file__).resolve().parent.parent
DATA_DIR   = ROOT_DIR / "data"
LOGS_DIR   = ROOT_DIR / "logs"

# Medallion layers
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR   = DATA_DIR / "gold"

# ── Source files ─────────────────────────────────────────────────────────────
RAW_CSV    = DATA_DIR / "raw" / "accepted_2007_to_2018Q4.csv"

# ── Bronze ───────────────────────────────────────────────────────────────────
BRONZE_FILE     = BRONZE_DIR / "loans_raw.parquet"
BRONZE_METADATA = BRONZE_DIR / "ingestion_metadata.json"

# ── Silver ───────────────────────────────────────────────────────────────────
SILVER_FILE = SILVER_DIR / "loans_clean.parquet"

# ── Gold (one file per mart) ─────────────────────────────────────────────────
GOLD_CREDIT_SUMMARY = GOLD_DIR / "credit_summary.parquet"
GOLD_VINTAGE        = GOLD_DIR / "vintage_analysis.parquet"
GOLD_GRADE_PERF     = GOLD_DIR / "grade_performance.parquet"
GOLD_GEO            = GOLD_DIR / "geo_distribution.parquet"

# ── Ingestion settings ───────────────────────────────────────────────────────
# Set to None to load the full dataset
SAMPLE_SIZE: int | None = 200_000

# Columns to keep from the raw CSV (subset of ~150 columns)
BRONZE_COLUMNS = [
    # identity & target
    "id", "loan_status", "grade", "sub_grade",
    # amounts & rates
    "loan_amnt", "funded_amnt", "funded_amnt_inv",
    "int_rate", "installment", "total_pymnt", "recoveries",
    # borrower profile
    "annual_inc", "emp_length", "home_ownership",
    "verification_status", "purpose", "title",
    "dti", "addr_state", "zip_code",
    # credit history
    "delinq_2yrs", "fico_range_low", "fico_range_high",
    "open_acc", "pub_rec", "revol_bal", "revol_util",
    "total_acc", "earliest_cr_line",
    # dates
    "issue_d", "last_pymnt_d", "last_credit_pull_d",
    # loan terms
    "term", "application_type",
]

# ── Default loan status groups ────────────────────────────────────────────────
DEFAULT_STATUSES = [
    "Charged Off",
    "Default",
    "Does not meet the credit policy. Status:Charged Off",
]

PAID_STATUSES = [
    "Fully Paid",
    "Does not meet the credit policy. Status:Fully Paid",
]
