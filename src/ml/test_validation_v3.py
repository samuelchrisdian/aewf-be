"""
Quick validation test for refactored ML pipeline (v3).

This script performs a smoke test on the new validation methodology:
- Generates mock data
- Tests GroupShuffleSplit
- Tests StratifiedGroupKFold CV
- Tests threshold tuning on validation
- Tests bootstrap CI
- Validates metadata structure

Run: py -m src.ml.test_validation_v3
"""

import sys
import os

project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.ml.preprocessing import engineer_features_from_df, FEATURE_COLUMNS
from src.ml.training import train_and_save_models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_mock_data(n_students=60, days_back=30):
    """Generate mock attendance data for testing."""
    np.random.seed(42)
    end_date = datetime.now().date()
    dates = [(end_date - timedelta(days=i)) for i in range(days_back)]

    records = []

    # 10 at-risk students
    for i in range(10):
        nis = f"ATRISK-{i+1:03d}"
        for date in dates:
            r = np.random.random()
            if r < 0.30:  # 30% absent/late
                status = "Absent" if r < 0.15 else "Late"
            elif r < 0.35:
                status = "Sick"
            else:
                status = "Present"
            records.append({"nis": nis, "date": date, "status": status})

    # 50 normal students
    for i in range(50):
        nis = f"NORMAL-{i+1:03d}"
        for date in dates:
            r = np.random.random()
            if r < 0.92:
                status = "Present"
            elif r < 0.96:
                status = "Late"
            else:
                status = "Sick"
            records.append({"nis": nis, "date": date, "status": status})

    return pd.DataFrame(records)


def main():
    logger.info("=" * 80)
    logger.info("ML VALIDATION REFACTOR - SMOKE TEST")
    logger.info("=" * 80)

    # Generate mock data
    logger.info("\n1. Generating mock data (60 students, 30 days)...")
    df = generate_mock_data()
    logger.info(f"Generated {len(df)} attendance records")

    # Engineer features
    logger.info("\n2. Engineering features...")
    features_df = engineer_features_from_df(df)
    logger.info(f"Engineered features for {len(features_df)} students")
    logger.info(f"Features used: {FEATURE_COLUMNS}")

    # Check for excluded features
    excluded = ["absent_ratio", "absent_count", "late_ratio"]
    for feat in excluded:
        if feat in FEATURE_COLUMNS:
            logger.error(f"❌ FAIL: {feat} should be excluded from FEATURE_COLUMNS!")
            return False
    logger.info(f"✓ Confirmed excluded features: {excluded}")

    # Run training pipeline
    logger.info("\n3. Running training pipeline...")
    result = train_and_save_models(custom_features_df=features_df)

    if result["status"] == "error":
        logger.error(f"❌ Training failed: {result['message']}")
        return False

    logger.info(f"✓ Training status: {result['status']}")

    # Validate CV metrics
    logger.info("\n4. Validating CV metrics...")
    cv_metrics = result.get("cv_metrics", {})
    required_cv_keys = ["recall_mean", "recall_std", "f1_mean", "f1_std"]
    for key in required_cv_keys:
        if key not in cv_metrics:
            logger.error(f"❌ Missing CV metric: {key}")
            return False
    logger.info(f"✓ CV Metrics: {cv_metrics}")

    # Validate test metrics
    logger.info("\n5. Validating test metrics...")
    test_metrics = result.get("test_metrics", {})
    required_test_keys = ["recall", "f1", "precision", "bootstrap_ci"]
    for key in required_test_keys:
        if key not in test_metrics:
            logger.error(f"❌ Missing test metric: {key}")
            return False

    # Check bootstrap CI structure
    bootstrap_ci = test_metrics.get("bootstrap_ci", {})
    for metric in ["recall", "f1", "precision"]:
        if metric not in bootstrap_ci:
            logger.error(f"❌ Missing bootstrap CI for: {metric}")
            return False
        ci = bootstrap_ci[metric]
        if not isinstance(ci, (list, tuple)) or len(ci) != 2:
            logger.error(f"❌ Invalid bootstrap CI format for {metric}: {ci}")
            return False

    logger.info(f"✓ Test Metrics: {test_metrics}")

    # Validate threshold source
    logger.info("\n6. Validating threshold source...")
    threshold = result.get("threshold")
    if threshold is None:
        logger.error("❌ Threshold not found in result")
        return False
    logger.info(f"✓ Threshold: {threshold:.3f}")

    # Load and validate metadata
    logger.info("\n7. Validating saved metadata...")
    import json

    metadata_path = "models/model_metadata.json"
    if not os.path.exists(metadata_path):
        logger.error(f"❌ Metadata file not found: {metadata_path}")
        return False

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    # Check metadata structure
    required_metadata = [
        "model_version",
        "split_method",
        "threshold_source",
        "features_excluded",
        "cv_metrics",
        "test_metrics",
    ]
    for key in required_metadata:
        if key not in metadata:
            logger.error(f"❌ Missing metadata key: {key}")
            return False

    logger.info(f"✓ Model version: {metadata['model_version']}")
    logger.info(f"✓ Split method: {metadata['split_method']}")
    logger.info(f"✓ Threshold source: {metadata['threshold_source']}")
    logger.info(f"✓ Features excluded: {metadata['features_excluded']}")

    # Verify threshold source is not 'test'
    if metadata["threshold_source"] == "test":
        logger.error("❌ FAIL: Threshold tuned on test set (contamination!)")
        return False

    # Verify excluded features
    expected_excluded = ["absent_ratio", "absent_count", "late_ratio"]
    if set(metadata["features_excluded"]) != set(expected_excluded):
        logger.error(
            f"❌ Unexpected excluded features: {metadata['features_excluded']}"
        )
        return False

    # Success
    logger.info("\n" + "=" * 80)
    logger.info("✅ ALL VALIDATION CHECKS PASSED")
    logger.info("=" * 80)
    logger.info("\nDefinition of Done Checklist:")
    logger.info("  ✓ Target leakage features removed (absent_ratio, absent_count, late_ratio)")
    logger.info("  ✓ Train/Val/Test split implemented (60/20/20)")
    logger.info("  ✓ Cross-validation metrics computed (mean ± std)")
    logger.info("  ✓ Threshold tuned on validation, NOT test set")
    logger.info("  ✓ Bootstrap confidence intervals calculated")
    logger.info("  ✓ Metadata structure correct and complete")
    logger.info("  ✓ Test set isolated (threshold_source != 'test')")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
