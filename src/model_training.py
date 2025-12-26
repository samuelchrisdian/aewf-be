"""
Model Training Module (Legacy Wrapper)

This module wraps the new ML training module for backward compatibility.
All actual training logic is now in src/ml/training.py

@deprecated Use src.ml.training instead
"""

# Re-export from the new module for backward compatibility
from src.ml.training import (
    train_and_save_models,
    create_target_labels,
    load_model,
    TARGET_RECALL,
    TARGET_F1,
    TARGET_AUC_ROC,
    MODEL_PATH,
    METADATA_PATH,
)

if __name__ == "__main__":
    import json

    result = train_and_save_models()
    print(json.dumps(result, indent=2, default=str))
