"""
ML Feature Engineering for Early Warning System (EWS) - Version 2

This module provides robust feature engineering for student attendance data.
Features are designed to support both ML-based prediction and rule-based triggers
for the hybrid EWS engine.

v2 Changes:
- Global Active Days calculation with adaptive thresholds
- Recording quality features (completeness, longest gap)
- Weekend exclusion option
- Data quality separated from behavioral risk

Technical Success Criteria:
- Handle 88 students efficiently
- Support interpretable features for LogisticRegression
- Consistent feature list between training and prediction
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple, Set
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# FEATURE CONFIGURATION (v2)
# =============================================================================

# Rule-based thresholds for automatic RED classification
ABSENT_RATIO_THRESHOLD = 0.15  # If absent_ratio > 15%, trigger rule
ABSENT_COUNT_THRESHOLD = 5  # If total_absent > 5, trigger rule

# Global Active Days configuration
ACTIVE_DAY_THRESHOLDS = [0.6, 0.5, 0.4]  # Try in order, fallback progressively
MIN_ACTIVE_STUDENTS = 5  # Minimum students to consider a day "active"
MIN_ACTIVE_DAYS = 5  # Minimum expected days for valid training
EXCLUDE_WEEKENDS = True  # Filter out Sat/Sun from school days

# Data quality thresholds
LOW_COMPLETENESS_THRESHOLD = 0.7  # Below this = low data quality

# Feature columns (must be consistent between training and prediction)
# NOTE: absent_ratio, absent_count, late_ratio excluded to prevent target leakage
# (these directly define the at-risk label in training)
FEATURE_COLUMNS = [
    # Behavioral features (derivative signals only)
    "late_count",
    "present_count",
    "permission_count",
    "sick_count",
    "total_days",
    "attendance_ratio",
    "trend_score",
    "is_rule_triggered",
    # Recording quality features (v2)
    "recording_completeness",
    "longest_gap_days",
]


# =============================================================================
# GLOBAL ACTIVE DAYS CALCULATION (v2)
# =============================================================================


def calculate_global_active_days(df: pd.DataFrame) -> Tuple[int, List]:
    """
    Calculate expected school days using global activity with adaptive fallback.

    A "school day" is defined as a day where >= threshold of students have records.
    Uses adaptive thresholds (0.6 → 0.5 → 0.4) with MIN_ACTIVE_DAYS guardrail.

    Args:
        df: DataFrame with 'nis' and 'date' columns

    Returns:
        Tuple of (expected_days, list_of_active_dates)
    """
    if df.empty or "date" not in df.columns:
        return 0, []

    df = df.copy()
    # Normalize to datetime then extract date for consistent comparison
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # Filter weekends if configured
    if EXCLUDE_WEEKENDS:
        df = df[df["date"].apply(lambda d: d.weekday() < 5)]  # Mon=0, Sun=6

    if df.empty:
        return 0, []

    total_students = df["nis"].nunique()

    # Count unique students per date
    records_per_date = df.groupby("date")["nis"].nunique()

    # Try thresholds in order until we get MIN_ACTIVE_DAYS
    for threshold in ACTIVE_DAY_THRESHOLDS:
        min_students = max(MIN_ACTIVE_STUDENTS, int(total_students * threshold))
        active_dates_mask = records_per_date >= min_students
        # Return as list of date objects (not Timestamps)
        active_dates = list(records_per_date[active_dates_mask].index)

        if len(active_dates) >= MIN_ACTIVE_DAYS:
            logger.info(
                f"Global active days: {len(active_dates)} (threshold={threshold:.0%}, "
                f"min_students={min_students})"
            )
            return len(active_dates), active_dates

    # Fallback: use all unique dates (with warning)
    all_dates = list(records_per_date.index)
    logger.warning(
        f"Could not reach {MIN_ACTIVE_DAYS} active days with any threshold. "
        f"Using all {len(all_dates)} unique dates."
    )
    return len(all_dates), all_dates


def calculate_longest_gap(student_dates: Set, active_dates: List) -> int:
    """
    Calculate longest consecutive active days WITHOUT a record for a student.

    Uses active_dates (school days), not raw calendar → avoids weekend/holiday gaps.

    Args:
        student_dates: Set of dates where student has records
        active_dates: List of active school dates (from global calculation)

    Returns:
        Integer count of longest consecutive gap
    """
    if not active_dates:
        return 0

    # Convert to set for O(1) lookup
    student_date_set = set(
        pd.to_datetime(d).date() if not isinstance(d, date) else d
        for d in student_dates
    )

    # Sort active dates
    sorted_active = sorted(
        pd.to_datetime(d).date() if not isinstance(d, date) else d for d in active_dates
    )

    # Find longest consecutive days without record
    max_gap = 0
    current_gap = 0

    for active_date in sorted_active:
        if active_date not in student_date_set:
            current_gap += 1
            max_gap = max(max_gap, current_gap)
        else:
            current_gap = 0

    return max_gap


def calculate_recording_completeness(recorded_days: int, expected_days: int) -> float:
    """
    Calculate recording completeness with proper edge case handling.

    Args:
        recorded_days: Number of days student has records
        expected_days: Expected school days from global calculation

    Returns:
        Float between 0.0 and 1.0
    """
    if expected_days == 0:
        return 0.0  # No expected days = no completeness possible
    return min(recorded_days / expected_days, 1.0)  # Clamp to max 1.0


# =============================================================================
# CORE FEATURE ENGINEERING (v2)
# =============================================================================


def engineer_features_from_df(
    df: pd.DataFrame, cutoff_date: Optional[date] = None
) -> pd.DataFrame:
    """
    Engineer features from a raw attendance DataFrame (v2).

    This is the core function used by both training (from DB) and
    validation (from mock data).

    Args:
        df: DataFrame with columns ['nis', 'date', 'status']
            - nis: Student identifier
            - date: Attendance date (datetime or date object)
            - status: One of 'Present', 'Absent', 'Late', 'Sick', 'Permission'
        cutoff_date: Optional cutoff date for temporal split validation.
                     If provided, only records BEFORE this date are used.
                     Prevents temporal leakage in time-based train/test splits.

    Returns:
        DataFrame with engineered features, indexed by 'nis'
    """
    if df.empty:
        logger.warning("Empty DataFrame provided for feature engineering")
        return pd.DataFrame(columns=["nis"] + FEATURE_COLUMNS)

    # Normalize date column to date objects (single source of truth)
    df = df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date

    # Apply cutoff date filter for temporal split validation
    if cutoff_date is not None:
        if isinstance(cutoff_date, str):
            cutoff_date = pd.to_datetime(cutoff_date).date()
        df = df[df["date"] < cutoff_date]
        logger.info(
            f"Applied temporal cutoff: using {len(df)} records before {cutoff_date}"
        )

    # Normalize status to title case
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

    # Build features DataFrame
    features = pd.DataFrame()
    features["nis"] = status_counts["nis"]
    features["absent_count"] = status_counts["Absent"].astype(
        int
    )  # Explicit absences only
    features["late_count"] = status_counts["Late"].astype(int)
    features["present_count"] = status_counts["Present"].astype(int)
    features["permission_count"] = status_counts["Permission"].astype(int)
    features["sick_count"] = status_counts["Sick"].astype(int)

    # Total RECORDED attendance days (days with any record)
    features["recorded_days"] = (
        features["absent_count"]
        + features["late_count"]
        + features["present_count"]
        + features["permission_count"]
        + features["sick_count"]
    )

    # ==========================================================================
    # GLOBAL ACTIVE DAYS (v2) - More robust than max per student
    # ==========================================================================
    expected_days, active_dates = calculate_global_active_days(df)

    # Ensure total_days is exactly len(active_dates) for consistency
    features["total_days"] = len(active_dates)

    if active_dates:
        logger.info(
            f"Expected school days: {len(active_dates)}, "
            f"Date range: {min(active_dates).strftime('%Y-%m-%d')} to "
            f"{max(active_dates).strftime('%Y-%m-%d')}"
        )
    else:
        logger.warning("No active dates found - ratios will default to 0.0")

    # ==========================================================================
    # RECORDING QUALITY FEATURES (v2)
    # ==========================================================================

    # Recording completeness (clamped 0-1)
    features["recording_completeness"] = features["recorded_days"].apply(
        lambda x: calculate_recording_completeness(x, expected_days)
    )

    # Longest gap calculation (against active dates, not calendar)
    if active_dates:
        student_dates_map = df.groupby("nis")["date"].apply(set).to_dict()
        features["longest_gap_days"] = features["nis"].apply(
            lambda nis: calculate_longest_gap(
                student_dates_map.get(nis, set()), active_dates
            )
        )
    else:
        features["longest_gap_days"] = 0

    # ==========================================================================
    # RATIO CALCULATIONS (use counts on ACTIVE school days only)
    # ==========================================================================

    # Compute per-student status counts restricted to active dates
    # Use set for O(1) lookup - dates are already normalized to date objects
    active_dates_set = set(active_dates) if active_dates else set()

    if active_dates_set:
        # Filter to active domain only
        df_active = df[df["date"].isin(active_dates_set)]
        logger.info(
            f"Active filter: {len(df)} total → {len(df_active)} active-domain records"
        )

        status_counts_active = df_active.pivot_table(
            index="nis", columns="status", aggfunc="size", fill_value=0
        ).reset_index()

        # Ensure all status columns exist in active subset
        for status in ["Present", "Absent", "Late", "Sick", "Permission"]:
            if status not in status_counts_active.columns:
                status_counts_active[status] = 0

        # Map active counts to features by nis
        active_map = status_counts_active.set_index("nis")

        # Helper to fetch active count safely
        def _get_active_count(nis_value: str, col: str) -> int:
            try:
                return (
                    int(active_map.at[nis_value, col])
                    if nis_value in active_map.index
                    else 0
                )
            except Exception:
                return 0

        features["_present_count_active"] = features["nis"].apply(
            lambda n: _get_active_count(n, "Present")
        )
        features["_absent_count_active"] = features["nis"].apply(
            lambda n: _get_active_count(n, "Absent")
        )
        features["_late_count_active"] = features["nis"].apply(
            lambda n: _get_active_count(n, "Late")
        )
    else:
        features["_present_count_active"] = 0
        features["_absent_count_active"] = 0
        features["_late_count_active"] = 0

    # Use ACTIVE counts over expected_days to avoid ratios > 1
    # Guard division by zero
    total_days_val = len(active_dates) if active_dates else 0
    if total_days_val == 0:
        logger.warning(
            "Division by zero guard: total_days=0, setting all ratios to 0.0"
        )
        features["absent_ratio"] = 0.0
        features["late_ratio"] = 0.0
        features["attendance_ratio"] = 0.0
    else:
        denom = features["total_days"].replace(0, np.nan)
        features["absent_ratio"] = (features["_absent_count_active"] / denom).fillna(
            0.0
        )
        features["late_ratio"] = (features["_late_count_active"] / denom).fillna(0.0)
        features["attendance_ratio"] = (
            features["_present_count_active"] / denom
        ).fillna(0.0)

    # ==========================================================================
    # INVARIANT CHECK: ratios should not exceed 1.0 (bug detection)
    # ==========================================================================
    for col in ["absent_ratio", "late_ratio", "attendance_ratio"]:
        violations = features[features[col] > 1.0 + 1e-6]
        if len(violations) > 0:
            # Log max 10 samples to avoid log explosion
            sample_violations = violations.head(10)[["nis", col, "total_days"]].to_dict(
                "records"
            )
            max_ratio = violations[col].max()
            logger.warning(
                f"INVARIANT VIOLATION: {col} > 1.0 for {len(violations)} students "
                f"(max={max_ratio:.3f}). Samples: {sample_violations}"
            )

    # Safety net clip (should not trigger if logic is correct)
    features["absent_ratio"] = features["absent_ratio"].clip(lower=0.0, upper=1.0)
    features["late_ratio"] = features["late_ratio"].clip(lower=0.0, upper=1.0)
    features["attendance_ratio"] = features["attendance_ratio"].clip(
        lower=0.0, upper=1.0
    )

    # Calculate trend for last 7 days per student
    # NOTE: _calculate_trend_scores returns Series indexed by 'nis', but features
    # DataFrame has default 0..N-1 index. Use .map() to align correctly.
    trend_series = _calculate_trend_scores(df)  # index = nis
    features["trend_score"] = features["nis"].map(trend_series).fillna(0.0)

    # Rule-based trigger (for hybrid system) - behavioral only
    features["is_rule_triggered"] = (
        (features["absent_ratio"] > ABSENT_RATIO_THRESHOLD)
        | (features["absent_count"] > ABSENT_COUNT_THRESHOLD)
    ).astype(int)

    # Drop intermediate columns
    features = features.drop(
        columns=[
            "recorded_days",
            "_present_count_active",
            "_absent_count_active",
            "_late_count_active",
        ],
        errors="ignore",
    )

    # Fill any remaining NaN values with 0
    features = features.fillna(0)

    # Log data quality summary
    low_quality_count = (
        features["recording_completeness"] < LOW_COMPLETENESS_THRESHOLD
    ).sum()
    if low_quality_count > 0:
        logger.warning(
            f"Data quality: {low_quality_count}/{len(features)} students have "
            f"recording_completeness < {LOW_COMPLETENESS_THRESHOLD:.0%}"
        )

    logger.info(f"Engineered features for {len(features)} students (v2)")

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
        return pd.Series(0.0, index=df["nis"].unique())

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    max_date = df["date"].max()

    recent_start = max_date - timedelta(days=7)
    previous_start = max_date - timedelta(days=14)

    def calc_good_rate(group):
        if len(group) == 0:
            return 0.5  # Neutral if no data
        good_count = (group["status"] == "Present").sum()
        return good_count / len(group)

    trends = {}

    for nis in df["nis"].unique():
        student_df = df[df["nis"] == nis]

        recent_data = student_df[student_df["date"] > recent_start]
        recent_rate = calc_good_rate(recent_data)

        previous_data = student_df[
            (student_df["date"] > previous_start) & (student_df["date"] <= recent_start)
        ]
        previous_rate = calc_good_rate(previous_data)

        trends[nis] = recent_rate - previous_rate

    return pd.Series(trends)


# =============================================================================
# DATA QUALITY FLAG (v2) - Separate from behavioral risk
# =============================================================================


def get_data_quality_flags(features_df: pd.DataFrame) -> pd.Series:
    """
    Flag students with low recording completeness.

    This is SEPARATE from at-risk labeling - it indicates data quality,
    not student behavior.

    Args:
        features_df: DataFrame with recording_completeness column

    Returns:
        Boolean Series where True = low data quality
    """
    if "recording_completeness" not in features_df.columns:
        return pd.Series(False, index=features_df.index)

    return features_df["recording_completeness"] < LOW_COMPLETENESS_THRESHOLD


# =============================================================================
# DATABASE INTEGRATION
# =============================================================================


def engineer_features() -> pd.DataFrame:
    """
    Fetches attendance records from DB and computes features for ML.

    This function is called during training to get real data from the database.

    Returns:
        DataFrame with engineered features
    """
    from src.domain.models import AttendanceDaily
    from src.app.extensions import db

    session = db.session

    try:
        records = session.query(AttendanceDaily).all()

        if not records:
            logger.warning("No attendance records found in database")
            return pd.DataFrame(columns=["nis"] + FEATURE_COLUMNS)

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
        # For single student, we need global context
        # Fetch ALL attendance to calculate global active days
        all_records = session.query(AttendanceDaily).all()

        if not all_records:
            logger.warning(f"No attendance records found")
            return {col: 0 for col in FEATURE_COLUMNS}

        # Convert to DataFrame
        all_data = [
            {"nis": r.student_nis, "date": r.attendance_date, "status": r.status}
            for r in all_records
        ]

        df = pd.DataFrame(all_data)
        features_df = engineer_features_from_df(df)

        if features_df.empty:
            return {col: 0 for col in FEATURE_COLUMNS}

        student_features = features_df[features_df["nis"] == nis]

        if student_features.empty:
            return {col: 0 for col in FEATURE_COLUMNS}

        feature_dict = student_features.iloc[0].to_dict()
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
    # Ensure all feature columns exist
    for col in FEATURE_COLUMNS:
        if col not in features_df.columns:
            features_df[col] = 0

    X = features_df[FEATURE_COLUMNS].copy()

    for col in X.columns:
        if col in ["is_rule_triggered"]:
            X[col] = X[col].astype(int)
        else:
            X[col] = X[col].astype(float)

    X = X.fillna(0)

    return X
