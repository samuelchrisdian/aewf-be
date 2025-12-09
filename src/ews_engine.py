import pickle
import os
import pandas as pd
from src.data_preprocessing import engineer_features
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = "models"
LR_MODEL_PATH = os.path.join(MODEL_DIR, "lr_model.pkl")
DT_MODEL_PATH = os.path.join(MODEL_DIR, "dt_model.pkl")

def load_models():
    lr_model = None
    dt_model = None
    try:
        with open(LR_MODEL_PATH, "rb") as f:
            lr_model = pickle.load(f)
        with open(DT_MODEL_PATH, "rb") as f:
            dt_model = pickle.load(f)
    except FileNotFoundError:
        logger.warning("Models not found. Training might be needed.")
    return lr_model, dt_model

def assess_risk(nis: str):
    """
    Assesses the risk for a specific student using Hybrid EWS (Rule-Based + ML).
    Returns: Dictionary with Risk Level and Rationale.
    """
    try:
        # Get latest features for all students
        # In production this should be optimized to fetch only one, 
        # but engineer_features calculates aggregates.
        df_features = engineer_features()
        
        if df_features.empty:
            return {"risk": "Unknown", "rationale": "No data available"}
            
        student_data = df_features[df_features['nis'] == nis]
        
        if student_data.empty:
            return {"risk": "Unknown", "rationale": "Student not found in attendance records"}
        
        # Prepare features for prediction
        X = student_data.drop(columns=['nis'])
        
        # Rule-Based Assessment (Priority)
        # Example Rule: If absent_ratio > 20% -> High Risk immediately
        absent_ratio = student_data['absent_ratio'].values[0]
        if absent_ratio > 0.20:
            return {
                "risk": "Red",
                "rationale": f"High Absenteeism ({absent_ratio*100:.1f}%) detected by Rule Engine."
            }
            
        # ML-Based Assessment
        lr_model, dt_model = load_models()
        
        if not lr_model or not dt_model:
            # Fallback if models not ready
            if absent_ratio > 0.10:
                 return {"risk": "Yellow", "rationale": "Moderate Absenteeism (Rule Fallback)."}
            return {"risk": "Green", "rationale": "Low Absenteeism (Rule Fallback)."}

        # Align columns with training data (in case new columns appeared)
        # Ideally, feature engineering schema must be consistent.
        # This is a simplified check.
        try:
             lr_pred = lr_model.predict(X)[0]
             dt_pred = dt_model.predict(X)[0]
        except Exception as e:
             logger.error(f"Prediction error: {e}")
             return {"risk": "Error", "rationale": "Model prediction failed."}
             
        # Hybrid Logic Combination
        # If ANY model predicts Risk (1), flag as Yellow/Red
        if lr_pred == 1 or dt_pred == 1:
            return {
                "risk": "Yellow",
                "rationale": "ML Models predict potential risk."
            }
            
        return {
            "risk": "Green",
            "rationale": "Safe. Low absenteeism and negative ML prediction."
        }

    except Exception as e:
        logger.error(f"Error in risk assessment: {e}")
        return {"risk": "Error", "rationale": str(e)}
