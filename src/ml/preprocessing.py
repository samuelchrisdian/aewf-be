"""
ML Feature Engineering for Early Warning System (EWS)

This module provides robust feature engineering for student attendance data.
Features are designed to support both ML-based prediction and rule-based triggers
for the hybrid EWS engine.

Technical Success Criteria:
- Handle 88 students efficiently
- Support interpretable features for LogisticRegression
- Consistent feature list between training and prediction
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# FEATURE CONFIGURATION
# =============================================================================

# Rule-based thresholds for automatic RED classification
ABSENT_RATIO_THRESHOLD = 0.15  # If absent_ratio > 15%, trigger rule
ABSENT_COUNT_THRESHOLD = 5  # If total_absent > 5, trigger rule

# Feature columns (must be consistent between training and prediction)
FEATURE_COLUMNS = [
    "absent_count",
    "late_count",
    "present_count",
    "permission_count",
    "sick_count",
    "total_days",
    "absent_ratio",
    "late_ratio",
    "attendance_ratio",
    "trend_score",
    "is_rule_triggered",
]

# =============================================================================
# CORE FEATURE ENGINEERING
# =============================================================================


def engineer_features_from_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineer features from a raw attendance DataFrame.

    This is the core function used by both training (from DB) and
    validation (from mock data).

    Args:
        df: DataFrame with columns ['nis', 'date', 'status']
            - nis: Student identifier
            - date: Attendance date (datetime or date object)
            - status: One of 'Present', 'Absent', 'Late', 'Sick', 'Permission'

    Returns:
        DataFrame with engineered features, indexed by 'nis'
    """
    if df.empty:
        logger.warning("Empty DataFrame provided for feature engineering")
        return pd.DataFrame(columns=["nis"] + FEATURE_COLUMNS)

    # Ensure date column is datetime
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])

    # Normalize status to title case (handles 'present' -> 'Present', 'late' -> 'Late', etc.)
    df = df.copy()
    df["status"] = df["status"].str.strip().str.title()

    # Status columns we expect
    status_types = ["Present", "Absent", "Late", "Sick", "Permission"]

    # Count each status per student
    status_counts = df.pivot_table(
        index="nis", columns="status", aggfunc="size", fill_value=0
    ).reset_index()

    # Ensure all status columns exist
    for status in status_types:
        if status not in status_counts.columns:
            status_counts[status] = 0

    # Rename columns for clarity
    features = pd.DataFrame()
    features["nis"] = status_counts["nis"]
    features["recorded_absent"] = status_counts["Absent"].astype(
        int
    )  # Explicit absent records
    features["late_count"] = status_counts["Late"].astype(int)
    features["present_count"] = status_counts["Present"].astype(int)
    features["permission_count"] = status_counts["Permission"].astype(int)
    features["sick_count"] = status_counts["Sick"].astype(int)

    # Total RECORDED attendance days (days with any record)
    features["recorded_days"] = (
        features["recorded_absent"]
        + features["late_count"]
        + features["present_count"]
        + features["permission_count"]
        + features["sick_count"]
    )

    # ==========================================================================
    # INFERRED ABSENCES: Calculate missing school days as absences
    # ==========================================================================
    # Expected school days = maximum recorded days across all students
    # (This assumes at least one student has attendance for all school days)
    expected_school_days = features["recorded_days"].max()

    # Inferred absences = days student has no record at all
    features["inferred_absent"] = expected_school_days - features["recorded_days"]
    features["inferred_absent"] = features["inferred_absent"].clip(
        lower=0
    )  # No negative

    # Total absent = recorded absent + inferred absent (no record = absent)
    features["absent_count"] = features["recorded_absent"] + features["inferred_absent"]

    # Total days for ratio calculation = expected school days
    features["total_days"] = expected_school_days

    logger.info(
        f"Expected school days: {expected_school_days}, "
        f"Students with full attendance: {sum(features['recorded_days'] == expected_school_days)}, "
        f"Students with inferred absences: {sum(features['inferred_absent'] > 0)}"
    )

    # Calculate ratios based on EXPECTED total days (not just recorded)
    features["absent_ratio"] = np.where(
        features["total_days"] > 0,
        features["absent_count"] / features["total_days"],
        0.0,
    )

    features["late_ratio"] = np.where(
        features["total_days"] > 0, features["late_count"] / features["total_days"], 0.0
    )

    features["attendance_ratio"] = np.where(
        features["total_days"] > 0,
        features["present_count"] / features["total_days"],
        0.0,
    )

    # Calculate trend for last 7 days per student
    features["trend_score"] = _calculate_trend_scores(df)

    # Rule-based trigger (for hybrid system)
    # Now includes inferred_absent in absent_count!
    features["is_rule_triggered"] = (
        (features["absent_ratio"] > ABSENT_RATIO_THRESHOLD)
        | (features["absent_count"] > ABSENT_COUNT_THRESHOLD)
    ).astype(int)

    # Drop intermediate columns not needed for model
    features = features.drop(
        columns=["recorded_absent", "recorded_days", "inferred_absent"]
    )

    # Fill any remaining NaN values with 0
    features = features.fillna(0)

    logger.info(f"Engineered features for {len(features)} students")

    return features


def _calculate_trend_scores(df: pd.DataFrame) -> pd.Series:
    """
    Calculate attendance trend score for each student based on recent days.

    Trend Score:
    - Positive value: Improving (more present days recently)
    - Negative value: Worsening (more absent/late days recently)
    - Range: -1.0 to +1.0

    Algorithm:
    - Compare last 7 days vs previous 7 days
    - Score = (recent_good_rate - previous_good_rate)
    """
    if "date" not in df.columns:
        # No date info, return neutral trend
        return pd.Series(0.0, index=df["nis"].unique())

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    # Get the most recent date in the data
    max_date = df["date"].max()

    # Define periods
    recent_start = max_date - timedelta(days=7)
    previous_start = max_date - timedelta(days=14)

    # Good statuses (Present counts as good, others count against)
    def calc_good_rate(group):
        if len(group) == 0:
            return 0.5  # Neutral if no data
        good_count = (group["status"] == "Present").sum()
        return good_count / len(group)

    trends = {}

    for nis in df["nis"].unique():
        student_df = df[df["nis"] == nis]

        # Recent period (last 7 days)
        recent_data = student_df[student_df["date"] > recent_start]
        recent_rate = calc_good_rate(recent_data)

        # Previous period (7-14 days ago)
        previous_data = student_df[
            (student_df["date"] > previous_start) & (student_df["date"] <= recent_start)
        ]
        previous_rate = calc_good_rate(previous_data)

        # Trend score: improvement is positive
        trends[nis] = recent_rate - previous_rate

    return pd.Series(trends)


def engineer_features() -> pd.DataFrame:
    """
    Fetches attendance records from DB and computes features for ML.

    This function is called during training to get real data from the database.

    Returns:
        DataFrame with engineered features
    """
    # Import here to avoid circular imports
    from src.domain.models import AttendanceDaily
    from src.app.extensions import db

    session = db.session

    try:
        # Fetch all attendance records
        records = session.query(AttendanceDaily).all()

        if not records:
            logger.warning("No attendance records found in database")
            return pd.DataFrame(columns=["nis"] + FEATURE_COLUMNS)

        # Convert to DataFrame
        data = [
            {"nis": r.student_nis, "date": r.attendance_date, "status": r.status}
            for r in records
        ]

        df = pd.DataFrame(data)

        return engineer_features_from_df(df)

    except Exception as e:
        logger.error(f"Error engineering features from DB: {e}")
        return pd.DataFrame(columns=["nis"] + FEATURE_COLUMNS)


def engineer_features_for_student(nis: str) -> Dict:
    """
    Engineer features for a single student (used in prediction).

    Args:
        nis: Student NIS identifier

    Returns:
        Dictionary with feature values, ready for model prediction
    """
    from src.domain.models import AttendanceDaily
    from src.app.extensions import db

    session = db.session

    try:
        # Fetch student's attendance records
        records = session.query(AttendanceDaily).filter_by(student_nis=nis).all()

        if not records:
            logger.warning(f"No attendance records found for student {nis}")
            # Return default features (all zeros except is_rule_triggered)
            return {col: 0 for col in FEATURE_COLUMNS}

        # Convert to DataFrame
        data = [
            {"nis": r.student_nis, "date": r.attendance_date, "status": r.status}
            for r in records
        ]

        df = pd.DataFrame(data)
        features_df = engineer_features_from_df(df)

        if features_df.empty:
            return {col: 0 for col in FEATURE_COLUMNS}

        # Get the row for this student
        student_features = features_df[features_df["nis"] == nis]

        if student_features.empty:
            return {col: 0 for col in FEATURE_COLUMNS}

        # Convert to dictionary
        feature_dict = student_features.iloc[0].to_dict()

        # Remove 'nis' from features (it's an identifier, not a feature)
        feature_dict.pop("nis", None)

        return feature_dict

    except Exception as e:
        logger.error(f"Error engineering features for student {nis}: {e}")
        return {col: 0 for col in FEATURE_COLUMNS}


def get_feature_columns() -> List[str]:
    """
    Returns the list of feature columns used by the model.

    This ensures consistency between training and prediction.
    """
    return FEATURE_COLUMNS.copy()


def prepare_features_for_model(features_df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare features DataFrame for model input.

    Ensures:
    - Only model features are included (no 'nis')
    - Columns are in the correct order
    - All expected columns exist

    Args:
        features_df: DataFrame with engineered features

    Returns:
        DataFrame ready for model.predict()
    """
    # Create a copy with only feature columns
    X = features_df[FEATURE_COLUMNS].copy()

    # Ensure correct dtypes
    for col in X.columns:
        if col in ["is_rule_triggered"]:
            X[col] = X[col].astype(int)
        else:
            X[col] = X[col].astype(float)

    # Fill any NaN
    X = X.fillna(0)

    return X
