"""
GOLD LAYER — Analytical marts
──────────────────────────────
Goal  : Produce aggregated, business-ready tables, each optimised for
        a specific Power BI report page.
Rules : Read ONLY from Silver. One function per mart.
        Each mart is independently callable and testable.

Output: data/gold/credit_summary.parquet    → KPI overview page
        data/gold/vintage_analysis.parquet  → vintage / cohort page
        data/gold/grade_performance.parquet → grade / risk page
        data/gold/geo_distribution.parquet  → geographic page
"""
from __future__ import annotations

import pandas as pd

from config.settings import (
    GOLD_CREDIT_SUMMARY,
    GOLD_GEO,
    GOLD_GRADE_PERF,
    GOLD_VINTAGE,
    SILVER_FILE,
)
from src.utils.io_helpers import read_parquet, write_parquet
from src.utils.logger import get_logger

log = get_logger("gold")


# ─── public entry-point ──────────────────────────────────────────────────────

def run() -> dict[str, pd.DataFrame]:
    """Build and persist all Gold marts. Returns a dict of DataFrames."""
    log.info("=" * 60)
    log.info("GOLD — building analytical marts")

    df = read_parquet(SILVER_FILE)

    marts = {
        "credit_summary": build_credit_summary(df),
        "vintage_analysis": build_vintage_analysis(df),
        "grade_performance": build_grade_performance(df),
        "geo_distribution": build_geo_distribution(df),
    }

    # Persist
    write_parquet(marts["credit_summary"],   GOLD_CREDIT_SUMMARY)
    write_parquet(marts["vintage_analysis"], GOLD_VINTAGE)
    write_parquet(marts["grade_performance"],GOLD_GRADE_PERF)
    write_parquet(marts["geo_distribution"], GOLD_GEO)

    log.info("GOLD — all marts ready ✓")
    return marts


# ─── mart builders ───────────────────────────────────────────────────────────

def build_credit_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Monthly KPI snapshot — feeds the executive overview page in Power BI.

    Columns produced
    ----------------
    issue_year, issue_quarter, issue_month
    total_loans, total_funded_amnt, avg_loan_amnt
    avg_int_rate, avg_dti, avg_fico_mid
    default_rate          (% of settled loans that defaulted)
    total_defaults
    avg_recovery_rate     (recoveries / funded_amnt for defaulted loans)
    """
    log.info("Building mart: credit_summary")

    settled = df[df["is_default"].notna()].copy()

    grp = settled.groupby(["issue_year", "issue_quarter", "issue_month"])

    summary = grp.agg(
        total_loans      =("id",            "count"),
        total_funded     =("funded_amnt",   "sum"),
        avg_loan_amnt    =("loan_amnt",     "mean"),
        avg_int_rate     =("int_rate",      "mean"),
        avg_dti          =("dti",           "mean"),
        avg_fico_mid     =("fico_mid",      "mean"),
        total_defaults   =("is_default",    "sum"),
    ).reset_index()

    summary["default_rate"] = (
        summary["total_defaults"] / summary["total_loans"] * 100
    ).round(2)

    # Recovery rate on defaulted loans only
    defaulted = settled[settled["is_default"] == 1].copy()
    if "recoveries" in defaulted.columns and "funded_amnt" in defaulted.columns:
        rec = (
            defaulted
            .groupby(["issue_year", "issue_quarter", "issue_month"])
            .apply(
                lambda g: (g["recoveries"].sum() / g["funded_amnt"].sum() * 100)
                if g["funded_amnt"].sum() > 0 else 0,
                include_groups=False,
            )
            .reset_index(name="avg_recovery_rate")
        )
        summary = summary.merge(rec, on=["issue_year", "issue_quarter", "issue_month"], how="left")

    summary = summary.sort_values(["issue_year", "issue_quarter", "issue_month"])
    log.info(f"credit_summary: {len(summary):,} rows")
    return summary


def build_vintage_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cohort / vintage analysis — each cohort is a quarter of loan issuance.
    Default rate is computed only on settled loans.

    Columns produced
    ----------------
    vintage_quarter     (e.g. '2015-Q1')
    grade
    cohort_size
    default_rate
    avg_int_rate
    avg_loan_amnt
    total_exposure      (sum of funded amounts)
    """
    log.info("Building mart: vintage_analysis")

    settled = df[df["is_default"].notna()].copy()

    if "issue_year" not in settled.columns or "issue_quarter" not in settled.columns:
        log.warning("Date columns missing — vintage mart will be empty")
        return pd.DataFrame()

    settled["vintage_quarter"] = (
        settled["issue_year"].astype(str) + "-Q" + settled["issue_quarter"].astype(str)
    )

    vintage = (
        settled
        .groupby(["vintage_quarter", "grade"], observed=True)
        .agg(
            cohort_size   =("id",          "count"),
            total_defaults=("is_default",  "sum"),
            avg_int_rate  =("int_rate",    "mean"),
            avg_loan_amnt =("loan_amnt",   "mean"),
            total_exposure=("funded_amnt", "sum"),
        )
        .reset_index()
    )

    vintage["default_rate"] = (
        vintage["total_defaults"] / vintage["cohort_size"] * 100
    ).round(2)

    vintage = vintage.sort_values(["vintage_quarter", "grade"])
    log.info(f"vintage_analysis: {len(vintage):,} rows")
    return vintage


def build_grade_performance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Grade & sub-grade performance table — feeds the risk heatmap page.

    Columns produced
    ----------------
    grade, sub_grade
    loan_count
    avg_int_rate, avg_dti, avg_fico_mid
    default_rate
    avg_loan_amnt
    total_exposure
    risk_band_dominant  (most common risk band in this sub-grade)
    """
    log.info("Building mart: grade_performance")

    settled = df[df["is_default"].notna()].copy()

    perf = (
        settled
        .groupby(["grade", "sub_grade"], observed=True)
        .agg(
            loan_count    =("id",         "count"),
            total_defaults=("is_default", "sum"),
            avg_int_rate  =("int_rate",   "mean"),
            avg_dti       =("dti",        "mean"),
            avg_fico_mid  =("fico_mid",   "mean"),
            avg_loan_amnt =("loan_amnt",  "mean"),
            total_exposure=("funded_amnt","sum"),
        )
        .reset_index()
    )

    perf["default_rate"] = (
        perf["total_defaults"] / perf["loan_count"] * 100
    ).round(2)

    # Dominant risk band per sub-grade
    if "risk_band" in settled.columns:
        mode_band = (
            settled
            .dropna(subset=["risk_band"])
            .groupby("sub_grade", observed=True)["risk_band"]
            .agg(lambda x: x.mode()[0] if len(x) > 0 else None)
            .reset_index()
            .rename(columns={"risk_band": "risk_band_dominant"})
        )
        perf = perf.merge(mode_band, on="sub_grade", how="left")

    perf = perf.sort_values(["grade", "sub_grade"])
    log.info(f"grade_performance: {len(perf):,} rows")
    return perf


def build_geo_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    State-level geographic distribution — feeds the map page.

    Columns produced
    ----------------
    addr_state
    loan_count
    total_funded
    avg_int_rate
    avg_loan_amnt
    default_rate
    dominant_purpose    (most common loan purpose in this state)
    """
    log.info("Building mart: geo_distribution")

    if "addr_state" not in df.columns:
        log.warning("addr_state missing — geo mart will be empty")
        return pd.DataFrame()

    settled = df[df["is_default"].notna()].copy()

    geo = (
        settled
        .groupby("addr_state")
        .agg(
            loan_count    =("id",         "count"),
            total_funded  =("funded_amnt","sum"),
            avg_int_rate  =("int_rate",   "mean"),
            avg_loan_amnt =("loan_amnt",  "mean"),
            total_defaults=("is_default", "sum"),
        )
        .reset_index()
    )

    geo["default_rate"] = (
        geo["total_defaults"] / geo["loan_count"] * 100
    ).round(2)

    if "purpose" in settled.columns:
        dominant = (
            settled
            .dropna(subset=["purpose"])
            .groupby("addr_state")["purpose"]
            .agg(lambda x: x.mode()[0] if len(x) > 0 else None)
            .reset_index()
            .rename(columns={"purpose": "dominant_purpose"})
        )
        geo = geo.merge(dominant, on="addr_state", how="left")

    geo = geo.sort_values("loan_count", ascending=False)
    log.info(f"geo_distribution: {len(geo):,} rows")
    return geo


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run()
