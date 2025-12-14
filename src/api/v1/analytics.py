"""
Analytics API endpoints.
Provides operations for analytics and reporting data.
"""
from flask import Blueprint, request

from src.app.middleware import token_required
from src.services.analytics_service import analytics_service
from src.utils.response_helpers import (
    success_response,
    not_found_response,
    validation_error_response
)


analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/v1/analytics')


@analytics_bp.route('/trends', methods=['GET'])
@token_required
def get_trends(current_user):
    """
    Get attendance trend data for charts.
    
    Query Parameters:
        - period: "weekly" or "monthly" (default: "weekly")
        - start_date: Start of date range (YYYY-MM-DD)
        - end_date: End of date range (YYYY-MM-DD)
    
    Returns:
        Time-series attendance data for charting
    """
    period = request.args.get('period', 'weekly')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Validate period
    if period not in ['weekly', 'monthly']:
        return validation_error_response(
            {"period": ["Must be 'weekly' or 'monthly'"]},
            message="Invalid period"
        )
    
    trends = analytics_service.get_trends(
        period=period,
        start_date=start_date,
        end_date=end_date
    )
    
    return success_response(
        data=trends,
        message="Attendance trends retrieved successfully"
    )


@analytics_bp.route('/class-comparison', methods=['GET'])
@token_required
def get_class_comparison(current_user):
    """
    Get per-class attendance comparison.
    
    Query Parameters:
        - period: Month period (YYYY-MM), defaults to current month
    
    Returns:
        Class-by-class attendance statistics sorted by performance
    """
    period = request.args.get('period')
    
    comparison = analytics_service.get_class_comparison(period=period)
    
    return success_response(
        data=comparison,
        message="Class comparison retrieved successfully"
    )


@analytics_bp.route('/student-patterns/<nis>', methods=['GET'])
@token_required
def get_student_patterns(current_user, nis):
    """
    Get individual student attendance patterns.
    
    Path Parameters:
        - nis: Student NIS
    
    Returns:
        Student's attendance patterns including:
        - Summary statistics
        - Weekly pattern analysis
        - Trend direction
        - Consecutive absence patterns
    """
    patterns, error = analytics_service.get_student_patterns(nis)
    
    if error:
        return not_found_response("Student")
    
    return success_response(
        data=patterns,
        message="Student patterns retrieved successfully"
    )
