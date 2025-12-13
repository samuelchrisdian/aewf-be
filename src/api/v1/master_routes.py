from flask import jsonify, request
from . import v1_bp
from src.services.master_import_service import master_import_service
import os

@v1_bp.route('/master/import', methods=['POST'])
def import_master():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"}), 400
    
    # Save temp
    temp_path = os.path.join("data", file.filename)
    # Ensure data dir exists
    if not os.path.exists("data"):
        os.makedirs("data")
        
    file.save(temp_path)
    
    try:
        master_import_service.import_master_data(temp_path)
        return jsonify({"success": True, "message": "Master data import initiated."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
