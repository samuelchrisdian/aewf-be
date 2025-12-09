import pandas as pd
import numpy as np
import pickle
import os
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTE
from src.data_preprocessing import engineer_features
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = "models"
if not os.path.exists(MODEL_DIR):
    os.makedirs(MODEL_DIR)

def train_and_save_models():
    """
    Trains Logistic Regression and Decision Tree models and saves them.
    Currently, this generates dummy labels for demonstration if no labels exist.
    In a real scenario, labels (At-Risk vs Not-At-Risk) should be part of the dataset.
    """
    try:
        df_features = engineer_features()
        if df_features.empty:
            logger.warning("No data available for training.")
            return

        # Prepare X (Features). Dropping 'nis' as it's an ID.
        X = df_features.drop(columns=['nis'])
        
        # MOCK TARGET GENERATION for demonstration purposes
        # In reality, you'd have historical 'At-Risk' labels.
        # Here we assume > 10% absence is 'At-Risk' (1), else Normal (0)
        y = (X.get('absent_ratio', 0) > 0.1).astype(int)
        
        # Check if we have enough classes
        if len(np.unique(y)) < 2:
            logger.warning("Not enough class diversity to train models (all data belongs to one class).")
            # Force at least one sample distinction for code to run or return
            return

        # Split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Handle Imbalance
        smote = SMOTE(random_state=42, k_neighbors=min(1, len(X_train)-1) if len(X_train) > 1 else 1)
        # Check if we can apply SMOTE (needs > 1 sample per class)
        try:
             X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
        except ValueError:
             # Fallback if too few samples
             X_train_res, y_train_res = X_train, y_train

        # Train LR
        lr_model = LogisticRegression(random_state=42)
        lr_model.fit(X_train_res, y_train_res)
        
        # Train DT
        dt_model = DecisionTreeClassifier(random_state=42)
        dt_model.fit(X_train_res, y_train_res)

        # Save Models
        with open(os.path.join(MODEL_DIR, "lr_model.pkl"), "wb") as f:
            pickle.dump(lr_model, f)
        
        with open(os.path.join(MODEL_DIR, "dt_model.pkl"), "wb") as f:
            pickle.dump(dt_model, f)
            
        logger.info("Models trained and saved successfully.")

    except Exception as e:
        logger.error(f"Error training models: {e}")
        raise

if __name__ == "__main__":
    train_and_save_models()
