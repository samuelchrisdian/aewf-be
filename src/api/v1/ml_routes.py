from flask import jsonify
from . import v1_bp
from src.ml.training import train_and_save_models

@v1_bp.route('/models/train', methods=['POST'])
def train_models():
    try:
        train_and_save_models()
        return jsonify({"success": True, "message": "Models trained successfully."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
