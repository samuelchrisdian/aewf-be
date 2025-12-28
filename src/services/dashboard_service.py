"""
Dashboard service for business logic.
Handles all business operations for dashboard statistics.
"""
from datetime import date
from typing import Optional, Any

from src.repositories.dashboard_repo import dashboard_repository
from src.repositories.teacher_repo import teacher_repository


class DashboardService:
    """Service class for Dashboard business logic."""
    
    def __init__(self):
        self.repository = dashboard_repository
    
    def get_dashboard_stats(self, current_user: Optional[Any] = None) -> dict:
        """
        Get complete dashboard statistics with role-based filtering.

        Aggregates all dashboard data including:
        - Entity overview (students, classes, teachers)
        - Today's attendance breakdown
        - This month's statistics with trend
        - Risk level summary
        
        Args:
            current_user: Current authenticated user (for role-based filtering)

        Returns:
            dict: Complete dashboard statistics
        """
        # Get class IDs for teacher role
        class_ids = None
        if current_user and current_user.role == 'Teacher':
            # Get classes managed by this teacher (wali kelas)
            teacher_classes = teacher_repository.get_classes_by_teacher(current_user.username)
            if teacher_classes:
                class_ids = [cls.class_id for cls in teacher_classes]
            else:
                # Teacher has no classes, return empty/zero stats
                class_ids = []

        # Get all dashboard components with class filtering
        overview = self.repository.get_entity_counts(class_ids=class_ids)
        today_attendance = self.repository.get_today_attendance(class_ids=class_ids)
        this_month = self.repository.get_month_attendance(class_ids=class_ids)
        risk_summary = self.repository.get_risk_summary(class_ids=class_ids)

        return {
            "overview": overview,
            "today_attendance": today_attendance,
            "this_month": this_month,
            "risk_summary": risk_summary
        }


# Singleton instance
dashboard_service = DashboardService()
