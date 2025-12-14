"""
System Configuration API endpoints.
Provides settings management and school calendar operations.
"""
from flask import Blueprint, request

from src.app.middleware import token_required, role_required
from src.services.config_service import config_service
from src.schemas.config_schema import settings_update_schema, holiday_create_schema
from src.utils.response_helpers import (
    success_response,
    created_response,
    error_response,
    not_found_response,
    validation_error_response
)


config_bp = Blueprint('config', __name__, url_prefix='/api/v1/config')


@config_bp.route('/settings', methods=['GET'])
@token_required
def get_settings(current_user):
    """
    Get all system settings.
    
    Returns:
        Complete system settings by category
    """
    settings = config_service.get_settings()
    
    return success_response(
        data=settings,
        message="Settings retrieved successfully"
    )


@config_bp.route('/settings', methods=['PUT'])
@token_required
@role_required(['Admin'])
def update_settings(current_user):
    """
    Update system settings.
    Admin only.
    
    Request Body:
        - attendance_rules: {...} (optional)
        - risk_thresholds: {...} (optional)
        - notification_settings: {...} (optional)
    
    Returns:
        Updated settings
    """
    json_data = request.get_json() or {}
    
    # Validate input
    errors = settings_update_schema.validate(json_data)
    if errors:
        return validation_error_response(errors)
    
    data = settings_update_schema.load(json_data)
    
    settings, error = config_service.update_settings(
        updates=data,
        user_id=current_user.id
    )
    
    if error:
        return error_response(
            message=error,
            code="UPDATE_FAILED",
            status_code=400
        )
    
    return success_response(
        data=settings,
        message="Settings updated successfully"
    )


@config_bp.route('/school-calendar', methods=['GET'])
@token_required
def get_school_calendar(current_user):
    """
    Get school calendar with holidays.
    
    Query Parameters:
        - year: Calendar year (default: current year)
        - month: Optional month filter (1-12)
    
    Returns:
        Calendar data with holidays and school settings
    """
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    calendar = config_service.get_school_calendar(year=year, month=month)
    
    return success_response(
        data=calendar,
        message="School calendar retrieved successfully"
    )


@config_bp.route('/holidays', methods=['POST'])
@token_required
@role_required(['Admin'])
def add_holiday(current_user):
    """
    Add a school holiday.
    Admin only.
    
    Request Body:
        - date: Holiday date (YYYY-MM-DD, required)
        - name: Holiday name (required)
        - type: holiday/break/event (default: holiday)
    
    Returns:
        Created holiday data
    """
    json_data = request.get_json() or {}
    
    # Validate input
    errors = holiday_create_schema.validate(json_data)
    if errors:
        return validation_error_response(errors)
    
    data = holiday_create_schema.load(json_data)
    
    holiday, error = config_service.add_holiday(
        date=data['date'],
        name=data['name'],
        type=data.get('type', 'holiday'),
        user_id=current_user.id
    )
    
    if error:
        return error_response(
            message=error,
            code="CREATE_FAILED",
            status_code=400
        )
    
    return created_response(
        data=holiday,
        message="Holiday added successfully"
    )


@config_bp.route('/holidays/<int:holiday_id>', methods=['DELETE'])
@token_required
@role_required(['Admin'])
def delete_holiday(current_user, holiday_id):
    """
    Delete a school holiday.
    Admin only.
    
    Path Parameters:
        - holiday_id: Holiday ID
    
    Returns:
        Success confirmation
    """
    success, error = config_service.remove_holiday(holiday_id)
    
    if error:
        return not_found_response("Holiday")
    
    return success_response(message="Holiday deleted successfully")
