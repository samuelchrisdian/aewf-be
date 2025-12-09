from flask import Flask, jsonify, request
from src.db_config import init_db
from src.master_data_service import (
    create_student, 
    get_student, 
    get_students_by_teacher,
    import_master_data
)
from src.data_preprocessing import clean_and_import_attendance
from src.model_training import train_and_save_models
from src.ews_engine import assess_risk
import os

app = Flask(__name__)

# Initialize DB on start
# In production, migration tools like Alembic are preferred.
with app.app_context():
    init_db()

@app.route('/')
def index():
    return jsonify({"message": "AEWF Backend API is running."})

# --- MDM Endpoints ---

@app.route('/api/students', methods=['POST'])
def add_student():
    data = request.json
    try:
        student = create_student(
            nis=data.get('nis'),
            name=data.get('name'),
            class_id=data.get('class_id')
        )
        return jsonify({"message": "Student created", "nis": student.nis}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/students/<nis>', methods=['GET'])
def read_student(nis):
    student = get_student(nis)
    if student:
        return jsonify({
            "nis": student.nis,
            "name": student.name,
            "class_id": student.class_id
        })
    return jsonify({"error": "Student not found"}), 404

@app.route('/api/teachers/<teacher_id>/students', methods=['GET'])
def get_teacher_students(teacher_id):
    students = get_students_by_teacher(teacher_id)
    result = [{
        "nis": s.nis,
        "name": s.name,
        "class_id": s.class_id
    } for s in students]
    return jsonify(result)

# --- Data Pipeline Endpoints ---

@app.route('/api/master/import', methods=['POST'])
def import_master():
    """
    Expects a file upload 'file'.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    # Save temp
    temp_path = os.path.join("data", file.filename)
    file.save(temp_path)
    
    try:
        import_master_data(temp_path)
        return jsonify({"message": "Master data import initiated."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/attendance/import', methods=['POST'])
def import_attendance():
    """
    Trigger preprocessing of raw attendance CSV.
    Expects file upload.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    temp_path = os.path.join("data", file.filename)
    file.save(temp_path)
    
    try:
        count = clean_and_import_attendance(temp_path)
        return jsonify({"message": f"Imported {count} records."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/models/train', methods=['POST'])
def train_models():
    try:
        train_and_save_models()
        return jsonify({"message": "Models trained successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- EWS Endpoints ---

@app.route('/api/risk/<nis>', methods=['GET'])
def get_student_risk(nis):
    result = assess_risk(nis)
    return jsonify({
        "nis": nis,
        "risk_assessment": result
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
