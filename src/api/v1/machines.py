"""
Machines API endpoints.
Provides CRUD operations for fingerprint machine management.
"""
from flask import Blueprint, request

from src.app.middleware import token_required
from src.services.machine_service import machine_service
from src.utils.response_helpers import (
    success_response,
    created_response,
    paginated_response,
    not_found_response,
    validation_error_response,
    conflict_response
)
from src.utils.pagination import get_pagination_params
from src.utils.validators import validate_sort_params, validate_boolean_param


machines_bp = Blueprint('machines', __name__, url_prefix='/api/v1/machines')


@machines_bp.route('', methods=['GET'])
@token_required
def get_machines(current_user):
    """
    Get paginated list of machines.
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - status: Filter by status (active/inactive)
        - search: Search by machine_code or location
        - sort_by: Sort field (machine_code, location)
        - order: Sort order (asc, desc)
    
    Returns:
        Paginated list of machines with user counts
    """
    # Get pagination params
    page, per_page = get_pagination_params(request.args)
    
    # Get filter params
    status = request.args.get('status')
    search = request.args.get('search')
    
    # Get sort params
    sort_by = request.args.get('sort_by')
    order = request.args.get('order', 'asc')
    
    # Validate sort params
    sort_by, order = validate_sort_params(
        sort_by, order, ['machine_code', 'location']
    )
    
    # Get machines
    result = machine_service.get_machines(
        page=page,
        per_page=per_page,
        status=status,
        search=search,
        sort_by=sort_by,
        order=order
    )
    
    return paginated_response(
        data=result["data"],
        pagination=result["pagination"],
        message="Machines retrieved successfully"
    )


@machines_bp.route('/<int:machine_id>', methods=['GET'])
@token_required
def get_machine(current_user, machine_id):
    """
    Get a single machine by ID.
    
    Path Parameters:
        - machine_id: Machine ID
    
    Returns:
        Machine details with user count
    """
    machine_data, error = machine_service.get_machine(machine_id)
    
    if error:
        return not_found_response("Machine")
    
    return success_response(
        data=machine_data,
        message="Machine retrieved successfully"
    )


@machines_bp.route('', methods=['POST'])
@token_required
def create_machine(current_user):
    """
    Create a new machine.
    
    Request Body:
        - machine_code: Unique machine code (required)
        - location: Machine location (optional)
        - status: Machine status - active/inactive (optional, default: active)
    
    Returns:
        Created machine data
    """
    data = request.get_json()
    
    if not data:
        return validation_error_response(
            {"_schema": ["Request body is required"]},
            message="Invalid request"
        )
    
    machine_data, errors = machine_service.create_machine(data)
    
    if errors:
        return validation_error_response(errors)
    
    return created_response(
        data=machine_data,
        message="Machine created successfully"
    )


@machines_bp.route('/<int:machine_id>', methods=['PUT'])
@token_required
def update_machine(current_user, machine_id):
    """
    Update an existing machine.
    
    Path Parameters:
        - machine_id: Machine ID
    
    Request Body:
        - location: Machine location (optional)
        - status: Machine status (optional)
    
    Returns:
        Updated machine data
    """
    data = request.get_json()
    
    if not data:
        return validation_error_response(
            {"_schema": ["Request body is required"]},
            message="Invalid request"
        )
    
    machine_data, errors = machine_service.update_machine(machine_id, data)
    
    if errors:
        # Check if it's a not found error
        if "id" in errors and "not found" in str(errors["id"]).lower():
            return not_found_response("Machine")
        return validation_error_response(errors)
    
    return success_response(
        data=machine_data,
        message="Machine updated successfully"
    )


@machines_bp.route('/<int:machine_id>', methods=['DELETE'])
@token_required
def delete_machine(current_user, machine_id):
    """
    Delete a machine.
    
    Path Parameters:
        - machine_id: Machine ID
    
    Returns:
        Success message
    """
    success, error = machine_service.delete_machine(machine_id)
    
    if not success:
        if "not found" in error.lower():
            return not_found_response("Machine")
        return conflict_response(error)
    
    return success_response(message="Machine deleted successfully")


@machines_bp.route('/<int:machine_id>/users', methods=['GET'])
@token_required
def get_machine_users(current_user, machine_id):
    """
    Get users registered on a machine.
    
    Path Parameters:
        - machine_id: Machine ID
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - search: Search by user name or ID
        - mapped: Filter by mapping status (true/false)
    
    Returns:
        Paginated list of machine users
    """
    # Get pagination params
    page, per_page = get_pagination_params(request.args)
    
    # Get filter params
    search = request.args.get('search')
    mapped = validate_boolean_param(request.args.get('mapped'))
    
    result, error = machine_service.get_machine_users(
        machine_id=machine_id,
        page=page,
        per_page=per_page,
        search=search,
        mapped_only=mapped
    )
    
    if error:
        return not_found_response("Machine")
    
    return paginated_response(
        data=result["data"],
        pagination=result["pagination"],
        message="Machine users retrieved successfully"
    )
