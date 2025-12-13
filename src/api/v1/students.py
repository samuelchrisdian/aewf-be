"""
Students API endpoints.
Provides CRUD operations for student management.
"""
from flask import Blueprint, request

from src.app.middleware import token_required
from src.services.student_service import student_service
from src.utils.response_helpers import (
    success_response,
    created_response,
    paginated_response,
    not_found_response,
    validation_error_response
)
from src.utils.pagination import get_pagination_params
from src.utils.validators import validate_boolean_param, validate_sort_params


students_bp = Blueprint('students', __name__, url_prefix='/api/v1/students')


@students_bp.route('', methods=['GET'])
@token_required
def get_students(current_user):
    """
    Get paginated list of students with filtering and sorting.
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - class_id: Filter by class ID
        - is_active: Filter by active status (true/false)
        - search: Search by name or NIS
        - sort_by: Sort field (name, nis, class_id)
        - order: Sort order (asc, desc)
    
    Returns:
        Paginated list of students
    """
    # Get pagination params
    page, per_page = get_pagination_params(request.args)
    
    # Get filter params
    class_id = request.args.get('class_id')
    is_active = validate_boolean_param(request.args.get('is_active'))
    search = request.args.get('search')
    
    # Get sort params
    sort_by = request.args.get('sort_by')
    order = request.args.get('order', 'asc')
    
    # Validate sort params
    sort_by, order = validate_sort_params(
        sort_by, order, ['name', 'nis', 'class_id']
    )
    
    # Get students
    result = student_service.get_students(
        page=page,
        per_page=per_page,
        class_id=class_id,
        is_active=is_active,
        search=search,
        sort_by=sort_by,
        order=order
    )
    
    return paginated_response(
        data=result["data"],
        pagination=result["pagination"],
        message="Students retrieved successfully"
    )


@students_bp.route('/<nis>', methods=['GET'])
@token_required
def get_student(current_user, nis):
    """
    Get a single student by NIS with attendance summary.
    
    Path Parameters:
        - nis: Student NIS (unique identifier)
    
    Returns:
        Student details with attendance summary
    """
    student_data, error = student_service.get_student(nis)
    
    if error:
        return not_found_response("Student")
    
    return success_response(
        data=student_data,
        message="Student retrieved successfully"
    )


@students_bp.route('', methods=['POST'])
@token_required
def create_student(current_user):
    """
    Create a new student.
    
    Request Body:
        - nis: Student NIS (required, unique)
        - name: Student name (required)
        - class_id: Class ID (required, must exist)
        - parent_phone: Parent phone number (optional)
        - is_active: Active status (optional, default: true)
    
    Returns:
        Created student data
    """
    data = request.get_json()
    
    if not data:
        return validation_error_response(
            {"_schema": ["Request body is required"]},
            message="Invalid request"
        )
    
    student_data, errors = student_service.create_student(data)
    
    if errors:
        return validation_error_response(errors)
    
    return created_response(
        data=student_data,
        message="Student created successfully"
    )


@students_bp.route('/<nis>', methods=['PUT'])
@token_required
def update_student(current_user, nis):
    """
    Update an existing student.
    
    Path Parameters:
        - nis: Student NIS
    
    Request Body:
        - name: Student name (optional)
        - class_id: Class ID (optional)
        - parent_phone: Parent phone number (optional)
        - is_active: Active status (optional)
    
    Returns:
        Updated student data
    """
    data = request.get_json()
    
    if not data:
        return validation_error_response(
            {"_schema": ["Request body is required"]},
            message="Invalid request"
        )
    
    student_data, errors = student_service.update_student(nis, data)
    
    if errors:
        # Check if it's a not found error
        if "nis" in errors and "not found" in str(errors["nis"]).lower():
            return not_found_response("Student")
        return validation_error_response(errors)
    
    return success_response(
        data=student_data,
        message="Student updated successfully"
    )


@students_bp.route('/<nis>', methods=['DELETE'])
@token_required
def delete_student(current_user, nis):
    """
    Soft delete a student (set is_active to False).
    
    Path Parameters:
        - nis: Student NIS
    
    Returns:
        Success message
    """
    success, error = student_service.delete_student(nis)
    
    if not success:
        return not_found_response("Student")
    
    return success_response(message="Student deleted successfully")
