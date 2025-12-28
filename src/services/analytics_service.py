"""
Analytics service for business logic.
Handles all business operations for analytics data.
"""
from typing import Optional, Any
from datetime import date, datetime

from src.repositories.analytics_repo import analytics_repository
from src.repositories.student_repo import student_repository
from src.repositories.teacher_repo import teacher_repository


class AnalyticsService:
    """Service class for Analytics business logic."""
    
    def __init__(self):
        self.repository = analytics_repository
    
    def get_trends(
        self,
        period: str = "weekly",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        current_user: Optional[Any] = None
    ) -> dict:
        """
        Get attendance trend data for charts with role-based filtering.

        Args:
            period: "weekly" or "monthly"
            start_date: Start of date range (YYYY-MM-DD)
            end_date: End of date range (YYYY-MM-DD)
            current_user: Current authenticated user (for role-based filtering)

        Returns:
            dict: Trend data with metadata and data points
        """
        # Parse dates
        parsed_start = self._parse_date(start_date)
        parsed_end = self._parse_date(end_date)
        
        # Role-based filtering
        class_ids = None
        if current_user and current_user.role == 'Teacher':
            # Get classes managed by this teacher (wali kelas)
            teacher_classes = teacher_repository.get_classes_by_teacher(current_user.username)
            if teacher_classes:
                class_ids = [cls.class_id for cls in teacher_classes]
            else:
                # Teacher has no classes, return empty result
                class_ids = []

        # Get trends from repository
        trends = self.repository.get_attendance_trends(
            period=period,
            start_date=parsed_start,
            end_date=parsed_end,
            class_ids=class_ids
        )
        
        return {
            "period": period,
            "start_date": (parsed_start or date.today()).isoformat() if parsed_start else None,
            "end_date": (parsed_end or date.today()).isoformat(),
            "data_points": len(trends),
            "trends": trends
        }
    
    def get_class_comparison(
        self,
        period: Optional[str] = None,
        current_user: Optional[Any] = None
    ) -> dict:
        """
        Get class comparison statistics with role-based filtering.

        Args:
            period: Month period (YYYY-MM)
            current_user: Current authenticated user (for role-based filtering)

        Returns:
            dict: Class comparison data
        """
        # Role-based filtering
        class_ids = None
        if current_user and current_user.role == 'Teacher':
            # Get classes managed by this teacher (wali kelas)
            teacher_classes = teacher_repository.get_classes_by_teacher(current_user.username)
            if teacher_classes:
                class_ids = [cls.class_id for cls in teacher_classes]
            else:
                # Teacher has no classes, return empty result
                class_ids = []

        comparison = self.repository.get_class_comparison(
            period=period,
            class_ids=class_ids
        )

        # Calculate additional insights
        if comparison:
            rates = [c["attendance_rate"] for c in comparison]
            average_rate = round(sum(rates) / len(rates), 1) if rates else 0.0
            best_class = comparison[0] if comparison else None
            worst_class = comparison[-1] if comparison else None
        else:
            average_rate = 0.0
            best_class = None
            worst_class = None
        
        return {
            "period": period or f"{date.today().year}-{date.today().month:02d}",
            "total_classes": len(comparison),
            "average_attendance_rate": average_rate,
            "best_performing": {
                "class_id": best_class["class_id"],
                "class_name": best_class["class_name"],
                "attendance_rate": best_class["attendance_rate"]
            } if best_class else None,
            "needs_attention": {
                "class_id": worst_class["class_id"],
                "class_name": worst_class["class_name"],
                "attendance_rate": worst_class["attendance_rate"]
            } if worst_class and worst_class["attendance_rate"] < 90 else None,
            "classes": comparison
        }
    
    def get_student_patterns(self, nis: str) -> tuple:
        """
        Get individual student attendance patterns.
        
        Args:
            nis: Student NIS
            
        Returns:
            tuple: (pattern_data, error)
        """
        # Check if student exists
        student = student_repository.get_by_nis(nis)
        if not student:
            return None, "Student not found"
        
        patterns = self.repository.get_student_patterns(nis)
        
        if patterns is None:
            return None, "Student not found"
        
        return patterns, None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None


# Singleton instance
analytics_service = AnalyticsService()
