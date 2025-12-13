"""
Classes API endpoints.
Provides CRUD operations for class management.
"""
from flask import Blueprint, request

from src.app.middleware import token_required
from src.services.class_service import class_service
from src.utils.response_helpers import (
    success_response,
    created_response,
    not_found_response,
    validation_error_response,
    conflict_response
)


classes_bp = Blueprint('classes', __name__, url_prefix='/api/v1/classes')


@classes_bp.route('', methods=['GET'])
@token_required
def get_classes(current_user):
    """
    Get list of all classes with student count.
    
    Returns:
        List of classes with wali kelas info and student count
    """
    classes_data = class_service.get_classes()
    
    return success_response(
        data=classes_data,
        message="Classes retrieved successfully"
    )


@classes_bp.route('/<class_id>', methods=['GET'])
@token_required
def get_class(current_user, class_id):
    """
    Get a single class by ID with full details.
    
    Path Parameters:
        - class_id: Class ID (unique identifier)
    
    Returns:
        Class details with wali kelas, student count, and attendance stats
    """
    class_data, error = class_service.get_class(class_id)
    
    if error:
        return not_found_response("Class")
    
    return success_response(
        data=class_data,
        message="Class retrieved successfully"
    )


@classes_bp.route('', methods=['POST'])
@token_required
def create_class(current_user):
    """
    Create a new class.
    
    Request Body:
        - class_id: Class ID (required, unique)
        - class_name: Class name (required)
        - wali_kelas_id: Homeroom teacher ID (optional, must exist if provided)
    
    Returns:
        Created class data
    """
    data = request.get_json()
    
    if not data:
        return validation_error_response(
            {"_schema": ["Request body is required"]},
            message="Invalid request"
        )
    
    class_data, errors = class_service.create_class(data)
    
    if errors:
        return validation_error_response(errors)
    
    return created_response(
        data=class_data,
        message="Class created successfully"
    )


@classes_bp.route('/<class_id>', methods=['PUT'])
@token_required
def update_class(current_user, class_id):
    """
    Update an existing class.
    
    Path Parameters:
        - class_id: Class ID
    
    Request Body:
        - class_name: Class name (optional)
        - wali_kelas_id: Homeroom teacher ID (optional)
    
    Returns:
        Updated class data
    """
    data = request.get_json()
    
    if not data:
        return validation_error_response(
            {"_schema": ["Request body is required"]},
            message="Invalid request"
        )
    
    class_data, errors = class_service.update_class(class_id, data)
    
    if errors:
        # Check if it's a not found error
        if "class_id" in errors and "not found" in str(errors["class_id"]).lower():
            return not_found_response("Class")
        return validation_error_response(errors)
    
    return success_response(
        data=class_data,
        message="Class updated successfully"
    )


@classes_bp.route('/<class_id>', methods=['DELETE'])
@token_required
def delete_class(current_user, class_id):
    """
    Delete a class.
    Cannot delete if class has active students.
    
    Path Parameters:
        - class_id: Class ID
    
    Returns:
        Success message
    """
    success, error = class_service.delete_class(class_id)
    
    if not success:
        if "not found" in error.lower():
            return not_found_response("Class")
        # Conflict error (has active students)
        return conflict_response(error)
    
    return success_response(message="Class deleted successfully")
