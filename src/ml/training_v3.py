"""
ML Model Training for Early Warning System (EWS) - Refactored Validation

This module trains a LogisticRegression model with proper validation methodology:
- Train/Val/Test 60/20/20 split with GroupShuffleSplit
- StratifiedGroupKFold CV (or GroupKFold fallback) for robust estimation
- Threshold tuning on validation set (NOT test set)
- Bootstrap confidence intervals for test metrics
- No target leakage (absent_ratio excluded from features)

Technical Success Criteria:
- Recall for At-Risk class: ≥ 0.70 (Priority: Minimize False Negatives)
- F1-Score: ≥ 0.65
- AUC-ROC: ≥ 0.75
"""

import pandas as pd
import numpy as np
import pickle
import json
import os
from datetime import datetime, timezone
from typing import Dict, Tuple, Optional, List
from collections import Counter

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (
    recall_score,
    f1_score,
    roc_auc_score,
    precision_score,
    confusion_matrix,
    classification_report,
)
from sklearn.utils import resample
from imblearn.over_sampling import SMOTE, RandomOverSampler

# Try to import StratifiedGroupKFold (sklearn >= 0.24)
try:
    from sklearn.model_selection import StratifiedGroupKFold
    HAS_STRATIFIED_GROUP_KFOLD = True
except ImportError:
    from sklearn.model_selection import GroupKFold
    HAS_STRATIFIED_GROUP_KFOLD = False
    import warnings
    warnings.warn("StratifiedGroupKFold not available. Falling back to GroupKFold.")

from src.ml.preprocessing import (
    engineer_features,
    engineer_features_from_df,
    get_feature_columns,
    prepare_features_for_model,
    get_data_quality_flags,
    FEATURE_COLUMNS,
    ABSENT_RATIO_THRESHOLD,
    LOW_COMPLETENESS_THRESHOLD,
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "ews_model.pkl")
EXPLAINER_MODEL_PATH = os.path.join(MODEL_DIR, "ews_explainer_tree.pkl")
METADATA_PATH = os.path.join(MODEL_DIR, "model_metadata.json")

# Validation configuration
TRAIN_SIZE = 0.60  # 60% for training
VAL_SIZE = 0.20    # 20% for validation (threshold tuning)
TEST_SIZE = 0.20   # 20% for final test (isolated)
CV_N_SPLITS = 3    # Reduced from 5 due to small sample size
BOOTSTRAP_ITERATIONS = 1000

# Success criteria
TARGET_RECALL = 0.70
TARGET_F1 = 0.65
TARGET_AUC_ROC = 0.75

# Model versioning
MODEL_VERSION = "v3"  # v3 = proper validation + no target leakage

# Ensure model directory exists
if not os.path.exists(MODEL_DIR):
    os.makedirs(MODEL_DIR)


# =============================================================================
# LABEL CREATION
# =============================================================================


def create_target_labels(features_df: pd.DataFrame) -> pd.Series:
    """
    Create target labels for training.

    A student is considered "At-Risk" (1) if ANY of these conditions are met:
    - late_count > 3 (frequent lateness)
    - attendance_ratio < 0.85 (low attendance rate)
    - trend_score < -0.2 (worsening attendance trend)
    - recording_completeness < 0.5 (very low data quality + behavioral risk)

    NOTE: We no longer use absent_ratio or absent_count directly (removed from features
    to prevent target leakage).

    Args:
        features_df: DataFrame with engineered features

    Returns:
        Series of binary labels (0=Normal, 1=At-Risk)
    """
    at_risk_mask = (
        (features_df["late_count"] > 3)  # More than 3 late arrivals
        | (features_df["attendance_ratio"] < 0.85)  # Less than 85% attendance
        | (features_df["trend_score"] < -0.2)  # Worsening trend
        | (
            (features_df["recording_completeness"] < 0.5)
            & (features_df["present_count"] < 10)  # Low quality + low presence
        )
    )

    return at_risk_mask.astype(int)


# =============================================================================
# DATA SPLITTING
# =============================================================================


def split_data_grouped(
    X: pd.DataFrame, y: pd.Series, groups: pd.Series, random_state: int = 42
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Split data into Train/Val/Test using GroupShuffleSplit.

    Args:
        X: Feature matrix
        y: Target labels
        groups: Student IDs (prevents same student in train and test)
        random_state: Random seed

    Returns:
        Tuple of (train_idx, val_idx, test_idx)
    """
    logger.info("=" * 60)
    logger.info("SPLITTING DATA: Train/Val/Test (60/20/20)")
    logger.info("=" * 60)

    # First split: separate test set (20%)
    gss_test = GroupShuffleSplit(
        n_splits=1, test_size=TEST_SIZE, random_state=random_state
    )
    trainval_idx, test_idx = next(gss_test.split(X, y, groups))

    # Second split: split train+val into train (75% of trainval = 60% overall)
    # and val (25% of trainval = 20% overall)
    X_trainval = X.iloc[trainval_idx]
    y_trainval = y.iloc[trainval_idx]
    groups_trainval = groups.iloc[trainval_idx]

    val_size_from_trainval = VAL_SIZE / (TRAIN_SIZE + VAL_SIZE)  # 0.25

    gss_val = GroupShuffleSplit(
        n_splits=1, test_size=val_size_from_trainval, random_state=random_state
    )
    train_idx_local, val_idx_local = next(
        gss_val.split(X_trainval, y_trainval, groups_trainval)
    )

    # Map local indices back to global indices
    train_idx = trainval_idx[train_idx_local]
    val_idx = trainval_idx[val_idx_local]

    # Log split statistics
    logger.info(f"Total samples: {len(X)}")
    logger.info(f"Train: {len(train_idx)} ({len(train_idx) / len(X):.1%})")
    logger.info(f"Val:   {len(val_idx)} ({len(val_idx) / len(X):.1%})")
    logger.info(f"Test:  {len(test_idx)} ({len(test_idx) / len(X):.1%})")

    # Log class distribution
    logger.info(f"Train class dist: {Counter(y.iloc[train_idx])}")
    logger.info(f"Val class dist:   {Counter(y.iloc[val_idx])}")
    logger.info(f"Test class dist:  {Counter(y.iloc[test_idx])}")

    return train_idx, val_idx, test_idx


# =============================================================================
# CROSS-VALIDATION
# =============================================================================


def cross_validate_groupkfold(
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    n_splits: int = CV_N_SPLITS,
) -> Tuple[pd.DataFrame, Dict]:
    """
    Perform GroupKFold (or StratifiedGroupKFold) cross-validation.

    SMOTE is applied only to training folds. Out-of-fold predictions are collected
    for threshold tuning.

    Args:
        X: Feature matrix
        y: Target labels
        groups: Student IDs
        n_splits: Number of CV folds

    Returns:
        Tuple of (oof_predictions_df, cv_metrics_dict)
    """
    logger.info("=" * 60)
    logger.info(f"CROSS-VALIDATION: {n_splits}-Fold Group CV")
    logger.info("=" * 60)

    # Initialize splitter
    if HAS_STRATIFIED_GROUP_KFOLD:
        splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)
        logger.info("Using StratifiedGroupKFold (preserves class distribution)")
    else:
        splitter = GroupKFold(n_splits=n_splits)
        logger.info("Using GroupKFold (StratifiedGroupKFold not available)")

    # Store OOF predictions
    oof_preds = np.zeros(len(X))
    oof_labels = np.zeros(len(X))

    fold_metrics = []

    for fold, (train_idx, val_idx) in enumerate(splitter.split(X, y, groups), 1):
        logger.info(f"\n--- Fold {fold}/{n_splits} ---")

        X_train_fold = X.iloc[train_idx]
        X_val_fold = X.iloc[val_idx]
        y_train_fold = y.iloc[train_idx]
        y_val_fold = y.iloc[val_idx]

        logger.info(f"Train: {len(train_idx)}, Val: {len(val_idx)}")
        logger.info(f"Train class dist: {Counter(y_train_fold)}")
        logger.info(f"Val class dist: {Counter(y_val_fold)}")

        # Apply oversampling (SMOTE with fallback to RandomOverSampler)
        try:
            minority_count = min(Counter(y_train_fold).values())
            if minority_count >= 2:
                k_neighbors = min(5, minority_count - 1)
                smote = SMOTE(random_state=42, k_neighbors=max(1, k_neighbors))
                X_train_res, y_train_res = smote.fit_resample(X_train_fold, y_train_fold)
                logger.info(f"SMOTE applied: {len(y_train_fold)} → {len(y_train_res)}")
            else:
                ros = RandomOverSampler(random_state=42)
                X_train_res, y_train_res = ros.fit_resample(X_train_fold, y_train_fold)
                logger.info(
                    f"RandomOverSampler used (minority < 2): {len(y_train_fold)} → {len(y_train_res)}"
                )
        except Exception as e:
            logger.warning(f"Oversampling failed: {e}. Using original data.")
            X_train_res, y_train_res = X_train_fold, y_train_fold

        # Train model
        model = LogisticRegression(
            class_weight="balanced", random_state=42, max_iter=1000, solver="lbfgs"
        )
        model.fit(X_train_res, y_train_res)

        # Predict on validation fold
        y_proba = model.predict_proba(X_val_fold)[:, 1]

        # Store OOF predictions
        oof_preds[val_idx] = y_proba
        oof_labels[val_idx] = y_val_fold

        # Calculate fold metrics (with default threshold 0.5)
        y_pred = (y_proba >= 0.5).astype(int)
        fold_recall = recall_score(y_val_fold, y_pred)
        fold_f1 = f1_score(y_val_fold, y_pred)
        fold_precision = precision_score(y_val_fold, y_pred, zero_division=0)

        fold_metrics.append(
            {"recall": fold_recall, "f1": fold_f1, "precision": fold_precision}
        )

        logger.info(
            f"Fold {fold} metrics (threshold=0.5): "
            f"Recall={fold_recall:.3f}, F1={fold_f1:.3f}, Precision={fold_precision:.3f}"
        )

    # Aggregate CV metrics
    cv_metrics = {
        "recall_mean": np.mean([m["recall"] for m in fold_metrics]),
        "recall_std": np.std([m["recall"] for m in fold_metrics]),
        "f1_mean": np.mean([m["f1"] for m in fold_metrics]),
        "f1_std": np.std([m["f1"] for m in fold_metrics]),
        "precision_mean": np.mean([m["precision"] for m in fold_metrics]),
        "precision_std": np.std([m["precision"] for m in fold_metrics]),
    }

    logger.info("\n" + "=" * 60)
    logger.info("CV SUMMARY (threshold=0.5)")
    logger.info("=" * 60)
    logger.info(
        f"Recall: {cv_metrics['recall_mean']:.3f} ± {cv_metrics['recall_std']:.3f}"
    )
    logger.info(f"F1: {cv_metrics['f1_mean']:.3f} ± {cv_metrics['f1_std']:.3f}")
    logger.info(
        f"Precision: {cv_metrics['precision_mean']:.3f} ± {cv_metrics['precision_std']:.3f}"
    )

    # Create OOF predictions DataFrame
    oof_df = pd.DataFrame({"y_true": oof_labels, "y_proba": oof_preds})

    return oof_df, cv_metrics


# =============================================================================
# THRESHOLD TUNING
# =============================================================================


def tune_threshold_on_validation(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    target_recall: float = TARGET_RECALL,
    min_threshold: float = 0.30,
    max_threshold: float = 0.70,
    step: float = 0.05,
) -> Tuple[float, Dict]:
    """
    Find optimal threshold by maximizing F1 while maintaining Recall >= target.

    Args:
        y_true: True labels
        y_proba: Predicted probabilities
        target_recall: Minimum required recall
        min_threshold: Minimum threshold to try
        max_threshold: Maximum threshold to try
        step: Step size for threshold search

    Returns:
        Tuple of (optimal_threshold, metrics_at_threshold)
    """
    logger.info("=" * 60)
    logger.info("THRESHOLD TUNING (on validation/OOF predictions)")
    logger.info("=" * 60)

    thresholds = np.arange(min_threshold, max_threshold + step, step)
    best_threshold = 0.5
    best_f1 = 0
    best_metrics = {}

    for threshold in thresholds:
        y_pred = (y_proba >= threshold).astype(int)

        recall = recall_score(y_true, y_pred)
        f1 = f1_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)

        logger.info(
            f"Threshold {threshold:.2f}: Recall={recall:.3f}, F1={f1:.3f}, Precision={precision:.3f}"
        )

        # Select threshold that maximizes F1 while meeting recall constraint
        if recall >= target_recall and f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
            best_metrics = {
                "recall": recall,
                "f1": f1,
                "precision": precision,
            }

    logger.info("\n" + "=" * 60)
    logger.info(f"OPTIMAL THRESHOLD: {best_threshold:.2f}")
    logger.info(
        f"Metrics at optimal: Recall={best_metrics['recall']:.3f}, "
        f"F1={best_metrics['f1']:.3f}, Precision={best_metrics['precision']:.3f}"
    )
    logger.info("=" * 60)

    return best_threshold, best_metrics


# =============================================================================
# BOOTSTRAP CONFIDENCE INTERVALS
# =============================================================================


def bootstrap_ci(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_iterations: int = BOOTSTRAP_ITERATIONS,
    ci_level: float = 0.95,
) -> Dict[str, Tuple[float, float]]:
    """
    Calculate bootstrap confidence intervals for test metrics.

    Args:
        y_true: True labels
        y_pred: Predicted labels
        n_iterations: Number of bootstrap samples
        ci_level: Confidence level (default 95%)

    Returns:
        Dict of {metric_name: (lower_bound, upper_bound)}
    """
    logger.info(f"\nCalculating bootstrap {ci_level:.0%} CI ({n_iterations} iterations)...")

    recalls = []
    f1s = []
    precisions = []

    n_samples = len(y_true)
    alpha = (1 - ci_level) / 2

    for i in range(n_iterations):
        # Resample with replacement
        indices = resample(np.arange(n_samples), replace=True, random_state=i)
        y_true_boot = y_true[indices]
        y_pred_boot = y_pred[indices]

        # Calculate metrics
        recalls.append(recall_score(y_true_boot, y_pred_boot, zero_division=0))
        f1s.append(f1_score(y_true_boot, y_pred_boot, zero_division=0))
        precisions.append(precision_score(y_true_boot, y_pred_boot, zero_division=0))

    # Calculate percentile CI
    ci_dict = {
        "recall": (
            np.percentile(recalls, alpha * 100),
            np.percentile(recalls, (1 - alpha) * 100),
        ),
        "f1": (
            np.percentile(f1s, alpha * 100),
            np.percentile(f1s, (1 - alpha) * 100),
        ),
        "precision": (
            np.percentile(precisions, alpha * 100),
            np.percentile(precisions, (1 - alpha) * 100),
        ),
    }

    for metric, (lower, upper) in ci_dict.items():
        logger.info(f"{metric.capitalize()}: 95% CI = [{lower:.3f}, {upper:.3f}]")

    return ci_dict


# =============================================================================
# MODEL TRAINING
# =============================================================================


def train_final_model(
    X_train: pd.DataFrame, y_train: pd.Series
) -> Tuple[LogisticRegression, DecisionTreeClassifier]:
    """
    Train final models on full training data (train+val).

    Args:
        X_train: Training features
        y_train: Training labels

    Returns:
        Tuple of (logistic_regression_model, explainer_tree_model)
    """
    logger.info("\n" + "=" * 60)
    logger.info("TRAINING FINAL MODEL (on Train+Val)")
    logger.info("=" * 60)

    # Apply SMOTE
    try:
        minority_count = min(Counter(y_train).values())
        if minority_count >= 2:
            k_neighbors = min(5, minority_count - 1)
            smote = SMOTE(random_state=42, k_neighbors=max(1, k_neighbors))
            X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
            logger.info(f"SMOTE applied: {len(y_train)} → {len(y_train_res)}")
        else:
            ros = RandomOverSampler(random_state=42)
            X_train_res, y_train_res = ros.fit_resample(X_train, y_train)
            logger.info(
                f"RandomOverSampler used: {len(y_train)} → {len(y_train_res)}"
            )
    except Exception as e:
        logger.warning(f"Oversampling failed: {e}. Using original data.")
        X_train_res, y_train_res = X_train, y_train

    # Train Logistic Regression
    model = LogisticRegression(
        class_weight="balanced", random_state=42, max_iter=1000, solver="lbfgs"
    )
    model.fit(X_train_res, y_train_res)
    logger.info("Logistic Regression model trained")

    # Train Decision Tree for explainability
    explainer_tree = DecisionTreeClassifier(max_depth=4, random_state=42)
    explainer_tree.fit(X_train_res, y_train_res)
    logger.info("Decision Tree explainer trained")

    return model, explainer_tree


# =============================================================================
# EVALUATION
# =============================================================================


def evaluate_on_test(
    model: LogisticRegression,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    threshold: float,
) -> Dict:
    """
    Evaluate model on isolated test set with frozen threshold.

    Args:
        model: Trained model
        X_test: Test features
        y_test: Test labels
        threshold: Frozen threshold from validation tuning

    Returns:
        Dict of test metrics
    """
    logger.info("\n" + "=" * 60)
    logger.info(f"TEST SET EVALUATION (threshold={threshold:.2f}, FROZEN)")
    logger.info("=" * 60)

    # Predict
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= threshold).astype(int)

    # Calculate metrics
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    
    # Calculate AUC-ROC if we have both classes
    try:
        auc_roc = roc_auc_score(y_test, y_proba)
    except ValueError:
        auc_roc = 0.0
        logger.warning("AUC-ROC not calculable (only one class in test set)")

    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)

    metrics = {
        "recall": recall,
        "f1": f1,
        "precision": precision,
        "auc_roc": auc_roc,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "test_size": len(y_test),
    }

    logger.info(f"Recall: {recall:.3f}")
    logger.info(f"F1: {f1:.3f}")
    logger.info(f"Precision: {precision:.3f}")
    logger.info(f"AUC-ROC: {auc_roc:.3f}")
    logger.info(f"Confusion Matrix: TN={tn}, FP={fp}, FN={fn}, TP={tp}")

    # Bootstrap CI
    ci_dict = bootstrap_ci(y_test.values, y_pred)
    metrics["bootstrap_ci"] = ci_dict

    logger.info("\n" + "=" * 60)
    logger.info("TEST EVALUATION COMPLETE")
    logger.info("=" * 60)

    return metrics


# =============================================================================
# FEATURE IMPORTANCE
# =============================================================================


def log_feature_importance(
    model: LogisticRegression, feature_names: List[str]
) -> Dict[str, float]:
    """
    Log feature importance from Logistic Regression coefficients.

    Args:
        model: Trained Logistic Regression model
        feature_names: List of feature names

    Returns:
        Dict of {feature_name: coefficient}
    """
    logger.info("\n" + "=" * 60)
    logger.info("FEATURE IMPORTANCE (Logistic Regression Coefficients)")
    logger.info("=" * 60)

    coefs = model.coef_[0]
    feature_importance = dict(zip(feature_names, coefs))
    sorted_features = sorted(
        feature_importance.items(), key=lambda x: abs(x[1]), reverse=True
    )

    for feature, coef in sorted_features:
        direction = "↑" if coef > 0 else "↓"
        logger.info(f"  {feature:25s}: {coef:+.4f} {direction}")

    return feature_importance


# =============================================================================
# SAVE/LOAD MODELS
# =============================================================================


def save_model_and_metadata(
    model: LogisticRegression,
    explainer_tree: DecisionTreeClassifier,
    threshold: float,
    test_metrics: Dict,
    cv_metrics: Dict,
    feature_names: List[str],
    feature_importance: Dict[str, float],
    split_method: str = "grouped",
):
    """
    Save trained models and metadata to disk.

    Args:
        model: Trained Logistic Regression model
        explainer_tree: Trained Decision Tree for explainability
        threshold: Optimal threshold
        test_metrics: Test set metrics
        cv_metrics: Cross-validation metrics
        feature_names: List of feature names
        feature_importance: Dict of feature importances
        split_method: 'grouped' or 'temporal'
    """
    logger.info("\n" + "=" * 60)
    logger.info("SAVING MODELS AND METADATA")
    logger.info("=" * 60)

    # Save models
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    logger.info(f"Model saved to {MODEL_PATH}")

    with open(EXPLAINER_MODEL_PATH, "wb") as f:
        pickle.dump(explainer_tree, f)
    logger.info(f"Explainer saved to {EXPLAINER_MODEL_PATH}")

    # Save metadata
    metadata = {
        "model_version": MODEL_VERSION,
        "model_type": "LogisticRegression",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "split_method": split_method,
        "threshold": threshold,
        "threshold_source": "validation_oof",
        "features": feature_names,
        "features_excluded": ["absent_ratio", "absent_count", "late_ratio"],
        "feature_importance": feature_importance,
        "cv_metrics": cv_metrics,
        "test_metrics": test_metrics,
        "validation_config": {
            "train_size": TRAIN_SIZE,
            "val_size": VAL_SIZE,
            "test_size": TEST_SIZE,
            "cv_n_splits": CV_N_SPLITS,
            "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
        },
    }

    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Metadata saved to {METADATA_PATH}")


def load_model() -> Tuple[LogisticRegression, DecisionTreeClassifier, Dict]:
    """
    Load trained models and metadata from disk.

    Returns:
        Tuple of (model, explainer_tree, metadata)
    """
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    with open(EXPLAINER_MODEL_PATH, "rb") as f:
        explainer_tree = pickle.load(f)

    with open(METADATA_PATH, "r") as f:
        metadata = json.load(f)

    return model, explainer_tree, metadata


# =============================================================================
# MAIN TRAINING PIPELINE
# =============================================================================


def train_and_save_models(
    custom_features_df: Optional[pd.DataFrame] = None,
) -> Dict:
    """
    Main training pipeline with proper validation methodology.

    Pipeline:
    1. Load/engineer features
    2. Create labels
    3. Split data (Train/Val/Test 60/20/20) with GroupShuffleSplit
    4. Cross-validate on Train+Val to get OOF predictions
    5. Tune threshold on OOF predictions
    6. Train final model on Train+Val
    7. Evaluate on isolated Test set with frozen threshold
    8. Save models and metadata

    Args:
        custom_features_df: Optional pre-engineered features for testing

    Returns:
        Dict with status and metrics
    """
    logger.info("\n" + "=" * 80)
    logger.info("TRAINING PIPELINE START (v3 - Proper Validation)")
    logger.info("=" * 80)

    try:
        # Step 1: Load features
        if custom_features_df is not None:
            features_df = custom_features_df
            logger.info(f"Using custom features: {len(features_df)} students")
        else:
            features_df = engineer_features()
            logger.info(f"Engineered features from DB: {len(features_df)} students")

        if features_df.empty:
            return {
                "status": "error",
                "message": "No features available. Please ensure attendance data exists.",
            }

        # Step 2: Create labels
        y = create_target_labels(features_df)
        groups = features_df["nis"]

        # Prepare features (drop nis, select only FEATURE_COLUMNS)
        X, selected_features = prepare_features_for_model(features_df)

        logger.info(f"\nDataset: {len(X)} students")
        logger.info(f"Class distribution: {Counter(y)}")
        logger.info(f"Features used: {selected_features}")

        # Check minimum samples
        if len(X) < 10:
            return {
                "status": "error",
                "message": f"Insufficient data: only {len(X)} samples. Need at least 10.",
            }

        # Check class diversity
        class_counts = Counter(y)
        if len(class_counts) < 2:
            return {
                "status": "error",
                "message": "Not enough class diversity. Need both at-risk and normal students.",
            }

        # Step 3: Split data (Train/Val/Test 60/20/20)
        train_idx, val_idx, test_idx = split_data_grouped(X, y, groups)

        # Step 4: Cross-validate on Train+Val
        trainval_idx = np.concatenate([train_idx, val_idx])
        X_trainval = X.iloc[trainval_idx]
        y_trainval = y.iloc[trainval_idx]
        groups_trainval = groups.iloc[trainval_idx]

        oof_df, cv_metrics = cross_validate_groupkfold(
            X_trainval, y_trainval, groups_trainval, n_splits=CV_N_SPLITS
        )

        # Step 5: Tune threshold on OOF predictions
        threshold, threshold_metrics = tune_threshold_on_validation(
            oof_df["y_true"].values, oof_df["y_proba"].values
        )

        # Step 6: Train final model on Train+Val
        model, explainer_tree = train_final_model(X_trainval, y_trainval)

        # Step 7: Evaluate on Test set
        X_test = X.iloc[test_idx]
        y_test = y.iloc[test_idx]
        test_metrics = evaluate_on_test(model, X_test, y_test, threshold)

        # Step 8: Feature importance
        feature_importance = log_feature_importance(model, selected_features)

        # Step 9: Save everything
        save_model_and_metadata(
            model,
            explainer_tree,
            threshold,
            test_metrics,
            cv_metrics,
            selected_features,
            feature_importance,
            split_method="grouped",
        )

        logger.info("\n" + "=" * 80)
        logger.info("TRAINING PIPELINE COMPLETE")
        logger.info("=" * 80)

        return {
            "status": "success",
            "message": "Models trained successfully with proper validation",
            "cv_metrics": cv_metrics,
            "test_metrics": test_metrics,
            "threshold": threshold,
            "model_version": MODEL_VERSION,
        }

    except Exception as e:
        logger.error(f"Training pipeline failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


# =============================================================================
# CONVENIENCE FUNCTIONS (for backward compatibility)
# =============================================================================


def get_model_info() -> Dict:
    """Get information about the currently loaded model."""
    try:
        _, _, metadata = load_model()
        return {
            "status": "available",
            "trained_at": metadata.get("trained_at"),
            "model_type": metadata.get("model_type"),
            "model_version": metadata.get("model_version"),
            "threshold": metadata.get("threshold"),
            "split_method": metadata.get("split_method"),
            "cv_metrics": metadata.get("cv_metrics"),
            "test_metrics": metadata.get("test_metrics"),
        }
    except FileNotFoundError:
        return {"status": "not_trained", "message": "No trained model found"}


def get_feature_importance() -> Dict:
    """Get feature importance from trained model."""
    try:
        _, _, metadata = load_model()
        return metadata.get("feature_importance", {})
    except FileNotFoundError:
        return {}
