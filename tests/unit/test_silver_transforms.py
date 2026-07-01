"""
Unit tests for Silver transformations.
Each transformation function is tested in isolation with minimal fixtures.

Run: pytest tests/unit/test_silver_transforms.py -v
"""
import pandas as pd
import pytest

from src.transform.silver import (
    _cast_categoricals,
    _clean_strings,
    _derive_fico_mid,
    _derive_risk_band,
    _derive_target,
    _drop_unusable_rows,
    _encode_emp_length,
    _encode_term,
    _parse_dates,
    _parse_percentages,
)


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def base_df():
    """Minimal raw DataFrame that mirrors Bronze output."""
    return pd.DataFrame({
        "id":            ["L001", "L002", "L003", "L004"],
        "loan_amnt":     [10_000, 5_000,  15_000, None],
        "funded_amnt":   [10_000, 5_000,  15_000, 8_000],
        "int_rate":      ["10.5%", "14.2%", "6.0%", "18.0%"],
        "revol_util":    ["45.3%", "80.0%", "20.1%", None],
        "emp_length":    ["5 years", "10+ years", "< 1 year", "2 years"],
        "term":          [" 36 months", " 60 months", " 36 months", " 60 months"],
        "loan_status":   ["Fully Paid", "Charged Off", "Current", None],
        "issue_d":       ["Jan-2015", "Mar-2017", "Jul-2019", "Nov-2020"],
        "earliest_cr_line": ["Jan-2000", "Mar-2005", "Jul-2010", "Nov-2015"],
        "fico_range_low": [700.0, 640.0, 750.0, 680.0],
        "fico_range_high":[704.0, 644.0, 754.0, 684.0],
        "grade":         ["B", "D", "A", "C"],
        "home_ownership":["RENT", "OWN", "MORTGAGE", "RENT"],
        "dti":           [15.0, 30.0, 8.0, None],
    })


# ── string cleaning ───────────────────────────────────────────────────────────

def test_clean_strings_strips_whitespace():
    df = pd.DataFrame({"name": ["  Alice ", " Bob"], "value": [1, 2]})
    out = _clean_strings(df)
    assert out["name"].tolist() == ["Alice", "Bob"]


# ── percentage parsing ────────────────────────────────────────────────────────

def test_parse_percentages_converts_to_float(base_df):
    out = _parse_percentages(base_df)
    assert out["int_rate"].dtype == "float32"
    assert abs(out["int_rate"].iloc[0] - 10.5) < 0.01


def test_parse_percentages_handles_null(base_df):
    out = _parse_percentages(base_df)
    assert pd.isna(out["revol_util"].iloc[3])


# ── date parsing ──────────────────────────────────────────────────────────────

def test_parse_dates_creates_issue_year(base_df):
    out = _parse_dates(base_df)
    assert "issue_year" in out.columns
    assert out["issue_year"].iloc[0] == 2015


def test_parse_dates_creates_credit_history_months(base_df):
    out = _parse_dates(base_df)
    assert "credit_history_months" in out.columns
    # Jan-2015 - Jan-2000 ≈ 180 months (calendar variance ±5 months accepted)
    assert abs(out["credit_history_months"].iloc[0] - 180) < 6


# ── employment length ─────────────────────────────────────────────────────────

def test_encode_emp_length_maps_correctly(base_df):
    out = _encode_emp_length(base_df)
    assert out["emp_length_num"].iloc[0] == 5   # "5 years"
    assert out["emp_length_num"].iloc[1] == 10  # "10+ years"
    assert out["emp_length_num"].iloc[2] == 0   # "< 1 year"


# ── term ─────────────────────────────────────────────────────────────────────

def test_encode_term_extracts_months(base_df):
    out = _encode_term(base_df)
    assert out["term_months"].iloc[0] == 36
    assert out["term_months"].iloc[1] == 60


# ── default target ────────────────────────────────────────────────────────────

def test_derive_target_flags_defaults(base_df):
    out = _derive_target(base_df)
    assert out["is_default"].iloc[0] == 0   # Fully Paid
    assert out["is_default"].iloc[1] == 1   # Charged Off
    assert pd.isna(out["is_default"].iloc[2])   # Current → NaN


# ── FICO mid ──────────────────────────────────────────────────────────────────

def test_derive_fico_mid_is_average(base_df):
    out = _derive_fico_mid(base_df)
    assert out["fico_mid"].iloc[0] == pytest.approx(702.0, abs=0.1)


# ── risk band ─────────────────────────────────────────────────────────────────

def test_derive_risk_band_buckets(base_df):
    out = _derive_fico_mid(base_df)
    out = _derive_risk_band(out)
    # fico_mid=702 → Good (690–719)
    assert "Good" in str(out["risk_band"].iloc[0])
    # fico_mid=642 → Fair (630–689)
    assert "Fair" in str(out["risk_band"].iloc[1])
    # fico_mid=752 → Excellent (720+)
    assert "Excellent" in str(out["risk_band"].iloc[2])


# ── drop unusable rows ────────────────────────────────────────────────────────

def test_drop_unusable_rows_removes_null_amnt_and_status(base_df):
    df = _parse_dates(base_df)   # issue_d must be datetime first
    out = _drop_unusable_rows(df)
    # Row 3 has null loan_amnt AND null loan_status → should be dropped
    assert len(out) == 3


def test_drop_unusable_rows_keeps_valid_rows(base_df):
    df = _parse_dates(base_df)
    out = _drop_unusable_rows(df)
    assert "L001" in out["id"].values
    assert "L002" in out["id"].values


# ── categorical casting ───────────────────────────────────────────────────────

def test_cast_categoricals_converts_grade(base_df):
    out = _cast_categoricals(base_df)
    assert str(out["grade"].dtype) == "category"


def test_cast_categoricals_leaves_numerics_unchanged(base_df):
    out = _cast_categoricals(base_df)
    assert out["loan_amnt"].dtype == base_df["loan_amnt"].dtype
