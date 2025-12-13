from flask import jsonify, request
from . import v1_bp
from src.ml.preprocessing import clean_and_import_attendance
import os

@v1_bp.route('/attendance/import', methods=['POST'])
def import_attendance():
    """
    Trigger preprocessing of raw attendance CSV.
    Expects file upload.
    """
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"}), 400
    
    # Save temp
    temp_path = os.path.join("data", file.filename)
    if not os.path.exists("data"):
        os.makedirs("data")

    file.save(temp_path)
    
    try:
        count = clean_and_import_attendance(temp_path)
        return jsonify({"success": True, "message": f"Imported {count} records."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
