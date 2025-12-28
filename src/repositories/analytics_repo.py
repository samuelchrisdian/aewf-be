"""
Analytics repository for database operations.
Handles all direct database interactions for analytics queries.
"""
from typing import Optional, List
from datetime import date, datetime, timedelta
from calendar import monthrange
from sqlalchemy import func, and_, desc
from src.domain.models import Student, Class, AttendanceDaily
from src.app.extensions import db


class AnalyticsRepository:
    """Repository class for analytics database operations."""
    
    def get_attendance_trends(
        self,
        period: str = "weekly",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        class_ids: Optional[List[str]] = None
    ) -> List[dict]:
        """
        Get time-series attendance data with optional class filtering.

        Args:
            period: "weekly" or "monthly"
            start_date: Start of date range
            end_date: End of date range
            class_ids: Filter by class IDs (for teacher role)

        Returns:
            List of attendance data points for charting
        """
        if end_date is None:
            end_date = date.today()
        
        if start_date is None:
            # Default: last 12 weeks for weekly, last 12 months for monthly
            if period == "weekly":
                start_date = end_date - timedelta(weeks=12)
            else:
                start_date = date(end_date.year - 1, end_date.month, 1)
        
        if period == "weekly":
            return self._get_weekly_trends(start_date, end_date, class_ids)
        else:
            return self._get_monthly_trends(start_date, end_date, class_ids)

    def _get_weekly_trends(
        self,
        start_date: date,
        end_date: date,
        class_ids: Optional[List[str]] = None
    ) -> List[dict]:
        """Get weekly attendance trends with optional class filtering."""
        trends = []
        
        current = start_date
        while current <= end_date:
            week_end = current + timedelta(days=6)
            if week_end > end_date:
                week_end = end_date
            
            # Query attendance for this week
            query = db.session.query(
                AttendanceDaily.status,
                func.count(AttendanceDaily.id).label('count')
            ).filter(
                and_(
                    AttendanceDaily.attendance_date >= current,
                    AttendanceDaily.attendance_date <= week_end
                )
            )

            # Apply class filter if provided
            if class_ids is not None:
                if len(class_ids) == 0:
                    # Teacher has no classes, return empty
                    return []
                query = query.join(Student, AttendanceDaily.student_nis == Student.nis)
                query = query.filter(Student.class_id.in_(class_ids))

            query = query.group_by(AttendanceDaily.status)
            results = query.all()
            
            counts = {"present": 0, "late": 0, "absent": 0, "sick": 0, "permission": 0}
            for status, count in results:
                status_lower = status.lower() if status else ""
                if status_lower in counts:
                    counts[status_lower] = count
            
            total = sum(counts.values())
            present_count = counts["present"] + counts["late"]
            rate = round((present_count / total * 100), 1) if total > 0 else 0.0
            
            trends.append({
                "period": current.isoformat(),
                "period_end": week_end.isoformat(),
                "period_label": f"Week of {current.strftime('%b %d')}",
                "present": counts["present"],
                "late": counts["late"],
                "absent": counts["absent"],
                "sick": counts["sick"],
                "permission": counts["permission"],
                "total": total,
                "attendance_rate": rate
            })
            
            current = week_end + timedelta(days=1)
        
        return trends
    
    def _get_monthly_trends(
        self,
        start_date: date,
        end_date: date,
        class_ids: Optional[List[str]] = None
    ) -> List[dict]:
        """Get monthly attendance trends with optional class filtering."""
        trends = []
        
        current_year = start_date.year
        current_month = start_date.month
        
        while date(current_year, current_month, 1) <= end_date:
            month_start = date(current_year, current_month, 1)
            month_end_day = monthrange(current_year, current_month)[1]
            month_end = date(current_year, current_month, month_end_day)
            
            if month_end > end_date:
                month_end = end_date
            
            # Query attendance for this month
            query = db.session.query(
                AttendanceDaily.status,
                func.count(AttendanceDaily.id).label('count')
            ).filter(
                and_(
                    AttendanceDaily.attendance_date >= month_start,
                    AttendanceDaily.attendance_date <= month_end
                )
            )

            # Apply class filter if provided
            if class_ids is not None:
                if len(class_ids) == 0:
                    # Teacher has no classes, return empty
                    return []
                query = query.join(Student, AttendanceDaily.student_nis == Student.nis)
                query = query.filter(Student.class_id.in_(class_ids))

            query = query.group_by(AttendanceDaily.status)
            results = query.all()
            
            counts = {"present": 0, "late": 0, "absent": 0, "sick": 0, "permission": 0}
            for status, count in results:
                status_lower = status.lower() if status else ""
                if status_lower in counts:
                    counts[status_lower] = count
            
            total = sum(counts.values())
            present_count = counts["present"] + counts["late"]
            rate = round((present_count / total * 100), 1) if total > 0 else 0.0
            
            trends.append({
                "period": f"{current_year}-{current_month:02d}",
                "period_label": month_start.strftime("%b %Y"),
                "present": counts["present"],
                "late": counts["late"],
                "absent": counts["absent"],
                "sick": counts["sick"],
                "permission": counts["permission"],
                "total": total,
                "attendance_rate": rate
            })
            
            # Move to next month
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
        
        return trends
    
    def get_class_comparison(
        self,
        period: Optional[str] = None,
        class_ids: Optional[List[str]] = None
    ) -> List[dict]:
        """
        Get per-class attendance statistics with optional filtering.

        Args:
            period: Month period (YYYY-MM), defaults to current month
            class_ids: Filter by class IDs (for teacher role)

        Returns:
            List of class statistics
        """
        # Parse period or use current month
        if period:
            try:
                year, month = map(int, period.split('-'))
            except (ValueError, AttributeError):
                today = date.today()
                year, month = today.year, today.month
        else:
            today = date.today()
            year, month = today.year, today.month
        
        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        
        # Get classes based on filter
        if class_ids is not None:
            if len(class_ids) == 0:
                # Teacher has no classes
                return []
            classes = db.session.query(Class).filter(Class.class_id.in_(class_ids)).all()
        else:
            # Admin gets all classes
            classes = db.session.query(Class).all()

        result = []
        for cls in classes:
            # Get students in this class
            student_count = db.session.query(func.count(Student.nis)).filter(
                Student.class_id == cls.class_id,
                Student.is_active == True
            ).scalar() or 0
            
            # Get attendance stats for students in this class
            query = db.session.query(
                AttendanceDaily.status,
                func.count(AttendanceDaily.id).label('count')
            ).join(Student).filter(
                and_(
                    Student.class_id == cls.class_id,
                    AttendanceDaily.attendance_date >= start_date,
                    AttendanceDaily.attendance_date <= end_date
                )
            ).group_by(AttendanceDaily.status)
            
            stats = query.all()
            
            counts = {"present": 0, "late": 0, "absent": 0, "sick": 0, "permission": 0}
            for status, count in stats:
                status_lower = status.lower() if status else ""
                if status_lower in counts:
                    counts[status_lower] = count
            
            total = sum(counts.values())
            present_count = counts["present"] + counts["late"]
            attendance_rate = round((present_count / total * 100), 1) if total > 0 else 0.0
            
            # Calculate average late per day
            school_days = db.session.query(
                func.count(func.distinct(AttendanceDaily.attendance_date))
            ).join(Student).filter(
                and_(
                    Student.class_id == cls.class_id,
                    AttendanceDaily.attendance_date >= start_date,
                    AttendanceDaily.attendance_date <= end_date
                )
            ).scalar() or 1
            
            average_late = round(counts["late"] / school_days, 1) if school_days > 0 else 0.0
            
            # Count at-risk students (more than 3 absences in the period)
            at_risk_query = db.session.query(
                func.count(func.distinct(AttendanceDaily.student_nis))
            ).join(Student).filter(
                and_(
                    Student.class_id == cls.class_id,
                    AttendanceDaily.attendance_date >= start_date,
                    AttendanceDaily.attendance_date <= end_date,
                    AttendanceDaily.status.in_(['Absent', 'Sick', 'Permission'])
                )
            ).group_by(AttendanceDaily.student_nis).having(
                func.count(AttendanceDaily.id) > 3
            )
            
            at_risk_count = len(at_risk_query.all())
            
            result.append({
                "class_id": cls.class_id,
                "class_name": cls.class_name,
                "student_count": student_count,
                "attendance_rate": attendance_rate,
                "average_late": average_late,
                "at_risk_count": at_risk_count,
                "present": counts["present"],
                "late": counts["late"],
                "absent": counts["absent"]
            })
        
        # Sort by attendance rate descending
        result.sort(key=lambda x: x["attendance_rate"], reverse=True)
        
        return result
    
    def get_student_patterns(self, nis: str) -> Optional[dict]:
        """
        Get individual student attendance patterns.
        
        Args:
            nis: Student NIS
            
        Returns:
            Student pattern analysis or None if student not found
        """
        # Get student
        student = db.session.query(Student).filter(Student.nis == nis).first()
        if not student:
            return None
        
        # Get last 90 days of attendance
        ninety_days_ago = date.today() - timedelta(days=90)
        
        records = db.session.query(AttendanceDaily).filter(
            and_(
                AttendanceDaily.student_nis == nis,
                AttendanceDaily.attendance_date >= ninety_days_ago
            )
        ).order_by(desc(AttendanceDaily.attendance_date)).all()
        
        # Count by status
        counts = {"present": 0, "late": 0, "absent": 0, "sick": 0, "permission": 0}
        for record in records:
            status_lower = record.status.lower() if record.status else ""
            if status_lower in counts:
                counts[status_lower] += 1
        
        total = len(records)
        present_total = counts["present"] + counts["late"]
        attendance_rate = round((present_total / total * 100), 1) if total > 0 else 0.0
        
        # Analyze patterns by day of week
        day_patterns = {i: {"present": 0, "late": 0, "absent": 0} for i in range(5)}  # Mon-Fri
        for record in records:
            day = record.attendance_date.weekday()
            if day < 5:  # Weekday only
                status = record.status.lower() if record.status else ""
                if status in ["present"]:
                    day_patterns[day]["present"] += 1
                elif status in ["late"]:
                    day_patterns[day]["late"] += 1
                elif status in ["absent", "sick", "permission"]:
                    day_patterns[day]["absent"] += 1
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        weekly_pattern = []
        for i, name in enumerate(day_names):
            day_total = sum(day_patterns[i].values())
            day_present = day_patterns[i]["present"] + day_patterns[i]["late"]
            rate = round((day_present / day_total * 100), 1) if day_total > 0 else 0.0
            weekly_pattern.append({
                "day": name,
                "attendance_rate": rate,
                "late_count": day_patterns[i]["late"],
                "absent_count": day_patterns[i]["absent"]
            })
        
        # Find consecutive absences
        consecutive_absences = self._find_consecutive_absences(records)
        
        # Calculate trend (compare last 30 days vs previous 30 days)
        thirty_days_ago = date.today() - timedelta(days=30)
        sixty_days_ago = date.today() - timedelta(days=60)
        
        recent_records = [r for r in records if r.attendance_date >= thirty_days_ago]
        older_records = [r for r in records if sixty_days_ago <= r.attendance_date < thirty_days_ago]
        
        recent_present = sum(1 for r in recent_records if r.status.lower() in ["present", "late"])
        recent_rate = round((recent_present / len(recent_records) * 100), 1) if recent_records else 0.0
        
        older_present = sum(1 for r in older_records if r.status.lower() in ["present", "late"])
        older_rate = round((older_present / len(older_records) * 100), 1) if older_records else 0.0
        
        trend_value = round(recent_rate - older_rate, 1)
        if trend_value > 2:
            trend = "improving"
        elif trend_value < -2:
            trend = "declining"
        else:
            trend = "stable"
        
        return {
            "student": {
                "nis": student.nis,
                "name": student.name,
                "class_id": student.class_id,
                "class_name": student.student_class.class_name if student.student_class else None
            },
            "period": {
                "start": ninety_days_ago.isoformat(),
                "end": date.today().isoformat(),
                "days_analyzed": total
            },
            "summary": {
                "attendance_rate": attendance_rate,
                "present": counts["present"],
                "late": counts["late"],
                "absent": counts["absent"],
                "sick": counts["sick"],
                "permission": counts["permission"]
            },
            "trend": {
                "direction": trend,
                "recent_rate": recent_rate,
                "previous_rate": older_rate,
                "change": trend_value
            },
            "weekly_pattern": weekly_pattern,
            "consecutive_absences": consecutive_absences
        }
    
    def _find_consecutive_absences(self, records: List[AttendanceDaily]) -> List[dict]:
        """Find patterns of consecutive absences."""
        if not records:
            return []
        
        # Sort by date ascending
        sorted_records = sorted(records, key=lambda r: r.attendance_date)
        
        patterns = []
        current_streak = []
        
        for record in sorted_records:
            if record.status.lower() in ["absent", "sick", "permission"]:
                current_streak.append(record)
            else:
                if len(current_streak) >= 3:
                    patterns.append({
                        "start_date": current_streak[0].attendance_date.isoformat(),
                        "end_date": current_streak[-1].attendance_date.isoformat(),
                        "count": len(current_streak),
                        "types": list(set(r.status for r in current_streak))
                    })
                current_streak = []
        
        # Check final streak
        if len(current_streak) >= 3:
            patterns.append({
                "start_date": current_streak[0].attendance_date.isoformat(),
                "end_date": current_streak[-1].attendance_date.isoformat(),
                "count": len(current_streak),
                "types": list(set(r.status for r in current_streak))
            })
        
        return patterns


# Singleton instance
analytics_repository = AnalyticsRepository()
