"""
Dashboard API endpoints.
Provides operations for dashboard statistics.
"""
from flask import Blueprint

from src.app.middleware import token_required
from src.services.dashboard_service import dashboard_service
from src.utils.response_helpers import success_response


dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/v1/dashboard')


@dashboard_bp.route('/stats', methods=['GET'])
@token_required
def get_dashboard_stats(current_user):
    """
    Get complete dashboard statistics.
    
    Returns aggregated data including:
        - overview: Entity counts (students, classes, teachers)
        - today_attendance: Today's attendance breakdown
        - this_month: Monthly statistics with trend
        - risk_summary: Students by risk level
    
    Returns:
        Dashboard statistics JSON response
    """
    stats = dashboard_service.get_dashboard_stats()
    
    return success_response(
        data=stats,
        message="Dashboard stats retrieved successfully"
    )
