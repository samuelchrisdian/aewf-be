"""
Notifications API endpoints.
Provides operations for in-app notifications and notification settings.
"""
from flask import Blueprint, request

from src.app.middleware import token_required
from src.services.notification_service import notification_service
from src.schemas.notification_schema import (
    send_notification_schema,
    notification_settings_update_schema
)
from src.utils.response_helpers import (
    success_response,
    paginated_response,
    not_found_response,
    validation_error_response,
    error_response
)


notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/v1/notifications')


@notifications_bp.route('', methods=['GET'])
@token_required
def get_notifications(current_user):
    """
    Get notifications for the current user.
    
    Query Parameters:
        - is_read: Filter by read status (true/false)
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
    
    Returns:
        List of notifications with unread count
    """
    # Parse query parameters
    is_read_param = request.args.get('is_read')
    is_read = None
    if is_read_param is not None:
        is_read = is_read_param.lower() == 'true'
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # For now, assume current user is a teacher
    # In production, you'd determine recipient_type from user role
    recipient_type = 'teacher'
    recipient_id = str(current_user.id)  # Use user ID as recipient ID
    
    data, pagination = notification_service.get_notifications(
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        is_read=is_read,
        page=page,
        per_page=per_page
    )
    
    return paginated_response(
        data=data,
        pagination=pagination,
        message="Notifications retrieved successfully"
    )


@notifications_bp.route('/send', methods=['POST'])
@token_required
def send_notification(current_user):
    """
    Send a notification.
    
    Request Body:
        - recipient_type: 'teacher' or 'parent' (required)
        - recipient_id: Teacher ID or parent phone (required)
        - type: 'risk_alert', 'attendance', 'custom' (default: 'custom')
        - title: Notification title (required)
        - message: Notification body (required)
        - priority: 'high', 'normal', 'low' (default: 'normal')
        - channel: 'in_app', 'email', 'sms' (default: 'in_app')
        - action_url: Optional action URL
    
    Returns:
        Created notification details
    """
    json_data = request.get_json() or {}
    
    # Validate input
    errors = send_notification_schema.validate(json_data)
    if errors:
        return validation_error_response(errors)
    
    data = send_notification_schema.load(json_data)
    
    notification = notification_service.send_notification(data)
    
    return success_response(
        data=notification,
        message="Notification sent successfully",
        status_code=201
    )


@notifications_bp.route('/<int:notification_id>/read', methods=['PUT'])
@token_required
def mark_notification_read(current_user, notification_id):
    """
    Mark a notification as read.
    
    Path Parameters:
        - notification_id: ID of the notification
    
    Returns:
        Success confirmation
    """
    # Determine recipient info from current user
    recipient_type = 'teacher'
    recipient_id = str(current_user.id)
    
    success, error = notification_service.mark_as_read(
        notification_id=notification_id,
        recipient_type=recipient_type,
        recipient_id=recipient_id
    )
    
    if not success:
        return not_found_response("Notification")
    
    return success_response(message="Notification marked as read")


@notifications_bp.route('/<int:notification_id>', methods=['DELETE'])
@token_required
def delete_notification(current_user, notification_id):
    """
    Delete a notification.
    
    Path Parameters:
        - notification_id: ID of the notification
    
    Returns:
        Success confirmation
    """
    # Determine recipient info from current user
    recipient_type = 'teacher'
    recipient_id = str(current_user.id)
    
    success, error = notification_service.delete_notification(
        notification_id=notification_id,
        recipient_type=recipient_type,
        recipient_id=recipient_id
    )
    
    if not success:
        return not_found_response("Notification")
    
    return success_response(message="Notification deleted successfully")


@notifications_bp.route('/settings', methods=['GET'])
@token_required
def get_notification_settings(current_user):
    """
    Get notification settings for the current user.
    
    Returns:
        Notification settings
    """
    # Use user ID from current user
    user_id = current_user.id
    
    settings = notification_service.get_settings(user_id)
    
    return success_response(
        data=settings,
        message="Notification settings retrieved successfully"
    )


@notifications_bp.route('/settings', methods=['PUT'])
@token_required
def update_notification_settings(current_user):
    """
    Update notification settings for the current user.
    
    Request Body:
        - enable_risk_alerts: Boolean
        - enable_attendance: Boolean
        - enable_email: Boolean
        - enable_sms: Boolean
        - daily_digest_time: Time in HH:MM format
    
    Returns:
        Updated notification settings
    """
    json_data = request.get_json() or {}
    
    # Validate input
    errors = notification_settings_update_schema.validate(json_data)
    if errors:
        return validation_error_response(errors)
    
    data = notification_settings_update_schema.load(json_data)
    
    # For now, use user ID
    user_id = current_user.id
    
    settings = notification_service.update_settings(user_id, data)
    
    return success_response(
        data=settings,
        message="Notification settings updated successfully"
    )
