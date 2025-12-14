"""
Dashboard service for business logic.
Handles all business operations for dashboard statistics.
"""
from datetime import date
from typing import Optional

from src.repositories.dashboard_repo import dashboard_repository


class DashboardService:
    """Service class for Dashboard business logic."""
    
    def __init__(self):
        self.repository = dashboard_repository
    
    def get_dashboard_stats(self) -> dict:
        """
        Get complete dashboard statistics.
        
        Aggregates all dashboard data including:
        - Entity overview (students, classes, teachers)
        - Today's attendance breakdown
        - This month's statistics with trend
        - Risk level summary
        
        Returns:
            dict: Complete dashboard statistics
        """
        # Get all dashboard components
        overview = self.repository.get_entity_counts()
        today_attendance = self.repository.get_today_attendance()
        this_month = self.repository.get_month_attendance()
        risk_summary = self.repository.get_risk_summary()
        
        return {
            "overview": overview,
            "today_attendance": today_attendance,
            "this_month": this_month,
            "risk_summary": risk_summary
        }


# Singleton instance
dashboard_service = DashboardService()
