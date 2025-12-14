"""
Authentication API endpoints.
Provides login, logout, token refresh, and password change operations.
"""
from flask import Blueprint, request

from src.app.middleware import token_required
from src.services.auth_service import auth_service
from src.schemas.auth_schema import login_schema, change_password_schema, refresh_token_schema
from src.utils.response_helpers import (
    success_response,
    error_response,
    validation_error_response
)


auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')


def get_client_info():
    """Extract client info from request."""
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')[:500]  # Limit length
    return ip_address, user_agent


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    User login endpoint.
    
    Request Body:
        - username: User's username (required)
        - password: User's password (required)
    
    Returns:
        Access token, refresh token, and user info
    """
    json_data = request.get_json() or {}
    
    # Validate input
    errors = login_schema.validate(json_data)
    if errors:
        return validation_error_response(errors)
    
    data = login_schema.load(json_data)
    ip_address, user_agent = get_client_info()
    
    success, result = auth_service.login(
        username=data['username'],
        password=data['password'],
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if not success:
        return error_response(
            message=result,
            code="AUTHENTICATION_FAILED",
            status_code=401
        )
    
    return success_response(
        data=result,
        message="Login successful"
    )


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    """
    User logout endpoint.
    
    Invalidates the refresh token.
    
    Returns:
        Success confirmation
    """
    ip_address, user_agent = get_client_info()
    
    auth_service.logout(
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return success_response(message="Logout successful")


@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """
    Refresh access token endpoint.
    
    Request Body:
        - refresh_token: Valid refresh token (required)
    
    Returns:
        New access token
    """
    json_data = request.get_json() or {}
    
    # Validate input
    errors = refresh_token_schema.validate(json_data)
    if errors:
        return validation_error_response(errors)
    
    data = refresh_token_schema.load(json_data)
    
    success, result = auth_service.refresh_access_token(data['refresh_token'])
    
    if not success:
        return error_response(
            message=result,
            code="TOKEN_REFRESH_FAILED",
            status_code=401
        )
    
    return success_response(
        data=result,
        message="Token refreshed successfully"
    )


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    """
    Get current user info endpoint.
    
    Returns:
        Current authenticated user's details
    """
    user_data = auth_service.get_current_user(current_user.id)
    
    if not user_data:
        return error_response(
            message="User not found",
            code="NOT_FOUND",
            status_code=404
        )
    
    return success_response(
        data=user_data,
        message="User retrieved successfully"
    )


@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    """
    Change password endpoint.
    
    Request Body:
        - current_password: Current password (required)
        - new_password: New password (required, min 6 chars)
        - confirm_password: Password confirmation (required)
    
    Returns:
        Success confirmation
    """
    json_data = request.get_json() or {}
    
    # Validate input
    errors = change_password_schema.validate(json_data)
    if errors:
        return validation_error_response(errors)
    
    data = change_password_schema.load(json_data)
    ip_address, user_agent = get_client_info()
    
    success, error = auth_service.change_password(
        user_id=current_user.id,
        current_password=data['current_password'],
        new_password=data['new_password'],
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if not success:
        return error_response(
            message=error,
            code="PASSWORD_CHANGE_FAILED",
            status_code=400
        )
    
    return success_response(message="Password changed successfully")
