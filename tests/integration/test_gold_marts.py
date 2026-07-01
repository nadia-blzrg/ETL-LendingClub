"""
Integration tests for Gold mart builders.
These tests use a realistic Silver-shaped fixture (post all Silver transforms).

Run: pytest tests/integration/test_gold_marts.py -v
"""
import pandas as pd
import pytest

from src.load.gold import (
    build_credit_summary,
    build_geo_distribution,
    build_grade_performance,
    build_vintage_analysis,
)


# ── fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def silver_df():
    """
    Realistic Silver output — already cleaned and typed.
    Includes both settled (is_default = 0/1) and active (is_default = NaN) loans.
    """
    return pd.DataFrame({
        "id":            [f"L{i:03d}" for i in range(12)],
        "loan_amnt":     [10_000, 5_000, 15_000, 20_000, 8_000,
                          12_000, 7_000, 25_000, 9_000, 11_000, 6_000, 13_000],
        "funded_amnt":   [10_000, 5_000, 15_000, 20_000, 8_000,
                          12_000, 7_000, 25_000, 9_000, 11_000, 6_000, 13_000],
        "int_rate":      [10.5, 18.0, 6.5, 22.0, 14.0, 9.0, 16.0, 8.0, 12.0, 11.0, 19.0, 7.5],
        "dti":           [15.0, 35.0, 8.0, 40.0, 20.0, 12.0, 28.0, 7.0, 18.0, 14.0, 32.0, 9.0],
        "fico_mid":      [702.0, 642.0, 752.0, 610.0, 680.0,
                          720.0, 655.0, 760.0, 690.0, 710.0, 630.0, 740.0],
        "risk_band":     pd.Categorical([
            "Good (690–719)", "Fair (630–689)", "Excellent (720+)", "Poor (<630)",
            "Fair (630–689)", "Excellent (720+)", "Fair (630–689)", "Excellent (720+)",
            "Good (690–719)", "Good (690–719)", "Fair (630–689)", "Excellent (720+)",
        ]),
        "grade":         pd.Categorical(["B","D","A","E","C","A","C","A","B","B","D","A"]),
        "sub_grade":     pd.Categorical(["B2","D3","A1","E5","C2","A2","C3","A1","B3","B1","D4","A3"]),
        "loan_status":   pd.Categorical([
            "Fully Paid","Charged Off","Fully Paid","Charged Off","Fully Paid",
            "Fully Paid","Current","Fully Paid","Charged Off","Fully Paid","Current","Fully Paid",
        ]),
        "is_default":    pd.array([0,1,0,1,0,0,None,0,1,0,None,0], dtype="Int8"),
        "issue_d":       pd.to_datetime([
            "2015-01-01","2017-03-01","2019-07-01","2015-01-01","2017-03-01",
            "2019-07-01","2015-01-01","2017-03-01","2019-07-01","2015-01-01","2017-03-01","2019-07-01",
        ]),
        "issue_year":    pd.array([2015,2017,2019,2015,2017,2019,2015,2017,2019,2015,2017,2019], dtype="Int16"),
        "issue_quarter": pd.array([1,1,3,1,1,3,1,1,3,1,1,3], dtype="Int8"),
        "issue_month":   pd.array([1,3,7,1,3,7,1,3,7,1,3,7], dtype="Int8"),
        "recoveries":    [0,800,0,1500,0,0,0,0,600,0,0,0],
        "purpose":       pd.Categorical([
            "debt_consolidation","car","home_improvement","debt_consolidation",
            "car","home_improvement","debt_consolidation","car","home_improvement",
            "debt_consolidation","car","home_improvement",
        ]),
        "addr_state":    ["CA","NY","TX","CA","NY","TX","FL","CA","NY","TX","FL","CA"],
        "home_ownership":pd.Categorical(["RENT","OWN","MORTGAGE","RENT","OWN","MORTGAGE",
                                          "RENT","OWN","MORTGAGE","RENT","OWN","MORTGAGE"]),
    })


# ── credit_summary ────────────────────────────────────────────────────────────

class TestCreditSummary:
    def test_returns_dataframe(self, silver_df):
        out = build_credit_summary(silver_df)
        assert isinstance(out, pd.DataFrame)

    def test_has_required_columns(self, silver_df):
        out = build_credit_summary(silver_df)
        required = {"issue_year", "total_loans", "default_rate", "avg_int_rate"}
        assert required.issubset(out.columns)

    def test_excludes_active_loans_from_count(self, silver_df):
        out = build_credit_summary(silver_df)
        # Total settled loans = 10 (2 active excluded)
        assert out["total_loans"].sum() == 10

    def test_default_rate_within_bounds(self, silver_df):
        out = build_credit_summary(silver_df)
        assert out["default_rate"].between(0, 100).all()

    def test_sorted_chronologically(self, silver_df):
        out = build_credit_summary(silver_df)
        years = out["issue_year"].tolist()
        assert years == sorted(years)

    def test_no_negative_values(self, silver_df):
        out = build_credit_summary(silver_df)
        num_cols = out.select_dtypes(include="number").columns
        assert (out[num_cols] >= 0).all().all()


# ── vintage_analysis ──────────────────────────────────────────────────────────

class TestVintageAnalysis:
    def test_returns_dataframe(self, silver_df):
        out = build_vintage_analysis(silver_df)
        assert isinstance(out, pd.DataFrame)

    def test_has_vintage_quarter_column(self, silver_df):
        out = build_vintage_analysis(silver_df)
        assert "vintage_quarter" in out.columns

    def test_vintage_format(self, silver_df):
        out = build_vintage_analysis(silver_df)
        sample = out["vintage_quarter"].iloc[0]
        # Must match '2015-Q1' format
        assert "-Q" in sample

    def test_grade_column_present(self, silver_df):
        out = build_vintage_analysis(silver_df)
        assert "grade" in out.columns

    def test_cohort_sizes_positive(self, silver_df):
        out = build_vintage_analysis(silver_df)
        assert (out["cohort_size"] > 0).all()


# ── grade_performance ─────────────────────────────────────────────────────────

class TestGradePerformance:
    def test_returns_dataframe(self, silver_df):
        out = build_grade_performance(silver_df)
        assert isinstance(out, pd.DataFrame)

    def test_grade_a_has_lower_default_than_d(self, silver_df):
        out = build_grade_performance(silver_df)
        grade_a_dr = out[out["grade"] == "A"]["default_rate"].dropna().mean()
        grade_d_dr = out[out["grade"] == "D"]["default_rate"].dropna().mean()
        assert float(grade_a_dr) < float(grade_d_dr)

    def test_all_grades_present(self, silver_df):
        out = build_grade_performance(silver_df)
        grades_in_data = set(silver_df["grade"].dropna().unique())
        grades_in_mart = set(out["grade"].unique())
        assert grades_in_data == grades_in_mart

    def test_risk_band_dominant_column_added(self, silver_df):
        out = build_grade_performance(silver_df)
        assert "risk_band_dominant" in out.columns


# ── geo_distribution ──────────────────────────────────────────────────────────

class TestGeoDistribution:
    def test_returns_dataframe(self, silver_df):
        out = build_geo_distribution(silver_df)
        assert isinstance(out, pd.DataFrame)

    def test_has_state_column(self, silver_df):
        out = build_geo_distribution(silver_df)
        assert "addr_state" in out.columns

    def test_all_states_present(self, silver_df):
        out = build_geo_distribution(silver_df)
        # Only states with SETTLED loans appear (active-only states like FL are excluded)
        settled = silver_df[silver_df["is_default"].notna()]
        states_settled = set(settled["addr_state"].dropna().unique())
        states_in_mart = set(out["addr_state"].unique())
        assert states_in_mart == states_settled

    def test_dominant_purpose_column_added(self, silver_df):
        out = build_geo_distribution(silver_df)
        assert "dominant_purpose" in out.columns

    def test_default_rate_within_bounds(self, silver_df):
        out = build_geo_distribution(silver_df)
        assert out["default_rate"].between(0, 100).all()
