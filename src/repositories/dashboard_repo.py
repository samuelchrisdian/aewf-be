"""
Dashboard repository for database operations.
Handles all direct database interactions for dashboard statistics.
"""
from typing import Optional
from datetime import date, datetime, timedelta
from calendar import monthrange
from sqlalchemy import func, and_, case
from src.domain.models import Student, Class, Teacher, AttendanceDaily
from src.app.extensions import db


class DashboardRepository:
    """Repository class for dashboard statistics database operations."""
    
    def get_entity_counts(self) -> dict:
        """
        Get counts of main entities.
        
        Returns:
            dict: Entity counts (students, active students, classes, teachers)
        """
        total_students = db.session.query(func.count(Student.nis)).scalar() or 0
        active_students = db.session.query(func.count(Student.nis)).filter(
            Student.is_active == True
        ).scalar() or 0
        total_classes = db.session.query(func.count(Class.class_id)).scalar() or 0
        total_teachers = db.session.query(func.count(Teacher.teacher_id)).scalar() or 0
        
        return {
            "total_students": total_students,
            "active_students": active_students,
            "total_classes": total_classes,
            "total_teachers": total_teachers
        }
    
    def get_today_attendance(self, target_date: Optional[date] = None) -> dict:
        """
        Get attendance breakdown for a specific date.
        
        Args:
            target_date: Date to check (defaults to today)
            
        Returns:
            dict: Today's attendance statistics
        """
        if target_date is None:
            target_date = date.today()
        
        # Count by status for the target date
        query = db.session.query(
            AttendanceDaily.status,
            func.count(AttendanceDaily.id).label('count')
        ).filter(
            AttendanceDaily.attendance_date == target_date
        ).group_by(AttendanceDaily.status)
        
        results = query.all()
        
        # Initialize counts
        counts = {
            "present": 0,
            "late": 0,
            "absent": 0,
            "sick": 0,
            "permission": 0
        }
        
        for status, count in results:
            status_lower = status.lower() if status else ""
            if status_lower in counts:
                counts[status_lower] = count
        
        # Calculate total and rate
        total = sum(counts.values())
        present_count = counts["present"] + counts["late"]  # Present includes on-time and late
        rate = round((present_count / total * 100), 1) if total > 0 else 0.0
        
        return {
            "date": target_date.isoformat(),
            "present": counts["present"],
            "late": counts["late"],
            "absent": counts["absent"],
            "sick": counts["sick"],
            "permission": counts["permission"],
            "rate": rate
        }
    
    def get_month_attendance(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> dict:
        """
        Get aggregated attendance statistics for a month.
        
        Args:
            year: Year (defaults to current year)
            month: Month (defaults to current month)
            
        Returns:
            dict: Monthly attendance statistics
        """
        if year is None or month is None:
            today = date.today()
            year = today.year
            month = today.month
        
        # Get first and last day of month
        first_day = date(year, month, 1)
        last_day_num = monthrange(year, month)[1]
        last_day = date(year, month, last_day_num)
        
        # Count by status for the month
        query = db.session.query(
            AttendanceDaily.status,
            func.count(AttendanceDaily.id).label('count')
        ).filter(
            and_(
                AttendanceDaily.attendance_date >= first_day,
                AttendanceDaily.attendance_date <= last_day
            )
        ).group_by(AttendanceDaily.status)
        
        results = query.all()
        
        counts = {
            "present": 0,
            "late": 0,
            "absent": 0,
            "sick": 0,
            "permission": 0
        }
        
        for status, count in results:
            status_lower = status.lower() if status else ""
            if status_lower in counts:
                counts[status_lower] = count
        
        total = sum(counts.values())
        present_count = counts["present"] + counts["late"]
        average_rate = round((present_count / total * 100), 1) if total > 0 else 0.0
        
        # Get previous month's rate for trend calculation
        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1
        
        prev_first_day = date(prev_year, prev_month, 1)
        prev_last_day_num = monthrange(prev_year, prev_month)[1]
        prev_last_day = date(prev_year, prev_month, prev_last_day_num)
        
        prev_query = db.session.query(
            AttendanceDaily.status,
            func.count(AttendanceDaily.id).label('count')
        ).filter(
            and_(
                AttendanceDaily.attendance_date >= prev_first_day,
                AttendanceDaily.attendance_date <= prev_last_day
            )
        ).group_by(AttendanceDaily.status)
        
        prev_results = prev_query.all()
        
        prev_counts = {"present": 0, "late": 0, "absent": 0, "sick": 0, "permission": 0}
        for status, count in prev_results:
            status_lower = status.lower() if status else ""
            if status_lower in prev_counts:
                prev_counts[status_lower] = count
        
        prev_total = sum(prev_counts.values())
        prev_present = prev_counts["present"] + prev_counts["late"]
        prev_rate = round((prev_present / prev_total * 100), 1) if prev_total > 0 else 0.0
        
        # Calculate trend
        trend_value = round(average_rate - prev_rate, 1)
        trend = f"+{trend_value}%" if trend_value >= 0 else f"{trend_value}%"
        
        return {
            "average_rate": average_rate,
            "trend": trend,
            "total_lates": counts["late"],
            "total_absents": counts["absent"] + counts["sick"] + counts["permission"]
        }
    
    def get_risk_summary(self) -> dict:
        """
        Get summary of students by risk level.
        
        Note: This is a placeholder implementation. Full risk calculation
        will be implemented in Phase 5 (EWS Enhancement).
        Currently returns estimated risk based on attendance patterns.
        
        Returns:
            dict: Risk level counts
        """
        # Get active students count for low risk baseline
        active_students = db.session.query(func.count(Student.nis)).filter(
            Student.is_active == True
        ).scalar() or 0
        
        # Calculate risk based on last 30 days attendance
        thirty_days_ago = date.today() - timedelta(days=30)
        
        # Students with more than 3 absences in last 30 days = high risk
        high_risk_query = db.session.query(
            func.count(func.distinct(AttendanceDaily.student_nis))
        ).filter(
            and_(
                AttendanceDaily.attendance_date >= thirty_days_ago,
                AttendanceDaily.status.in_(['Absent', 'Sick', 'Permission'])
            )
        ).group_by(AttendanceDaily.student_nis).having(
            func.count(AttendanceDaily.id) > 3
        )
        
        high_risk = len(high_risk_query.all())
        
        # Students with 1-3 absences = medium risk
        medium_risk_query = db.session.query(
            func.count(func.distinct(AttendanceDaily.student_nis))
        ).filter(
            and_(
                AttendanceDaily.attendance_date >= thirty_days_ago,
                AttendanceDaily.status.in_(['Absent', 'Sick', 'Permission'])
            )
        ).group_by(AttendanceDaily.student_nis).having(
            and_(
                func.count(AttendanceDaily.id) >= 1,
                func.count(AttendanceDaily.id) <= 3
            )
        )
        
        medium_risk = len(medium_risk_query.all())
        
        # Everyone else = low risk
        low_risk = max(0, active_students - high_risk - medium_risk)
        
        return {
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk
        }


# Singleton instance
dashboard_repository = DashboardRepository()
