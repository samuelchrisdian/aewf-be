"""
Unit tests for ML Preprocessing module.
Tests for feature engineering and ratio calculations.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta

from src.ml.preprocessing import (
    engineer_features_from_df,
    calculate_global_active_days,
    calculate_longest_gap,
    calculate_recording_completeness,
    FEATURE_COLUMNS,
)


class TestCalculateGlobalActiveDays:
    """Unit tests for calculate_global_active_days function."""

    def test_empty_dataframe_returns_zero(self):
        """Test that empty DataFrame returns 0 active days."""
        df = pd.DataFrame(columns=["nis", "date", "status"])
        expected_days, active_dates = calculate_global_active_days(df)
        assert expected_days == 0
        assert active_dates == []

    def test_single_student_multiple_days(self):
        """Test with a single student having records on multiple days."""
        dates = [date(2025, 1, 6) + timedelta(days=i) for i in range(5)]  # Mon-Fri
        df = pd.DataFrame(
            {
                "nis": ["S001"] * 5,
                "date": dates,
                "status": ["Present"] * 5,
            }
        )
        expected_days, active_dates = calculate_global_active_days(df)
        # With only 1 student, threshold won't be met but fallback kicks in
        assert expected_days == 5
        assert len(active_dates) == 5

    def test_multiple_students_threshold(self):
        """Test that threshold correctly identifies active days."""
        # 10 students, all have records on same 5 days
        students = [f"S{i:03d}" for i in range(10)]
        dates = [date(2025, 1, 6) + timedelta(days=i) for i in range(5)]  # Mon-Fri

        records = []
        for nis in students:
            for d in dates:
                records.append({"nis": nis, "date": d, "status": "Present"})

        df = pd.DataFrame(records)
        expected_days, active_dates = calculate_global_active_days(df)

        assert expected_days == 5
        assert len(active_dates) == 5

    def test_weekends_excluded(self):
        """Test that weekend days are excluded from active days."""
        # Include Saturday and Sunday
        dates = [
            date(2025, 1, 6),  # Monday
            date(2025, 1, 7),  # Tuesday
            date(2025, 1, 11),  # Saturday
            date(2025, 1, 12),  # Sunday
        ]
        students = [f"S{i:03d}" for i in range(10)]

        records = []
        for nis in students:
            for d in dates:
                records.append({"nis": nis, "date": d, "status": "Present"})

        df = pd.DataFrame(records)
        expected_days, active_dates = calculate_global_active_days(df)

        # Only Mon & Tue should be counted (weekends excluded)
        assert expected_days == 2


class TestEngineerFeaturesFromDf:
    """Unit tests for engineer_features_from_df function."""

    @pytest.fixture
    def sample_attendance_df(self):
        """Create sample attendance data for multiple students."""
        # 5 students, 10 weekdays of attendance
        students = [f"S{i:03d}" for i in range(5)]
        # Using dates that are weekdays (Mon-Fri, twice)
        dates = [
            date(2025, 1, 6),
            date(2025, 1, 7),
            date(2025, 1, 8),
            date(2025, 1, 9),
            date(2025, 1, 10),  # Week 1
            date(2025, 1, 13),
            date(2025, 1, 14),
            date(2025, 1, 15),
            date(2025, 1, 16),
            date(2025, 1, 17),  # Week 2
        ]

        records = []
        for nis in students:
            for d in dates:
                records.append({"nis": nis, "date": d, "status": "Present"})

        return pd.DataFrame(records)

    def test_attendance_ratio_never_exceeds_one(self, sample_attendance_df):
        """Critical test: attendance_ratio must always be <= 1.0."""
        features = engineer_features_from_df(sample_attendance_df)

        assert (
            features["attendance_ratio"] <= 1.0
        ).all(), f"attendance_ratio exceeded 1.0: {features['attendance_ratio'].max()}"

    def test_absent_ratio_never_exceeds_one(self, sample_attendance_df):
        """Critical test: absent_ratio must always be <= 1.0."""
        features = engineer_features_from_df(sample_attendance_df)

        assert (
            features["absent_ratio"] <= 1.0
        ).all(), f"absent_ratio exceeded 1.0: {features['absent_ratio'].max()}"

    def test_late_ratio_never_exceeds_one(self, sample_attendance_df):
        """Critical test: late_ratio must always be <= 1.0."""
        features = engineer_features_from_df(sample_attendance_df)

        assert (
            features["late_ratio"] <= 1.0
        ).all(), f"late_ratio exceeded 1.0: {features['late_ratio'].max()}"

    def test_present_count_active_lte_total_days(self, sample_attendance_df):
        """Test that present_count_active <= total_days (1 record per day)."""
        features = engineer_features_from_df(sample_attendance_df)

        # Since data has 1 record per student per day, this must hold
        assert (
            features["present_count"] <= features["total_days"]
        ).all(), "present_count exceeded total_days"

    def test_total_days_matches_expected(self, sample_attendance_df):
        """Test that total_days is correct."""
        features = engineer_features_from_df(sample_attendance_df)

        # 10 weekdays expected
        assert features["total_days"].iloc[0] == 10

    def test_all_feature_columns_present(self, sample_attendance_df):
        """Test that all expected feature columns are present."""
        features = engineer_features_from_df(sample_attendance_df)

        for col in FEATURE_COLUMNS:
            assert col in features.columns, f"Missing column: {col}"

    def test_multi_month_data_correct_ratio(self):
        """
        Regression test for issue #237: Student with records spanning multiple
        months should still have attendance_ratio <= 1.0.
        """
        # Simulate the bug scenario: student has 49 records over 4 months
        # but only 16 days are "active" globally
        students = [f"S{i:03d}" for i in range(20)]

        # Create sparse data where only some days have enough students
        active_dates = [date(2025, 8, i) for i in [4, 5, 6, 7, 8, 11, 12, 13, 14, 15]]
        other_dates = [date(2025, 9, i) for i in [1, 2, 3, 4, 5]]

        records = []
        # All students have records on active_dates
        for nis in students:
            for d in active_dates:
                records.append({"nis": nis, "date": d, "status": "Present"})

        # Only one student (S000) has records on other_dates too
        for d in other_dates:
            records.append({"nis": "S000", "date": d, "status": "Present"})

        df = pd.DataFrame(records)
        features = engineer_features_from_df(df)

        # S000 has more records than others, but ratio should still be <= 1
        s000_features = features[features["nis"] == "S000"]
        assert (
            s000_features["attendance_ratio"].iloc[0] <= 1.0
        ), f"S000 attendance_ratio: {s000_features['attendance_ratio'].iloc[0]}"

    def test_empty_attendance_returns_zeros(self):
        """Test that empty DataFrame returns zero-filled features."""
        df = pd.DataFrame(columns=["nis", "date", "status"])
        features = engineer_features_from_df(df)

        assert len(features) == 0 or (features["attendance_ratio"] == 0).all()


class TestCalculateLongestGap:
    """Unit tests for calculate_longest_gap function."""

    def test_no_gap(self):
        """Test when student has record on all active days."""
        student_dates = {date(2025, 1, 6), date(2025, 1, 7), date(2025, 1, 8)}
        active_dates = [date(2025, 1, 6), date(2025, 1, 7), date(2025, 1, 8)]

        gap = calculate_longest_gap(student_dates, active_dates)
        assert gap == 0

    def test_single_day_gap(self):
        """Test when student misses 1 day."""
        student_dates = {date(2025, 1, 6), date(2025, 1, 8)}  # Missing Jan 7
        active_dates = [date(2025, 1, 6), date(2025, 1, 7), date(2025, 1, 8)]

        gap = calculate_longest_gap(student_dates, active_dates)
        assert gap == 1

    def test_consecutive_gap(self):
        """Test consecutive missing days."""
        student_dates = {date(2025, 1, 6), date(2025, 1, 10)}  # Missing 7,8,9
        active_dates = [
            date(2025, 1, 6),
            date(2025, 1, 7),
            date(2025, 1, 8),
            date(2025, 1, 9),
            date(2025, 1, 10),
        ]

        gap = calculate_longest_gap(student_dates, active_dates)
        assert gap == 3


class TestCalculateRecordingCompleteness:
    """Unit tests for calculate_recording_completeness function."""

    def test_full_completeness(self):
        """Test 100% completeness."""
        assert calculate_recording_completeness(10, 10) == 1.0

    def test_half_completeness(self):
        """Test 50% completeness."""
        assert calculate_recording_completeness(5, 10) == 0.5

    def test_zero_expected_days(self):
        """Test edge case with zero expected days."""
        assert calculate_recording_completeness(5, 0) == 0.0

    def test_clamped_to_one(self):
        """Test that completeness is clamped to 1.0 max."""
        # Edge case: more recorded than expected (shouldn't happen, but guarded)
        assert calculate_recording_completeness(15, 10) == 1.0
