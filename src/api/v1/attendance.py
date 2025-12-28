"""
Attendance API endpoints.
Provides operations for attendance management.
"""
from flask import Blueprint, request

from src.app.middleware import token_required
from src.services.attendance_service import attendance_service
from src.utils.response_helpers import (
    success_response,
    created_response,
    paginated_response,
    not_found_response,
    validation_error_response
)
from src.utils.pagination import get_pagination_params


attendance_bp = Blueprint('attendance', __name__, url_prefix='/api/v1/attendance')


@attendance_bp.route('/daily', methods=['GET'])
@token_required
def get_daily_attendance(current_user):
    """
    Get paginated list of daily attendance with filtering.
    
    Query Parameters:
        - date: Specific date (YYYY-MM-DD)
        - class_id: Filter by class
        - status: Filter by status (Present, Absent, Late, Sick, Permission)
        - start_date: Start of date range (YYYY-MM-DD)
        - end_date: End of date range (YYYY-MM-DD)
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
    
    Note:
        - Admin role: Returns all attendance records
        - Teacher role: Returns only records from their classes

    Returns:
        Paginated list of attendance records with student info
    """
    # Get pagination params
    page, per_page = get_pagination_params(request.args)
    
    # Get filter params
    attendance_date = request.args.get('date')
    class_id = request.args.get('class_id')
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Get attendance records with role-based filtering
    result = attendance_service.get_daily_attendance(
        page=page,
        per_page=per_page,
        attendance_date=attendance_date,
        class_id=class_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        current_user=current_user
    )
    
    return paginated_response(
        data=result["data"],
        pagination=result["pagination"],
        message="Daily attendance retrieved successfully"
    )


@attendance_bp.route('/student/<nis>', methods=['GET'])
@token_required
def get_student_attendance(current_user, nis):
    """
    Get attendance history for a specific student.
    
    Path Parameters:
        - nis: Student NIS
    
    Query Parameters:
        - start_date: Start of date range (YYYY-MM-DD)
        - end_date: End of date range (YYYY-MM-DD)
        - month: Month filter (YYYY-MM) - overrides start_date/end_date
    
    Returns:
        Student attendance history with summary and patterns
    """
    # Get date params
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    month = request.args.get('month')
    
    # Get student attendance
    attendance_data, error = attendance_service.get_student_attendance(
        nis=nis,
        start_date=start_date,
        end_date=end_date,
        month=month
    )
    
    if error:
        return not_found_response("Student")
    
    return success_response(
        data=attendance_data,
        message="Student attendance retrieved successfully"
    )


@attendance_bp.route('/manual', methods=['POST'])
@token_required
def create_manual_attendance(current_user):
    """
    Create a manual attendance entry.
    
    Request Body:
        - student_nis: Student NIS (required)
        - attendance_date: Date (required, YYYY-MM-DD)
        - status: Status (required, one of: Present, Absent, Late, Sick, Permission)
        - notes: Notes/reason (optional)
        - recorded_by: Teacher ID who recorded (optional)
    
    Returns:
        Created attendance record
    """
    data = request.get_json()
    
    if not data:
        return validation_error_response(
            {"_schema": ["Request body is required"]},
            message="Invalid request"
        )
    
    # Set recorded_by to current user's related teacher if available
    # This could be enhanced to auto-set based on current_user
    
    attendance_data, errors = attendance_service.create_manual_attendance(data)
    
    if errors:
        return validation_error_response(errors)
    
    return created_response(
        data=attendance_data,
        message="Attendance recorded successfully"
    )


@attendance_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_attendance(current_user, id):
    """
    Update an existing attendance record.
    
    Path Parameters:
        - id: Attendance record ID
    
    Request Body:
        - status: Status (optional)
        - check_in: Check-in time (optional)
        - check_out: Check-out time (optional)
        - notes: Notes (optional)
    
    Returns:
        Updated attendance record
    """
    data = request.get_json()
    
    if not data:
        return validation_error_response(
            {"_schema": ["Request body is required"]},
            message="Invalid request"
        )
    
    attendance_data, errors = attendance_service.update_attendance(id, data)
    
    if errors:
        # Check if it's a not found error
        if "id" in errors and "not found" in str(errors["id"]).lower():
            return not_found_response("Attendance record")
        return validation_error_response(errors)
    
    return success_response(
        data=attendance_data,
        message="Attendance updated successfully"
    )


@attendance_bp.route('/summary', methods=['GET'])
@token_required
def get_attendance_summary(current_user):
    """
    Get aggregated attendance summary with daily breakdown.
    
    Query Parameters:
        - class_id: Filter by class (optional)
        - period: Month period (YYYY-MM) - overrides start_date/end_date
        - start_date: Start of custom date range (YYYY-MM-DD)
        - end_date: End of custom date range (YYYY-MM-DD)
    
    Returns:
        Attendance summary with statistics and daily breakdown
    """
    # Get params
    class_id = request.args.get('class_id')
    period = request.args.get('period')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Get summary
    summary_data = attendance_service.get_attendance_summary(
        class_id=class_id,
        period=period,
        start_date=start_date,
        end_date=end_date
    )
    
    return success_response(
        data=summary_data,
        message="Attendance summary retrieved successfully"
    )
