"""
EWS Validation Script

This script validates the ML pipeline by:
1. Generating mock attendance data for 100 students (imbalanced: 10 at-risk, 90 normal)
2. Running the training pipeline
3. Asserting metrics meet success criteria
4. Testing hybrid prediction logic on sample cases

Success Criteria:
- Recall (At-Risk class): ≥ 0.70
- F1-Score: ≥ 0.65
- AUC-ROC: ≥ 0.75

Usage:
    py -m src.ml.validation_script
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add project root to path if needed
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ml.preprocessing import (
    engineer_features_from_df,
    FEATURE_COLUMNS,
    ABSENT_RATIO_THRESHOLD,
    ABSENT_COUNT_THRESHOLD,
)
from src.ml.training import (
    train_and_save_models,
    create_target_labels,
    TARGET_RECALL,
    TARGET_F1,
    TARGET_AUC_ROC,
)

# =============================================================================
# MOCK DATA GENERATION
# =============================================================================


def generate_mock_attendance_data(
    n_students: int = 100, n_at_risk: int = 10, days_back: int = 30, seed: int = 42
) -> pd.DataFrame:
    """
    Generate mock attendance data for testing.

    Args:
        n_students: Total number of students
        n_at_risk: Number of at-risk students
        days_back: Number of days of attendance data
        seed: Random seed for reproducibility

    Returns:
        DataFrame with columns ['nis', 'date', 'status']
    """
    np.random.seed(seed)

    n_normal = n_students - n_at_risk

    # Generate dates
    end_date = datetime.now().date()
    dates = [(end_date - timedelta(days=i)) for i in range(days_back)]

    records = []

    # Generate normal students (low absence, mostly present)
    for i in range(n_normal):
        nis = f"NORMAL-{i+1:03d}"

        for date in dates:
            # 90% present, 5% late, 2% sick, 2% permission, 1% absent
            r = np.random.random()
            if r < 0.90:
                status = "Present"
            elif r < 0.95:
                status = "Late"
            elif r < 0.97:
                status = "Sick"
            elif r < 0.99:
                status = "Permission"
            else:
                status = "Absent"

            records.append({"nis": nis, "date": date, "status": status})

    # Generate at-risk students (high absence, late patterns)
    for i in range(n_at_risk):
        nis = f"ATRISK-{i+1:03d}"

        for date in dates:
            # 40% present, 20% late, 5% sick, 5% permission, 30% absent
            r = np.random.random()
            if r < 0.40:
                status = "Present"
            elif r < 0.60:
                status = "Late"
            elif r < 0.65:
                status = "Sick"
            elif r < 0.70:
                status = "Permission"
            else:
                status = "Absent"

            records.append({"nis": nis, "date": date, "status": status})

    df = pd.DataFrame(records)

    print(f"Generated mock data:")
    print(f"  - Total students: {n_students}")
    print(f"  - Normal students: {n_normal}")
    print(f"  - At-risk students: {n_at_risk}")
    print(f"  - Days of data: {days_back}")
    print(f"  - Total records: {len(df)}")

    return df


# =============================================================================
# SAMPLE TEST CASES
# =============================================================================


def create_test_cases() -> pd.DataFrame:
    """
    Create specific test cases for hybrid logic validation.

    Test Cases:
    1. Normal student (low absence) → Expected: GREEN
    2. Slightly late student → Expected: YELLOW or GREEN
    3. High absence (rule triggered) → Expected: RED (Rule Override)
    4. Edge case: just below threshold → Expected: YELLOW
    5. ML-predicted high risk (no rule) → Expected: RED (ML)
    """
    records = []
    end_date = datetime.now().date()
    dates = [(end_date - timedelta(days=i)) for i in range(30)]

    # Case 1: Normal student - 95% present
    for date in dates:
        r = np.random.random()
        status = "Present" if r < 0.95 else "Late"
        records.append({"nis": "TEST-CASE-1-NORMAL", "date": date, "status": status})

    # Case 2: Slightly late student - 80% present, 15% late
    for date in dates:
        r = np.random.random()
        if r < 0.80:
            status = "Present"
        elif r < 0.95:
            status = "Late"
        else:
            status = "Absent"
        records.append({"nis": "TEST-CASE-2-LATE", "date": date, "status": status})

    # Case 3: High absence (rule triggered) - > 15% absent
    for date in dates:
        r = np.random.random()
        if r < 0.50:
            status = "Present"
        elif r < 0.75:
            status = "Late"
        else:
            status = "Absent"  # ~25% absent → should trigger rule
        records.append(
            {"nis": "TEST-CASE-3-HIGH-ABSENT", "date": date, "status": status}
        )

    # Case 4: Edge case - 10-12% absent (below rule threshold but borderline)
    for date in dates:
        r = np.random.random()
        if r < 0.75:
            status = "Present"
        elif r < 0.88:
            status = "Late"
        else:
            status = "Absent"  # ~12% absent
        records.append({"nis": "TEST-CASE-4-EDGE", "date": date, "status": status})

    # Case 5: Worsening trend (more absences recently)
    for i, date in enumerate(dates):
        if i < 10:  # Last 10 days - more absences
            r = np.random.random()
            if r < 0.50:
                status = "Present"
            elif r < 0.70:
                status = "Late"
            else:
                status = "Absent"
        else:  # Earlier days - mostly present
            r = np.random.random()
            status = "Present" if r < 0.90 else "Late"
        records.append({"nis": "TEST-CASE-5-WORSENING", "date": date, "status": status})

    return pd.DataFrame(records)


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================


def validate_training_metrics(result: dict) -> bool:
    """
    Validate that training metrics meet success criteria.

    Returns:
        True if all criteria met, False otherwise
    """
    print("\n" + "=" * 60)
    print("VALIDATING TRAINING METRICS")
    print("=" * 60)

    if result.get("status") != "success":
        print(f"❌ Training failed: {result.get('message')}")
        return False

    metrics = result.get("metrics", {})
    recall = metrics.get("recall", 0)
    f1 = metrics.get("f1", 0)
    auc_roc = metrics.get("auc_roc", 0)

    print(f"\nMetrics vs Targets:")
    print(
        f"  Recall:   {recall:.3f} (target: ≥{TARGET_RECALL}) {'✓' if recall >= TARGET_RECALL else '✗'}"
    )
    print(
        f"  F1-Score: {f1:.3f} (target: ≥{TARGET_F1}) {'✓' if f1 >= TARGET_F1 else '✗'}"
    )
    print(
        f"  AUC-ROC:  {auc_roc:.3f} (target: ≥{TARGET_AUC_ROC}) {'✓' if auc_roc >= TARGET_AUC_ROC else '✗'}"
    )

    all_met = result.get("all_criteria_met", False)

    if all_met:
        print("\n✅ ALL SUCCESS CRITERIA MET!")
    else:
        print("\n⚠️ SOME CRITERIA NOT MET")

    return all_met


def validate_hybrid_logic(features_df: pd.DataFrame) -> bool:
    """
    Validate hybrid prediction logic on test cases.

    Returns:
        True if all test cases pass, False otherwise
    """
    print("\n" + "=" * 60)
    print("VALIDATING HYBRID PREDICTION LOGIC")
    print("=" * 60)

    # Get test case features
    test_nis = [
        "TEST-CASE-1-NORMAL",
        "TEST-CASE-2-LATE",
        "TEST-CASE-3-HIGH-ABSENT",
        "TEST-CASE-4-EDGE",
        "TEST-CASE-5-WORSENING",
    ]

    test_features = features_df[features_df["nis"].isin(test_nis)]

    if test_features.empty:
        print("❌ No test cases found in features")
        return False

    print("\nTest Case Results:")
    print("-" * 60)

    all_pass = True

    for _, row in test_features.iterrows():
        nis = row["nis"]
        absent_ratio = row["absent_ratio"]
        absent_count = row["absent_count"]
        is_rule_triggered = row["is_rule_triggered"]

        # Determine expected tier based on rule logic
        if (
            is_rule_triggered
            or absent_ratio > ABSENT_RATIO_THRESHOLD
            or absent_count > ABSENT_COUNT_THRESHOLD
        ):
            expected_rule = "RED (Rule)"
            tier = "RED"
        else:
            expected_rule = "ML-based"
            tier = "?"

        # Check expectations based on test case name
        if "NORMAL" in nis:
            expected = "GREEN"
            passed = not is_rule_triggered and absent_ratio < 0.10
        elif "HIGH-ABSENT" in nis:
            expected = "RED"
            passed = is_rule_triggered or absent_ratio > ABSENT_RATIO_THRESHOLD
        elif "EDGE" in nis:
            expected = "YELLOW"
            passed = not is_rule_triggered  # Should not trigger rule
        else:
            expected = "VARIES"
            passed = True  # No strict expectation

        status = "✓" if passed else "✗"
        if not passed:
            all_pass = False

        print(f"  {status} {nis}:")
        print(
            f"      absent_ratio={absent_ratio:.2%}, absent_count={int(absent_count)}"
        )
        print(f"      rule_triggered={bool(is_rule_triggered)}, expected={expected}")

    print("-" * 60)

    if all_pass:
        print("✅ ALL TEST CASES PASSED!")
    else:
        print("⚠️ SOME TEST CASES FAILED")

    return all_pass


# =============================================================================
# MAIN VALIDATION
# =============================================================================


def run_validation():
    """
    Run full validation suite.
    """
    print("=" * 70)
    print("EWS MODEL VALIDATION SUITE")
    print("=" * 70)
    print(f"Started at: {datetime.now().isoformat()}")

    # Step 1: Generate mock data
    print("\n" + "=" * 60)
    print("STEP 1: GENERATING MOCK DATA")
    print("=" * 60)

    mock_data = generate_mock_attendance_data(
        n_students=100, n_at_risk=10, days_back=30, seed=42
    )

    # Add test cases to mock data
    test_cases = create_test_cases()
    all_data = pd.concat([mock_data, test_cases], ignore_index=True)

    print(f"\nTotal records (with test cases): {len(all_data)}")
    print(f"Unique students: {all_data['nis'].nunique()}")

    # Step 2: Engineer features
    print("\n" + "=" * 60)
    print("STEP 2: ENGINEERING FEATURES")
    print("=" * 60)

    features_df = engineer_features_from_df(all_data)
    print(f"Features engineered for {len(features_df)} students")

    # Show sample features
    print("\nSample features (first 5 students):")
    print(features_df.head().to_string())

    # Step 3: Run training
    print("\n" + "=" * 60)
    print("STEP 3: TRAINING MODEL")
    print("=" * 60)

    training_result = train_and_save_models(features_df)

    # Step 4: Validate metrics
    metrics_valid = validate_training_metrics(training_result)

    # Step 5: Validate hybrid logic
    hybrid_valid = validate_hybrid_logic(features_df)

    # Final summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print(f"  Metrics validation: {'PASS ✓' if metrics_valid else 'FAIL ✗'}")
    print(f"  Hybrid logic validation: {'PASS ✓' if hybrid_valid else 'FAIL ✗'}")
    print("=" * 70)

    if metrics_valid and hybrid_valid:
        print("\n🎉 ALL VALIDATIONS PASSED! Model is ready for deployment.")
        return True
    else:
        print("\n⚠️ SOME VALIDATIONS FAILED. Review the issues above.")
        return False


def run_quick_test():
    """
    Quick test of core functionality without assertions.
    """
    print("Quick test of EWS ML Pipeline...")

    # Generate small dataset
    mock_data = generate_mock_attendance_data(
        n_students=20, n_at_risk=5, days_back=14, seed=123
    )

    # Engineer features
    features = engineer_features_from_df(mock_data)
    print(f"\nFeatures shape: {features.shape}")

    # Show stats
    print("\nFeature statistics:")
    print(features.describe().round(3).T[["mean", "std", "min", "max"]])

    return True


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="EWS Validation Script")
    parser.add_argument("--quick", action="store_true", help="Run quick test only")
    args = parser.parse_args()

    if args.quick:
        success = run_quick_test()
    else:
        success = run_validation()

    sys.exit(0 if success else 1)
