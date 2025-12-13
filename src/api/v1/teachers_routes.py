from flask import jsonify
from . import v1_bp
from src.services.teacher_service import teacher_service
from src.services.student_service import student_service

@v1_bp.route('/teachers/<teacher_id>/students', methods=['GET'])
def get_teacher_students(teacher_id):
    students = student_service.get_students_by_teacher(teacher_id)
    result = [{
        "nis": s.nis,
        "name": s.name,
        "class_id": s.class_id
    } for s in students]
    return jsonify({"success": True, "data": result})
