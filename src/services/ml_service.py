"""
ML Service for Early Warning System (EWS)

This service provides the hybrid prediction engine that combines:
1. Rule-Based Triggers (for edge cases)
2. ML Probability-Based Classification

Risk Tiers:
- RED (High Risk): Rule triggered OR Probability > 0.70
- YELLOW (Warning): Probability > 0.40
- GREEN (Normal): Default

Technical Requirements:
- API Response time < 3 seconds
- Interpretable output with factors
- Hybrid: ML + Rules
"""

import os
import pickle
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime

import numpy as np
import pandas as pd

from src.ml.training import (
    train_and_save_models as train_models,
    load_model,
    MODEL_PATH,
    METADATA_PATH,
)
from src.ml.preprocessing import (
    engineer_features_for_student,
    get_feature_columns,
    FEATURE_COLUMNS,
    ABSENT_RATIO_THRESHOLD,
    ABSENT_COUNT_THRESHOLD,
)

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Risk tier thresholds (for ML-based classification)
TIER_RED_THRESHOLD = 0.70  # Probability > 70% → RED
TIER_YELLOW_THRESHOLD = 0.40  # Probability > 40% → YELLOW
# Below 40% → GREEN

# Risk tier definitions
TIER_RED = "RED"
TIER_YELLOW = "YELLOW"
TIER_GREEN = "GREEN"


# =============================================================================
# ML SERVICE CLASS
# =============================================================================


class MLService:
    """
    Machine Learning Service for Student Risk Prediction.

    Provides:
    - Model training
    - Hybrid risk prediction (ML + Rules)
    - Batch predictions
    """

    _model = None
    _metadata = None
    _threshold = None

    @classmethod
    def _ensure_model_loaded(cls) -> bool:
        """
        Ensure model is loaded into memory for predictions.

        Returns:
            True if model is loaded, False otherwise
        """
        if cls._model is not None:
            return True

        model, metadata = load_model()
        if model is None:
            logger.warning("Model not loaded. Train the model first.")
            return False

        cls._model = model
        cls._metadata = metadata
        cls._threshold = metadata.get("threshold", 0.5)

        logger.info(f"Model loaded with threshold: {cls._threshold}")
        return True

    @classmethod
    def _unload_model(cls):
        """Unload model from memory (for retraining)."""
        cls._model = None
        cls._metadata = None
        cls._threshold = None

    @staticmethod
    def train_models() -> Dict:
        """
        Triggers the training pipeline.

        Returns:
            Dictionary with training results
        """
        try:
            # Unload existing model so we reload the new one
            MLService._unload_model()

            result = train_models()

            return {
                "status": result.get("status", "error"),
                "message": result.get("message", "Unknown"),
                "metrics": result.get("metrics"),
                "threshold": result.get("threshold"),
                "all_criteria_met": result.get("all_criteria_met", False),
            }
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def predict_risk(nis: str) -> Dict:
        """
        Predict risk tier for a single student using hybrid logic.

        Hybrid Logic:
        1. Rule Check: If absent_ratio > 0.15 OR total_absent > 5 → RED
        2. ML Check: Use model probability for classification

        Args:
            nis: Student NIS identifier

        Returns:
            Dictionary with:
            - nis: Student identifier
            - risk_tier: RED, YELLOW, or GREEN
            - risk_probability: ML probability (0.0-1.0)
            - is_rule_overridden: True if rule forced the tier
            - factors: Contributing factors
            - prediction_method: 'rule' or 'ml'
        """
        start_time = datetime.now()

        try:
            # Engineer features for this student
            features = engineer_features_for_student(nis)

            # Extract key factors for reporting
            absent_ratio = features.get("absent_ratio", 0)
            absent_count = features.get("absent_count", 0)
            late_ratio = features.get("late_ratio", 0)
            late_count = features.get("late_count", 0)
            trend_score = features.get("trend_score", 0)
            is_rule_triggered = features.get("is_rule_triggered", 0)

            factors = {
                "absent_ratio": round(absent_ratio, 3),
                "absent_count": int(absent_count),
                "late_ratio": round(late_ratio, 3),
                "late_count": int(late_count),
                "trend_score": round(trend_score, 3),
                "total_days": int(features.get("total_days", 0)),
                "attendance_ratio": round(features.get("attendance_ratio", 0), 3),
            }

            # =================================================================
            # STEP 1: RULE-BASED OVERRIDE CHECK
            # =================================================================
            if (
                is_rule_triggered
                or absent_ratio > ABSENT_RATIO_THRESHOLD
                or absent_count > ABSENT_COUNT_THRESHOLD
            ):
                elapsed = (datetime.now() - start_time).total_seconds()

                rule_reason = []
                if absent_ratio > ABSENT_RATIO_THRESHOLD:
                    rule_reason.append(
                        f"absent_ratio ({absent_ratio:.1%}) > {ABSENT_RATIO_THRESHOLD:.0%}"
                    )
                if absent_count > ABSENT_COUNT_THRESHOLD:
                    rule_reason.append(
                        f"absent_count ({absent_count}) > {ABSENT_COUNT_THRESHOLD}"
                    )

                return {
                    "nis": nis,
                    "risk_tier": TIER_RED,
                    "risk_probability": 1.0,
                    "is_rule_overridden": True,
                    "prediction_method": "rule",
                    "rule_reason": "; ".join(rule_reason),
                    "factors": factors,
                    "response_time_ms": round(elapsed * 1000, 2),
                }

            # =================================================================
            # STEP 2: ML-BASED PREDICTION
            # =================================================================
            if not MLService._ensure_model_loaded():
                # Model not available, use simple heuristic
                elapsed = (datetime.now() - start_time).total_seconds()

                # Fallback: Simple heuristic based on absent_ratio
                if absent_ratio > 0.10:
                    tier = TIER_YELLOW
                    prob = 0.5
                else:
                    tier = TIER_GREEN
                    prob = 0.2

                return {
                    "nis": nis,
                    "risk_tier": tier,
                    "risk_probability": prob,
                    "is_rule_overridden": False,
                    "prediction_method": "heuristic",
                    "warning": "Model not loaded, using heuristic fallback",
                    "factors": factors,
                    "response_time_ms": round(elapsed * 1000, 2),
                }

            # Prepare features for model
            feature_values = [features.get(col, 0) for col in FEATURE_COLUMNS]
            X = pd.DataFrame([feature_values], columns=FEATURE_COLUMNS)

            # Get probability
            probability = MLService._model.predict_proba(X)[0][1]

            # Determine tier based on probability and threshold
            threshold = MLService._threshold

            if probability >= TIER_RED_THRESHOLD:
                tier = TIER_RED
            elif probability >= TIER_YELLOW_THRESHOLD:
                tier = TIER_YELLOW
            else:
                tier = TIER_GREEN

            elapsed = (datetime.now() - start_time).total_seconds()

            return {
                "nis": nis,
                "risk_tier": tier,
                "risk_probability": round(float(probability), 4),
                "is_rule_overridden": False,
                "prediction_method": "ml",
                "model_threshold": threshold,
                "factors": factors,
                "response_time_ms": round(elapsed * 1000, 2),
            }

        except Exception as e:
            logger.error(f"Prediction error for student {nis}: {e}")
            import traceback

            traceback.print_exc()

            return {
                "nis": nis,
                "risk_tier": TIER_GREEN,
                "risk_probability": 0.0,
                "is_rule_overridden": False,
                "prediction_method": "error",
                "error": str(e),
                "factors": {},
                "response_time_ms": 0,
            }

    @staticmethod
    def predict_risk_batch(nis_list: List[str]) -> List[Dict]:
        """
        Predict risk for multiple students.

        Args:
            nis_list: List of student NIS identifiers

        Returns:
            List of prediction dictionaries
        """
        results = []
        for nis in nis_list:
            result = MLService.predict_risk(nis)
            results.append(result)
        return results

    @staticmethod
    def get_model_info() -> Dict:
        """
        Get information about the current model.

        Returns:
            Dictionary with model metadata
        """
        if not os.path.exists(METADATA_PATH):
            return {"status": "no_model", "message": "No trained model found"}

        try:
            with open(METADATA_PATH, "r") as f:
                metadata = json.load(f)

            return {
                "status": "available",
                "trained_at": metadata.get("trained_at"),
                "model_type": metadata.get("model_type"),
                "threshold": metadata.get("threshold"),
                "metrics": metadata.get("metrics"),
                "feature_columns": metadata.get("feature_columns"),
                "config": metadata.get("config"),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_feature_importance() -> List[Dict]:
        """
        Get feature importance from the trained model.

        Returns:
            List of features with their importance scores
        """
        if not os.path.exists(METADATA_PATH):
            return []

        try:
            with open(METADATA_PATH, "r") as f:
                metadata = json.load(f)

            return metadata.get("feature_importance", [])
        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
            return []


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def get_tier_description(tier: str) -> str:
    """Get human-readable description of risk tier."""
    descriptions = {
        TIER_RED: "High Risk - Immediate attention required",
        TIER_YELLOW: "Warning - Monitor closely",
        TIER_GREEN: "Normal - No immediate concerns",
    }
    return descriptions.get(tier, "Unknown")


def get_tier_recommendations(tier: str) -> List[str]:
    """Get action recommendations for each tier."""
    recommendations = {
        TIER_RED: [
            "Contact parent/guardian immediately",
            "Schedule meeting with homeroom teacher",
            "Review attendance pattern with BK counselor",
            "Create intervention plan",
        ],
        TIER_YELLOW: [
            "Monitor attendance closely for next 2 weeks",
            "Send attendance reminder to parent",
            "Check for underlying issues (health, family, etc.)",
        ],
        TIER_GREEN: [
            "Continue regular monitoring",
            "Acknowledge good attendance if applicable",
        ],
    }
    return recommendations.get(tier, [])
