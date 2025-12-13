"""
Attendance repository for database operations.
Handles all direct database interactions for AttendanceDaily model.
"""
from typing import Optional, List, Tuple
from datetime import date, datetime, timedelta
from sqlalchemy import func, and_
from src.domain.models import AttendanceDaily, Student, Class
from src.app.extensions import db


class AttendanceRepository:
    """Repository class for AttendanceDaily entity database operations."""
    
    def get_by_id(self, id: int) -> Optional[AttendanceDaily]:
        """
        Get attendance record by ID.
        
        Args:
            id: Attendance record ID
            
        Returns:
            AttendanceDaily or None if not found
        """
        return db.session.query(AttendanceDaily).filter(
            AttendanceDaily.id == id
        ).first()
    
    def get_daily(
        self,
        attendance_date: Optional[date] = None,
        class_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ):
        """
        Get query for daily attendance records with filters.
        
        Args:
            attendance_date: Specific date filter
            class_id: Filter by class
            status: Filter by status
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            SQLAlchemy query object
        """
        query = db.session.query(AttendanceDaily).join(
            Student, AttendanceDaily.student_nis == Student.nis
        )
        
        # Apply filters
        if attendance_date:
            query = query.filter(AttendanceDaily.attendance_date == attendance_date)
        
        if class_id:
            query = query.filter(Student.class_id == class_id)
        
        if status:
            query = query.filter(AttendanceDaily.status == status)
        
        if start_date:
            query = query.filter(AttendanceDaily.attendance_date >= start_date)
        
        if end_date:
            query = query.filter(AttendanceDaily.attendance_date <= end_date)
        
        # Order by date descending, then by student
        query = query.order_by(
            AttendanceDaily.attendance_date.desc(),
            Student.name.asc()
        )
        
        return query
    
    def get_by_student(
        self,
        nis: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[AttendanceDaily]:
        """
        Get attendance history for a student.
        
        Args:
            nis: Student NIS
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of AttendanceDaily records
        """
        query = db.session.query(AttendanceDaily).filter(
            AttendanceDaily.student_nis == nis
        )
        
        if start_date:
            query = query.filter(AttendanceDaily.attendance_date >= start_date)
        
        if end_date:
            query = query.filter(AttendanceDaily.attendance_date <= end_date)
        
        return query.order_by(AttendanceDaily.attendance_date.desc()).all()
    
    def exists_for_date(self, nis: str, attendance_date: date) -> bool:
        """
        Check if attendance record exists for student on date.
        
        Args:
            nis: Student NIS
            attendance_date: Date to check
            
        Returns:
            bool: True if exists
        """
        return db.session.query(
            db.session.query(AttendanceDaily).filter(
                AttendanceDaily.student_nis == nis,
                AttendanceDaily.attendance_date == attendance_date
            ).exists()
        ).scalar()
    
    def create(self, data: dict) -> AttendanceDaily:
        """
        Create a new attendance record.
        
        Args:
            data: Dictionary with attendance fields
            
        Returns:
            Created AttendanceDaily instance
        """
        attendance = AttendanceDaily(**data)
        db.session.add(attendance)
        db.session.commit()
        return attendance
    
    def update(self, id: int, update_data: dict) -> Optional[AttendanceDaily]:
        """
        Update an existing attendance record.
        
        Args:
            id: Attendance ID
            update_data: Dictionary with fields to update
            
        Returns:
            Updated AttendanceDaily or None if not found
        """
        attendance = self.get_by_id(id)
        if not attendance:
            return None
        
        for key, value in update_data.items():
            if hasattr(attendance, key):
                setattr(attendance, key, value)
        
        db.session.commit()
        return attendance
    
    def get_summary_stats(
        self,
        class_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """
        Get aggregated attendance statistics.
        
        Args:
            class_id: Filter by class
            start_date: Start of period
            end_date: End of period
            
        Returns:
            dict: Aggregated statistics
        """
        query = db.session.query(AttendanceDaily)
        
        if class_id:
            query = query.join(
                Student, AttendanceDaily.student_nis == Student.nis
            ).filter(Student.class_id == class_id)
        
        if start_date:
            query = query.filter(AttendanceDaily.attendance_date >= start_date)
        
        if end_date:
            query = query.filter(AttendanceDaily.attendance_date <= end_date)
        
        records = query.all()
        
        if not records:
            return {
                "total_school_days": 0,
                "average_attendance_rate": 0.0,
                "present_count": 0,
                "late_count": 0,
                "absent_count": 0,
                "sick_count": 0,
                "permission_count": 0
            }
        
        # Count by status
        status_counts = {
            "Present": 0,
            "Late": 0,
            "Absent": 0,
            "Sick": 0,
            "Permission": 0
        }
        
        unique_dates = set()
        for record in records:
            unique_dates.add(record.attendance_date)
            if record.status in status_counts:
                status_counts[record.status] += 1
        
        total = len(records)
        attended = status_counts["Present"] + status_counts["Late"]
        attendance_rate = round((attended / total) * 100, 1) if total > 0 else 0.0
        
        return {
            "total_school_days": len(unique_dates),
            "average_attendance_rate": attendance_rate,
            "present_count": status_counts["Present"],
            "late_count": status_counts["Late"],
            "absent_count": status_counts["Absent"],
            "sick_count": status_counts["Sick"],
            "permission_count": status_counts["Permission"]
        }
    
    def get_daily_breakdown(
        self,
        class_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[dict]:
        """
        Get day-by-day attendance counts.
        
        Args:
            class_id: Filter by class
            start_date: Start of period
            end_date: End of period
            
        Returns:
            List of daily attendance counts
        """
        query = db.session.query(
            AttendanceDaily.attendance_date,
            AttendanceDaily.status,
            func.count(AttendanceDaily.id).label('count')
        )
        
        if class_id:
            query = query.join(
                Student, AttendanceDaily.student_nis == Student.nis
            ).filter(Student.class_id == class_id)
        
        if start_date:
            query = query.filter(AttendanceDaily.attendance_date >= start_date)
        
        if end_date:
            query = query.filter(AttendanceDaily.attendance_date <= end_date)
        
        results = query.group_by(
            AttendanceDaily.attendance_date,
            AttendanceDaily.status
        ).order_by(AttendanceDaily.attendance_date.asc()).all()
        
        # Aggregate by date
        daily_data = {}
        for att_date, status, count in results:
            date_str = att_date.isoformat()
            if date_str not in daily_data:
                daily_data[date_str] = {
                    "date": att_date,
                    "present": 0,
                    "late": 0,
                    "absent": 0,
                    "sick": 0,
                    "permission": 0
                }
            
            status_key = status.lower() if status else "absent"
            if status_key in daily_data[date_str]:
                daily_data[date_str][status_key] = count
        
        return list(daily_data.values())
    
    def count_by_status(
        self,
        nis: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """
        Count attendance by status for a student.
        
        Args:
            nis: Student NIS
            start_date: Start of period
            end_date: End of period
            
        Returns:
            dict: Status counts
        """
        query = db.session.query(
            AttendanceDaily.status,
            func.count(AttendanceDaily.id).label('count')
        ).filter(AttendanceDaily.student_nis == nis)
        
        if start_date:
            query = query.filter(AttendanceDaily.attendance_date >= start_date)
        
        if end_date:
            query = query.filter(AttendanceDaily.attendance_date <= end_date)
        
        results = query.group_by(AttendanceDaily.status).all()
        
        counts = {
            "present": 0,
            "late": 0,
            "absent": 0,
            "sick": 0,
            "permission": 0,
            "total": 0
        }
        
        for status, count in results:
            status_key = status.lower() if status else "absent"
            if status_key in counts:
                counts[status_key] = count
            counts["total"] += count
        
        return counts


# Singleton instance
attendance_repository = AttendanceRepository()
