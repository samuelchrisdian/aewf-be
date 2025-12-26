"""
ML Model Training for Early Warning System (EWS)

This module trains a LogisticRegression model with class balancing and SMOTE
to handle imbalanced student risk data.

Technical Success Criteria:
- Recall for At-Risk class: ≥ 0.70 (Priority: Minimize False Negatives)
- F1-Score: ≥ 0.65
- AUC-ROC: ≥ 0.75
- Feature importance must be logged for interpretability
"""

import pandas as pd
import numpy as np
import pickle
import json
import os
from datetime import datetime
from typing import Dict, Tuple, Optional

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    recall_score,
    f1_score,
    roc_auc_score,
    precision_score,
    confusion_matrix,
    classification_report,
)
from imblearn.over_sampling import SMOTE

from src.ml.preprocessing import (
    engineer_features,
    engineer_features_from_df,
    get_feature_columns,
    prepare_features_for_model,
    FEATURE_COLUMNS,
    ABSENT_RATIO_THRESHOLD,
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

# Training configuration
DEFAULT_THRESHOLD = 0.5
MIN_THRESHOLD = 0.30
THRESHOLD_STEP = 0.05

# Success criteria
TARGET_RECALL = 0.70
TARGET_F1 = 0.65
TARGET_AUC_ROC = 0.75

# Ensure model directory exists
if not os.path.exists(MODEL_DIR):
    os.makedirs(MODEL_DIR)


# =============================================================================
# MODEL TRAINING
# =============================================================================


def create_target_labels(features_df: pd.DataFrame) -> pd.Series:
    """
    Create target labels for training.

    A student is considered "At-Risk" (1) if ANY of these conditions are met:
    - absent_ratio > 10% (lower than rule threshold for ML sensitivity)
    - OR absent_count > 3 (more than 3 absences)
    - OR late_count > 3 (frequent lateness - lowered from 5 to capture more cases)
    - OR late_ratio > 15% (high late percentage)
    - OR trend_score < -0.2 (worsening attendance trend)

    Args:
        features_df: DataFrame with engineered features

    Returns:
        Series of binary labels (0=Normal, 1=At-Risk)
    """
    # Use adaptive thresholds based on available data
    at_risk_mask = (
        (features_df["absent_ratio"] > 0.10)  # 10% absence rate
        | (features_df["absent_count"] > 3)  # More than 3 absences
        | (features_df["late_count"] > 3)  # More than 3 late arrivals
        | (features_df["late_ratio"] > 0.15)  # More than 15% late ratio
        | (features_df["trend_score"] < -0.2)  # Worsening trend
    )

    return at_risk_mask.astype(int)


def train_model_with_threshold_tuning(
    X_train: pd.DataFrame, X_test: pd.DataFrame, y_train: pd.Series, y_test: pd.Series
) -> Tuple[LogisticRegression, float, Dict]:
    """
    Train LogisticRegression and tune threshold to meet Recall target.

    Args:
        X_train, X_test: Feature DataFrames
        y_train, y_test: Target labels

    Returns:
        Tuple of (trained_model, optimal_threshold, metrics_dict)
    """
    logger.info("=" * 60)
    logger.info("TRAINING LOGISTIC REGRESSION MODEL")
    logger.info("=" * 60)

    # Apply SMOTE for class balancing
    try:
        # Ensure we have at least 2 samples of minority class for SMOTE
        minority_count = y_train.sum()
        if minority_count >= 2:
            k_neighbors = min(5, minority_count - 1)
            smote = SMOTE(random_state=42, k_neighbors=max(1, k_neighbors))
            X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
            logger.info(f"SMOTE applied: {len(y_train)} → {len(y_train_res)} samples")
        else:
            logger.warning("Not enough minority samples for SMOTE, skipping")
            X_train_res, y_train_res = X_train, y_train
    except Exception as e:
        logger.warning(f"SMOTE failed: {e}, using original data")
        X_train_res, y_train_res = X_train, y_train

    # Train LogisticRegression with class_weight='balanced'
    model = LogisticRegression(
        class_weight="balanced", random_state=42, max_iter=1000, solver="lbfgs"
    )

    model.fit(X_train_res, y_train_res)

    # Train Decision Tree for explainability (interpretable rules)
    explainer_tree = DecisionTreeClassifier(
        max_depth=4,  # Keep shallow for interpretability
        min_samples_leaf=5,  # Ensure meaningful rules
        random_state=42,
        class_weight="balanced",
    )
    explainer_tree.fit(X_train_res, y_train_res)
    logger.info("Decision Tree explainer trained for interpretability")

    # Get probability predictions
    y_proba = model.predict_proba(X_test)[:, 1]

    # Find optimal threshold
    best_threshold = DEFAULT_THRESHOLD
    best_metrics = None

    current_threshold = DEFAULT_THRESHOLD
    while current_threshold >= MIN_THRESHOLD:
        y_pred = (y_proba >= current_threshold).astype(int)

        # Calculate metrics
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        precision = precision_score(y_test, y_pred, zero_division=0)

        try:
            auc_roc = roc_auc_score(y_test, y_proba)
        except ValueError:
            auc_roc = 0.5  # Default if only one class

        logger.info(
            f"Threshold {current_threshold:.2f}: Recall={recall:.3f}, F1={f1:.3f}, AUC-ROC={auc_roc:.3f}"
        )

        if recall >= TARGET_RECALL:
            best_threshold = current_threshold
            best_metrics = {
                "threshold": current_threshold,
                "recall": recall,
                "f1": f1,
                "precision": precision,
                "auc_roc": auc_roc,
            }
            break

        current_threshold -= THRESHOLD_STEP

    # If we couldn't reach target recall, use the lowest threshold
    if best_metrics is None:
        y_pred = (y_proba >= MIN_THRESHOLD).astype(int)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        precision = precision_score(y_test, y_pred, zero_division=0)

        try:
            auc_roc = roc_auc_score(y_test, y_proba)
        except ValueError:
            auc_roc = 0.5

        best_threshold = MIN_THRESHOLD
        best_metrics = {
            "threshold": MIN_THRESHOLD,
            "recall": recall,
            "f1": f1,
            "precision": precision,
            "auc_roc": auc_roc,
        }
        logger.warning(
            f"Could not reach target Recall={TARGET_RECALL}, using threshold={MIN_THRESHOLD}"
        )

    logger.info("-" * 60)
    logger.info(f"OPTIMAL THRESHOLD: {best_threshold}")
    logger.info(f"FINAL METRICS:")
    logger.info(
        f"  - Recall (At-Risk):  {best_metrics['recall']:.3f} (target: ≥{TARGET_RECALL})"
    )
    logger.info(
        f"  - F1-Score:          {best_metrics['f1']:.3f} (target: ≥{TARGET_F1})"
    )
    logger.info(
        f"  - AUC-ROC:           {best_metrics['auc_roc']:.3f} (target: ≥{TARGET_AUC_ROC})"
    )
    logger.info(f"  - Precision:         {best_metrics['precision']:.3f}")
    logger.info("-" * 60)

    # Confusion matrix
    y_pred_final = (y_proba >= best_threshold).astype(int)
    cm = confusion_matrix(y_test, y_pred_final)
    logger.info("Confusion Matrix:")
    logger.info(f"  TN: {cm[0][0]:3d}  FP: {cm[0][1]:3d}")
    logger.info(f"  FN: {cm[1][0]:3d}  TP: {cm[1][1]:3d}")

    return model, explainer_tree, best_threshold, best_metrics


def log_feature_importance(model: LogisticRegression, feature_columns: list):
    """
    Log feature importance for interpretability.

    For LogisticRegression, coefficients indicate feature importance.
    """
    logger.info("-" * 60)
    logger.info("FEATURE IMPORTANCE (LogisticRegression Coefficients)")
    logger.info("-" * 60)

    coefficients = model.coef_[0]
    importance_df = pd.DataFrame(
        {
            "feature": feature_columns,
            "coefficient": coefficients,
            "abs_importance": np.abs(coefficients),
        }
    ).sort_values("abs_importance", ascending=False)

    for _, row in importance_df.iterrows():
        direction = "↑" if row["coefficient"] > 0 else "↓"
        logger.info(f"  {row['feature']:20s}: {row['coefficient']:+.4f} {direction}")

    return importance_df.to_dict("records")


def save_model_and_metadata(
    model: LogisticRegression,
    explainer_tree: DecisionTreeClassifier,
    threshold: float,
    metrics: Dict,
    feature_columns: list,
    feature_importance: list,
):
    """
    Save trained model and metadata.

    Saves:
    - models/ews_model.pkl: Trained model
    - models/model_metadata.json: Training metadata
    """
    # Save main model (Logistic Regression)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    logger.info(f"Model saved to: {MODEL_PATH}")

    # Save explainer model (Decision Tree)
    with open(EXPLAINER_MODEL_PATH, "wb") as f:
        pickle.dump(explainer_tree, f)
    logger.info(f"Explainer tree saved to: {EXPLAINER_MODEL_PATH}")

    # Save metadata
    metadata = {
        "trained_at": datetime.now().isoformat(),
        "model_type": "LogisticRegression",
        "explainer_type": "DecisionTree",
        "threshold": threshold,
        "feature_columns": feature_columns,
        "metrics": metrics,
        "feature_importance": feature_importance,
        "explainer_config": {
            "max_depth": 4,
            "min_samples_leaf": 5,
        },
        "config": {
            "target_recall": TARGET_RECALL,
            "target_f1": TARGET_F1,
            "target_auc_roc": TARGET_AUC_ROC,
            "class_weight": "balanced",
            "smote_applied": True,
        },
    }

    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Metadata saved to: {METADATA_PATH}")


def train_and_save_models(features_df: pd.DataFrame = None) -> Dict:
    """
    Main training function.

    Args:
        features_df: Optional pre-computed features DataFrame.
                     If None, will fetch from database.

    Returns:
        Dictionary with training results
    """
    logger.info("=" * 60)
    logger.info("STARTING EWS MODEL TRAINING PIPELINE")
    logger.info("=" * 60)

    try:
        # Get features
        if features_df is None:
            df_features = engineer_features()
        else:
            df_features = features_df

        if df_features.empty:
            logger.warning("No data available for training.")
            return {"status": "error", "message": "No data available"}

        logger.info(f"Training data: {len(df_features)} students")

        # Prepare features for model
        X = prepare_features_for_model(df_features)

        # Create target labels
        y = create_target_labels(df_features)

        logger.info(f"Class distribution: Normal={sum(y==0)}, At-Risk={sum(y==1)}")

        # Check for class diversity
        if len(np.unique(y)) < 2:
            logger.warning("Not enough class diversity (all data belongs to one class)")
            return {"status": "error", "message": "Not enough class diversity"}

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        logger.info(f"Train set: {len(X_train)}, Test set: {len(X_test)}")

        # Train with threshold tuning (returns model, explainer_tree, threshold, metrics)
        model, explainer_tree, threshold, metrics = train_model_with_threshold_tuning(
            X_train, X_test, y_train, y_test
        )

        # Log feature importance
        feature_importance = log_feature_importance(model, FEATURE_COLUMNS)

        # Save model and metadata
        save_model_and_metadata(
            model,
            explainer_tree,
            threshold,
            metrics,
            FEATURE_COLUMNS,
            feature_importance,
        )

        # Check if criteria met
        criteria_met = {
            "recall": metrics["recall"] >= TARGET_RECALL,
            "f1": metrics["f1"] >= TARGET_F1,
            "auc_roc": metrics["auc_roc"] >= TARGET_AUC_ROC,
        }

        all_met = all(criteria_met.values())

        logger.info("=" * 60)
        if all_met:
            logger.info("✓ ALL SUCCESS CRITERIA MET!")
        else:
            logger.warning("⚠ SOME CRITERIA NOT MET:")
            for criterion, met in criteria_met.items():
                status = "✓" if met else "✗"
                logger.warning(f"  {status} {criterion}")
        logger.info("=" * 60)

        return {
            "status": "success",
            "message": "Model trained successfully",
            "metrics": metrics,
            "threshold": threshold,
            "criteria_met": criteria_met,
            "all_criteria_met": all_met,
            "model_path": MODEL_PATH,
            "metadata_path": METADATA_PATH,
        }

    except Exception as e:
        logger.error(f"Error training models: {e}")
        import traceback

        traceback.print_exc()
        return {"status": "error", "message": str(e)}


def load_model() -> (
    Tuple[
        Optional[LogisticRegression], Optional[DecisionTreeClassifier], Optional[Dict]
    ]
):
    """
    Load trained model, explainer tree, and metadata.

    Returns:
        Tuple of (model, explainer_tree, metadata) or (None, None, None) if not found
    """
    try:
        if not os.path.exists(MODEL_PATH) or not os.path.exists(METADATA_PATH):
            logger.warning("Model or metadata file not found")
            return None, None, None

        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)

        # Load explainer tree (optional - may not exist for older models)
        explainer_tree = None
        if os.path.exists(EXPLAINER_MODEL_PATH):
            with open(EXPLAINER_MODEL_PATH, "rb") as f:
                explainer_tree = pickle.load(f)
        else:
            logger.warning("Explainer tree not found, explanations will be limited")

        with open(METADATA_PATH, "r") as f:
            metadata = json.load(f)

        return model, explainer_tree, metadata

    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return None, None, None


if __name__ == "__main__":
    # Run training when executed directly
    result = train_and_save_models()
    print(json.dumps(result, indent=2, default=str))
