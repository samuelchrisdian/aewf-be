from src.ml.training import train_and_save_models
import logging

logger = logging.getLogger(__name__)

class MLService:
    @staticmethod
    def train_models():
        """
        Triggers the training pipeline.
        """
        try:
            train_and_save_models()
            return {"status": "success", "message": "Models trained successfully"}
        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise

    @staticmethod
    def predict_risk(nis):
        """
        Placeholder for prediction logic.
        In a real scenario, this would load the model and predict for the specific student.
        """
        # TODO: Implement actual prediction loading the pickle file
        return {"nis": nis, "risk_score": 0.0, "risk_level": "Low (Not Implemented)"}
