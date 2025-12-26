"""
ML Model Management API endpoints.
Provides operations for ML model information and retraining.
Uses the new EWS model (ews_model.pkl) with Logistic Regression.
"""

from flask import Blueprint
import os
from datetime import datetime

from src.app.middleware import token_required
from src.services.ml_service import MLService
from src.utils.response_helpers import success_response, error_response


models_bp = Blueprint("models", __name__, url_prefix="/api/v1/models")


@models_bp.route("/info", methods=["GET"])
@token_required
def get_models_info(current_user):
    """
    Get information about the trained ML model.

    Returns:
        Model metadata including version, training time, metrics, and type
    """
    model_info = MLService.get_model_info()

    return success_response(
        data={
            "ews_model": model_info,
            "model_type": "Logistic Regression with SMOTE",
            "description": "Hybrid ML + Rule-based Early Warning System",
        },
        message="Model information retrieved successfully",
    )


@models_bp.route("/performance", methods=["GET"])
@token_required
def get_models_performance(current_user):
    """
    Get performance metrics for the trained ML model.

    Returns:
        Model performance metrics (recall, F1, AUC-ROC, threshold)
    """
    model_info = MLService.get_model_info()

    if model_info.get("status") == "no_model":
        return success_response(
            data={
                "status": "not_trained",
                "message": "No trained model found. Please train the model first.",
            },
            message="Model not yet trained",
        )

    metrics = model_info.get("metrics", {})

    performance = {
        "ews_model": {
            "status": model_info.get("status", "unknown"),
            "model_type": model_info.get("model_type", "LogisticRegression"),
            "trained_at": model_info.get("trained_at"),
            "threshold": model_info.get("threshold", 0.5),
            "metrics": {
                "recall": metrics.get("recall", 0),
                "f1_score": metrics.get("f1", 0),
                "auc_roc": metrics.get("auc_roc", 0),
                "precision": metrics.get("precision", 0),
                "accuracy": metrics.get("accuracy", 0),
            },
            "targets": {"recall": "≥ 0.70", "f1_score": "≥ 0.65", "auc_roc": "≥ 0.75"},
            "all_targets_met": all(
                [
                    metrics.get("recall", 0) >= 0.70,
                    metrics.get("f1", 0) >= 0.65,
                    metrics.get("auc_roc", 0) >= 0.75,
                ]
            ),
        },
        "feature_importance": MLService.get_feature_importance(),
        "config": model_info.get("config", {}),
    }

    return success_response(
        data=performance, message="Model performance retrieved successfully"
    )


@models_bp.route("/retrain", methods=["POST"])
@models_bp.route("/train", methods=["POST"])
@token_required
def retrain_models(current_user):
    """
    Trigger model retraining.

    This endpoint starts the ML model training pipeline.
    Uses SMOTE for handling imbalanced data and automatic threshold tuning.

    Returns:
        Training status and results including metrics
    """
    try:
        result = MLService.train_models()

        if result.get("status") == "error":
            return error_response(
                message=result.get("message", "Training failed"),
                code="TRAINING_ERROR",
                status_code=500,
            )

        return success_response(
            data={
                "status": result.get("status", "completed"),
                "message": result.get("message", "Model trained successfully"),
                "metrics": result.get("metrics"),
                "threshold": result.get("threshold"),
                "all_criteria_met": result.get("all_criteria_met", False),
                "model_type": "LogisticRegression",
            },
            message="Model training completed successfully",
        )
    except Exception as e:
        return error_response(
            message=f"Model training failed: {str(e)}",
            code="TRAINING_ERROR",
            status_code=500,
        )


@models_bp.route("/predict/<nis>", methods=["GET"])
@token_required
def predict_student_risk(current_user, nis: str):
    """
    Get ML risk prediction for a specific student.

    Args:
        nis: Student NIS identifier

    Returns:
        Risk prediction with tier, probability, and factors
    """
    try:
        result = MLService.predict_risk(nis)

        return success_response(data=result, message="Risk prediction completed")
    except Exception as e:
        return error_response(
            message=f"Prediction failed: {str(e)}",
            code="PREDICTION_ERROR",
            status_code=500,
        )


@models_bp.route("/features", methods=["GET"])
@token_required
def get_feature_importance(current_user):
    """
    Get feature importance from the trained model.

    Returns:
        List of features with their importance scores (coefficients)
    """
    importance = MLService.get_feature_importance()

    return success_response(
        data={
            "features": importance,
            "description": "Higher positive values increase risk, negative values decrease risk",
        },
        message="Feature importance retrieved successfully",
    )
