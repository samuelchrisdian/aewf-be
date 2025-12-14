"""
Risk Management API endpoints.
Provides operations for EWS risk assessment and alerts.
"""
from flask import Blueprint, request

from src.app.middleware import token_required
from src.services.risk_service import risk_service
from src.schemas.risk_schema import risk_alert_action_schema, risk_recalculate_schema
from src.utils.response_helpers import (
    success_response,
    paginated_response,
    not_found_response,
    validation_error_response,
    error_response
)


risk_bp = Blueprint('risk', __name__, url_prefix='/api/v1/risk')


@risk_bp.route('/list', methods=['GET'])
@token_required
def get_risk_list(current_user):
    """
    Get list of at-risk students.
    
    Query Parameters:
        - level: Filter by risk level ('high', 'medium', 'low')
        - class_id: Filter by class
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
    
    Returns:
        Paginated list of at-risk students sorted by risk score
    """
    level = request.args.get('level')
    class_id = request.args.get('class_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Validate level if provided
    if level and level not in ['high', 'medium', 'low']:
        return validation_error_response(
            {"level": ["Must be 'high', 'medium', or 'low'"]},
            message="Invalid risk level"
        )
    
    students, pagination = risk_service.get_at_risk_students(
        level=level,
        class_id=class_id,
        page=page,
        per_page=per_page
    )
    
    return paginated_response(
        data=students,
        pagination=pagination,
        message="At-risk students retrieved successfully"
    )


@risk_bp.route('/<nis>', methods=['GET'])
@token_required
def get_student_risk(current_user, nis):
    """
    Get detailed risk information for a specific student.
    
    Path Parameters:
        - nis: Student NIS
    
    Returns:
        Student's risk details including factors and score
    """
    risk_data, error = risk_service.get_student_risk(nis)
    
    if error:
        return not_found_response("Student")
    
    return success_response(
        data=risk_data,
        message="Student risk retrieved successfully"
    )


@risk_bp.route('/alerts', methods=['GET'])
@token_required
def get_alerts(current_user):
    """
    Get risk alerts.
    
    Query Parameters:
        - status: Filter by status ('pending', 'acknowledged', 'resolved')
        - class_id: Filter by class
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
    
    Returns:
        Paginated list of risk alerts
    """
    status = request.args.get('status')
    class_id = request.args.get('class_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Validate status if provided
    if status and status not in ['pending', 'acknowledged', 'resolved']:
        return validation_error_response(
            {"status": ["Must be 'pending', 'acknowledged', or 'resolved'"]},
            message="Invalid status"
        )
    
    alerts, pagination = risk_service.get_alerts(
        status=status,
        class_id=class_id,
        page=page,
        per_page=per_page
    )
    
    return paginated_response(
        data=alerts,
        pagination=pagination,
        message="Risk alerts retrieved successfully"
    )


@risk_bp.route('/alerts/<int:alert_id>/action', methods=['POST'])
@token_required
def take_alert_action(current_user, alert_id):
    """
    Take action on a risk alert.
    
    Path Parameters:
        - id: Alert ID
    
    Request Body:
        - action: Action taken (required)
        - notes: Action notes (optional)
        - follow_up_date: Follow-up date (optional)
        - status: New status (optional, defaults to 'acknowledged')
    
    Returns:
        Success confirmation
    """
    json_data = request.get_json() or {}
    
    # Validate input
    errors = risk_alert_action_schema.validate(json_data)
    if errors:
        return validation_error_response(errors)
    
    data = risk_alert_action_schema.load(json_data)
    
    success, error = risk_service.take_alert_action(
        alert_id=alert_id,
        action=data['action'],
        notes=data.get('notes'),
        follow_up_date=data.get('follow_up_date'),
        status=data.get('status', 'acknowledged')
    )
    
    if error:
        return not_found_response("Alert")
    
    return success_response(
        message="Alert action recorded successfully"
    )


@risk_bp.route('/history/<nis>', methods=['GET'])
@token_required
def get_risk_history(current_user, nis):
    """
    Get risk history for a student.
    
    Path Parameters:
        - nis: Student NIS
    
    Returns:
        Historical risk scores and factors
    """
    history, error = risk_service.get_risk_history(nis)
    
    if error:
        return not_found_response("Student")
    
    return success_response(
        data=history,
        message="Risk history retrieved successfully"
    )


@risk_bp.route('/recalculate', methods=['POST'])
@token_required
def recalculate_risks(current_user):
    """
    Trigger risk recalculation for students.
    
    Request Body (optional):
        - class_id: Recalculate only for specific class
        - student_nis: Recalculate only for specific student
    
    Returns:
        Recalculation results summary
    """
    json_data = request.get_json() or {}
    
    # Validate input
    errors = risk_recalculate_schema.validate(json_data)
    if errors:
        return validation_error_response(errors)
    
    data = risk_recalculate_schema.load(json_data)
    
    results = risk_service.recalculate_risks(
        class_id=data.get('class_id'),
        student_nis=data.get('student_nis')
    )
    
    return success_response(
        data=results,
        message="Risk recalculation completed"
    )
