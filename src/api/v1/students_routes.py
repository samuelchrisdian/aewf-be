from flask import jsonify, request
from . import v1_bp
from src.services.student_service import student_service

@v1_bp.route('/students', methods=['POST'])
def add_student():
    data = request.json
    try:
        student = student_service.create_student(
            nis=data.get('nis'),
            name=data.get('name'),
            class_id=data.get('class_id')
        )
        return jsonify({"success": True, "data": {"nis": student.nis}, "message": "Student created"}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@v1_bp.route('/students/<nis>', methods=['GET'])
def read_student(nis):
    student = student_service.get_student(nis)
    if student:
        return jsonify({
            "success": True,
            "data": {
                "nis": student.nis,
                "name": student.name,
                "class_id": student.class_id
            }
        })
    return jsonify({"success": False, "error": "Student not found"}), 404
