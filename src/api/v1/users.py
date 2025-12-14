"""
User Management API endpoints.
Provides CRUD operations for user administration (Admin only).
"""
from flask import Blueprint, request

from src.app.middleware import token_required, role_required
from src.services.user_service import user_service
from src.schemas.user_schema import user_create_schema, user_update_schema
from src.utils.response_helpers import (
    success_response,
    created_response,
    paginated_response,
    not_found_response,
    error_response,
    validation_error_response
)


users_bp = Blueprint('users', __name__, url_prefix='/api/v1/users')


def get_client_info():
    """Extract client info from request."""
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')[:500]
    return ip_address, user_agent


@users_bp.route('', methods=['GET'])
@token_required
@role_required(['Admin'])
def list_users(current_user):
    """
    List all users with pagination and filtering.
    Admin only.
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
        - is_active: Filter by active status (true/false)
        - role: Filter by role (Admin/Teacher/Staff)
        - search: Search by username or email
    
    Returns:
        Paginated list of users
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Parse is_active filter
    is_active_param = request.args.get('is_active')
    is_active = None
    if is_active_param is not None:
        is_active = is_active_param.lower() == 'true'
    
    role = request.args.get('role')
    search = request.args.get('search')
    
    users, pagination = user_service.list_users(
        page=page,
        per_page=per_page,
        is_active=is_active,
        role=role,
        search=search
    )
    
    return paginated_response(
        data=users,
        pagination=pagination,
        message="Users retrieved successfully"
    )


@users_bp.route('', methods=['POST'])
@token_required
@role_required(['Admin'])
def create_user(current_user):
    """
    Create a new user.
    Admin only.
    
    Request Body:
        - username: Unique username (required)
        - password: Password min 6 chars (required)
        - email: Email address (optional)
        - role: Admin/Teacher/Staff (default: Staff)
        - is_active: Active status (default: true)
    
    Returns:
        Created user data
    """
    json_data = request.get_json() or {}
    
    # Validate input
    errors = user_create_schema.validate(json_data)
    if errors:
        return validation_error_response(errors)
    
    data = user_create_schema.load(json_data)
    ip_address, user_agent = get_client_info()
    
    user, error = user_service.create_user(
        data=data,
        created_by_user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if error:
        return error_response(
            message=error,
            code="CREATE_FAILED",
            status_code=400
        )
    
    return created_response(
        data=user,
        message="User created successfully"
    )


@users_bp.route('/<int:user_id>', methods=['GET'])
@token_required
@role_required(['Admin'])
def get_user(current_user, user_id):
    """
    Get user by ID.
    Admin only.
    
    Path Parameters:
        - user_id: User ID
    
    Returns:
        User data
    """
    user, error = user_service.get_user(user_id)
    
    if error:
        return not_found_response("User")
    
    return success_response(
        data=user,
        message="User retrieved successfully"
    )


@users_bp.route('/<int:user_id>', methods=['PUT'])
@token_required
@role_required(['Admin'])
def update_user(current_user, user_id):
    """
    Update an existing user.
    Admin only.
    
    Path Parameters:
        - user_id: User ID
    
    Request Body:
        - username: New username (optional)
        - email: New email (optional)
        - role: New role (optional)
        - is_active: Active status (optional)
        - password: New password (optional)
    
    Returns:
        Updated user data
    """
    json_data = request.get_json() or {}
    
    # Validate input
    errors = user_update_schema.validate(json_data)
    if errors:
        return validation_error_response(errors)
    
    data = user_update_schema.load(json_data)
    ip_address, user_agent = get_client_info()
    
    user, error = user_service.update_user(
        user_id=user_id,
        data=data,
        updated_by_user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if error:
        if "not found" in error.lower():
            return not_found_response("User")
        return error_response(
            message=error,
            code="UPDATE_FAILED",
            status_code=400
        )
    
    return success_response(
        data=user,
        message="User updated successfully"
    )


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@token_required
@role_required(['Admin'])
def delete_user(current_user, user_id):
    """
    Delete a user (soft delete).
    Admin only. Cannot delete own account.
    
    Path Parameters:
        - user_id: User ID
    
    Returns:
        Success confirmation
    """
    ip_address, user_agent = get_client_info()
    
    success, error = user_service.delete_user(
        user_id=user_id,
        deleted_by_user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if error:
        if "not found" in error.lower():
            return not_found_response("User")
        return error_response(
            message=error,
            code="DELETE_FAILED",
            status_code=400
        )
    
    return success_response(message="User deleted successfully")


@users_bp.route('/<int:user_id>/activity-log', methods=['GET'])
@token_required
@role_required(['Admin'])
def get_activity_log(current_user, user_id):
    """
    Get activity log for a user.
    Admin only.
    
    Path Parameters:
        - user_id: User ID
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
        - action: Filter by action type (optional)
    
    Returns:
        Paginated list of activity log entries
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    action = request.args.get('action')
    
    logs, pagination, error = user_service.get_activity_log(
        user_id=user_id,
        page=page,
        per_page=per_page,
        action=action
    )
    
    if error:
        return not_found_response("User")
    
    return paginated_response(
        data=logs,
        pagination=pagination,
        message="Activity log retrieved successfully"
    )
