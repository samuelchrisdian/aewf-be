"""
Dashboard repository for database operations.
Handles all direct database interactions for dashboard statistics.
"""
from typing import Optional, List
from datetime import date, datetime, timedelta
from calendar import monthrange
from sqlalchemy import func, and_, case
from src.domain.models import Student, Class, Teacher, AttendanceDaily
from src.app.extensions import db


class DashboardRepository:
    """Repository class for dashboard statistics database operations."""
    
    def get_entity_counts(self, class_ids: Optional[List[str]] = None) -> dict:
        """
        Get counts of main entities.
        
        Args:
            class_ids: Filter by class IDs (for teacher role)

        Returns:
            dict: Entity counts (students, active students, classes, teachers)
        """
        # Build student queries with optional class filter
        student_query = db.session.query(func.count(Student.nis))
        active_student_query = db.session.query(func.count(Student.nis)).filter(
            Student.is_active == True
        )

        if class_ids is not None:
            if len(class_ids) == 0:
                # Teacher has no classes
                return {
                    "total_students": 0,
                    "active_students": 0,
                    "total_classes": 0,
                    "total_teachers": 0
                }
            student_query = student_query.filter(Student.class_id.in_(class_ids))
            active_student_query = active_student_query.filter(Student.class_id.in_(class_ids))

        total_students = student_query.scalar() or 0
        active_students = active_student_query.scalar() or 0

        # For teacher role, count only their classes
        if class_ids is not None:
            total_classes = len(class_ids)
            # Teachers count is 1 for the teacher themselves
            total_teachers = 1
        else:
            # Admin gets all counts
            total_classes = db.session.query(func.count(Class.class_id)).scalar() or 0
            total_teachers = db.session.query(func.count(Teacher.teacher_id)).scalar() or 0

        return {
            "total_students": total_students,
            "active_students": active_students,
            "total_classes": total_classes,
            "total_teachers": total_teachers
        }
    
    def get_today_attendance(
        self,
        target_date: Optional[date] = None,
        class_ids: Optional[List[str]] = None
    ) -> dict:
        """
        Get attendance breakdown for a specific date.
        
        Args:
            target_date: Date to check (defaults to today)
            class_ids: Filter by class IDs (for teacher role)

        Returns:
            dict: Today's attendance statistics
        """
        if target_date is None:
            target_date = date.today()
        
        # Build query with optional class filter
        query = db.session.query(
            AttendanceDaily.status,
            func.count(AttendanceDaily.id).label('count')
        ).filter(
            AttendanceDaily.attendance_date == target_date
        )

        # Add class filter if provided
        if class_ids is not None:
            if len(class_ids) == 0:
                # Teacher has no classes, return zero stats
                return {
                    "date": target_date.isoformat(),
                    "present": 0,
                    "late": 0,
                    "absent": 0,
                    "sick": 0,
                    "permission": 0,
                    "rate": 0.0
                }
            # Join with Student to filter by class_id
            query = query.join(Student, AttendanceDaily.student_nis == Student.nis)
            query = query.filter(Student.class_id.in_(class_ids))

        query = query.group_by(AttendanceDaily.status)
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
        month: Optional[int] = None,
        class_ids: Optional[List[str]] = None
    ) -> dict:
        """
        Get aggregated attendance statistics for a month.
        
        Args:
            year: Year (defaults to current year)
            month: Month (defaults to current month)
            class_ids: Filter by class IDs (for teacher role)

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
        
        # Build query with optional class filter
        query = db.session.query(
            AttendanceDaily.status,
            func.count(AttendanceDaily.id).label('count')
        ).filter(
            and_(
                AttendanceDaily.attendance_date >= first_day,
                AttendanceDaily.attendance_date <= last_day
            )
        )

        # Add class filter if provided
        if class_ids is not None:
            if len(class_ids) == 0:
                # Teacher has no classes, return zero stats
                return {
                    "average_rate": 0.0,
                    "trend": "+0.0%",
                    "total_lates": 0,
                    "total_absents": 0
                }
            # Join with Student to filter by class_id
            query = query.join(Student, AttendanceDaily.student_nis == Student.nis)
            query = query.filter(Student.class_id.in_(class_ids))

        query = query.group_by(AttendanceDaily.status)
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
        )

        # Add class filter to previous month query
        if class_ids is not None and len(class_ids) > 0:
            prev_query = prev_query.join(Student, AttendanceDaily.student_nis == Student.nis)
            prev_query = prev_query.filter(Student.class_id.in_(class_ids))

        prev_query = prev_query.group_by(AttendanceDaily.status)
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
    
    def get_risk_summary(self, class_ids: Optional[List[str]] = None) -> dict:
        """
        Get summary of students by risk level.
        
        Note: This is a placeholder implementation. Full risk calculation
        will be implemented in Phase 5 (EWS Enhancement).
        Currently returns estimated risk based on attendance patterns.
        
        Args:
            class_ids: Filter by class IDs (for teacher role)

        Returns:
            dict: Risk level counts
        """
        # Get active students count for low risk baseline
        active_students_query = db.session.query(func.count(Student.nis)).filter(
            Student.is_active == True
        )

        if class_ids is not None:
            if len(class_ids) == 0:
                # Teacher has no classes
                return {
                    "high_risk": 0,
                    "medium_risk": 0,
                    "low_risk": 0
                }
            active_students_query = active_students_query.filter(Student.class_id.in_(class_ids))

        active_students = active_students_query.scalar() or 0

        # Calculate risk based on last 30 days attendance
        thirty_days_ago = date.today() - timedelta(days=30)
        
        # Students with more than 3 absences in last 30 days = high risk
        high_risk_query = db.session.query(
            AttendanceDaily.student_nis,
            func.count(AttendanceDaily.id).label('absence_count')
        ).filter(
            and_(
                AttendanceDaily.attendance_date >= thirty_days_ago,
                AttendanceDaily.status.in_(['Absent', 'Sick', 'Permission'])
            )
        )

        # Add class filter if provided
        if class_ids is not None and len(class_ids) > 0:
            high_risk_query = high_risk_query.join(Student, AttendanceDaily.student_nis == Student.nis)
            high_risk_query = high_risk_query.filter(Student.class_id.in_(class_ids))

        high_risk_query = high_risk_query.group_by(AttendanceDaily.student_nis).having(
            func.count(AttendanceDaily.id) > 3
        )
        
        high_risk = len(high_risk_query.all())
        
        # Students with 1-3 absences = medium risk
        medium_risk_query = db.session.query(
            AttendanceDaily.student_nis,
            func.count(AttendanceDaily.id).label('absence_count')
        ).filter(
            and_(
                AttendanceDaily.attendance_date >= thirty_days_ago,
                AttendanceDaily.status.in_(['Absent', 'Sick', 'Permission'])
            )
        )

        # Add class filter if provided
        if class_ids is not None and len(class_ids) > 0:
            medium_risk_query = medium_risk_query.join(Student, AttendanceDaily.student_nis == Student.nis)
            medium_risk_query = medium_risk_query.filter(Student.class_id.in_(class_ids))

        medium_risk_query = medium_risk_query.group_by(AttendanceDaily.student_nis).having(
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
