"""
Teachers API endpoints.
Provides CRUD operations for teacher management.
"""
from flask import Blueprint, request

from src.app.middleware import token_required
from src.services.teacher_service import teacher_service
from src.utils.response_helpers import (
    success_response,
    created_response,
    not_found_response,
    validation_error_response,
    conflict_response
)


teachers_bp = Blueprint('teachers', __name__, url_prefix='/api/v1/teachers')


@teachers_bp.route('', methods=['GET'])
@token_required
def get_teachers(current_user):
    """
    Get list of all teachers with optional role filter.
    
    Query Parameters:
        - role: Filter by role (e.g., "Wali Kelas")
    
    Returns:
        List of teachers
    """
    role_filter = request.args.get('role')
    
    teachers_data = teacher_service.get_teachers(role_filter=role_filter)
    
    return success_response(
        data=teachers_data,
        message="Teachers retrieved successfully"
    )


@teachers_bp.route('/<teacher_id>', methods=['GET'])
@token_required
def get_teacher(current_user, teacher_id):
    """
    Get a single teacher by ID with classes they manage.
    
    Path Parameters:
        - teacher_id: Teacher ID (unique identifier)
    
    Returns:
        Teacher details with classes list
    """
    teacher_data, error = teacher_service.get_teacher(teacher_id)
    
    if error:
        return not_found_response("Teacher")
    
    return success_response(
        data=teacher_data,
        message="Teacher retrieved successfully"
    )


@teachers_bp.route('', methods=['POST'])
@token_required
def create_teacher(current_user):
    """
    Create a new teacher.
    
    Request Body:
        - teacher_id: Teacher ID (required, unique)
        - name: Teacher name (required)
        - role: Teacher role (optional, default: "Teacher")
        - phone: Phone number (optional)
    
    Returns:
        Created teacher data
    """
    data = request.get_json()
    
    if not data:
        return validation_error_response(
            {"_schema": ["Request body is required"]},
            message="Invalid request"
        )
    
    teacher_data, errors = teacher_service.create_teacher(data)
    
    if errors:
        return validation_error_response(errors)
    
    return created_response(
        data=teacher_data,
        message="Teacher created successfully"
    )


@teachers_bp.route('/<teacher_id>', methods=['PUT'])
@token_required
def update_teacher(current_user, teacher_id):
    """
    Update an existing teacher.
    
    Path Parameters:
        - teacher_id: Teacher ID
    
    Request Body:
        - name: Teacher name (optional)
        - role: Teacher role (optional)
        - phone: Phone number (optional)
    
    Returns:
        Updated teacher data
    """
    data = request.get_json()
    
    if not data:
        return validation_error_response(
            {"_schema": ["Request body is required"]},
            message="Invalid request"
        )
    
    teacher_data, errors = teacher_service.update_teacher(teacher_id, data)
    
    if errors:
        # Check if it's a not found error
        if "teacher_id" in errors and "not found" in str(errors["teacher_id"]).lower():
            return not_found_response("Teacher")
        return validation_error_response(errors)
    
    return success_response(
        data=teacher_data,
        message="Teacher updated successfully"
    )


@teachers_bp.route('/<teacher_id>', methods=['DELETE'])
@token_required
def delete_teacher(current_user, teacher_id):
    """
    Delete a teacher.
    Cannot delete if assigned as wali kelas for any class.
    
    Path Parameters:
        - teacher_id: Teacher ID
    
    Returns:
        Success message
    """
    success, error = teacher_service.delete_teacher(teacher_id)
    
    if not success:
        if "not found" in error.lower():
            return not_found_response("Teacher")
        # Conflict error (is wali kelas)
        return conflict_response(error)
    
    return success_response(message="Teacher deleted successfully")
