"""
Attendance service for business logic.
Handles all business operations for attendance management.
"""
from typing import Optional, Tuple, List
from datetime import date, datetime
from calendar import monthrange
from marshmallow import ValidationError

from src.repositories.attendance_repo import attendance_repository
from src.repositories.student_repo import student_repository
from src.repositories.teacher_repo import teacher_repository
from src.schemas.attendance_schema import (
    attendance_create_schema,
    attendance_update_schema
)
from src.utils.pagination import paginate


class AttendanceService:
    """Service class for Attendance business logic."""
    
    def __init__(self):
        self.repository = attendance_repository
    
    def get_daily_attendance(
        self,
        page: int = 1,
        per_page: int = 20,
        attendance_date: Optional[str] = None,
        class_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        """
        Get paginated list of daily attendance with filters.
        
        Args:
            page: Page number
            per_page: Items per page
            attendance_date: Specific date (YYYY-MM-DD)
            class_id: Filter by class
            status: Filter by status
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            dict: Paginated attendance data
        """
        # Parse dates
        parsed_date = self._parse_date(attendance_date)
        parsed_start = self._parse_date(start_date)
        parsed_end = self._parse_date(end_date)
        
        # Get query with filters
        query = self.repository.get_daily(
            attendance_date=parsed_date,
            class_id=class_id,
            status=status,
            start_date=parsed_start,
            end_date=parsed_end
        )
        
        # Paginate
        result = paginate(query, page, per_page)
        
        # Serialize with student info
        attendance_data = []
        for record in result["items"]:
            student = record.student
            attendance_dict = {
                "id": record.id,
                "student_nis": record.student_nis,
                "student_name": student.name if student else None,
                "class_id": student.class_id if student else None,
                "class_name": student.student_class.class_name if student and student.student_class else None,
                "attendance_date": record.attendance_date.isoformat(),
                "check_in": record.check_in.isoformat() if record.check_in else None,
                "check_out": record.check_out.isoformat() if record.check_out else None,
                "status": record.status,
                "notes": record.notes,
                "recorded_by": record.recorded_by,
                "recorder_name": record.recorder.name if record.recorder else None
            }
            attendance_data.append(attendance_dict)
        
        return {
            "data": attendance_data,
            "pagination": result["pagination"]
        }
    
    def get_student_attendance(
        self,
        nis: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        month: Optional[str] = None
    ) -> Tuple[Optional[dict], Optional[str]]:
        """
        Get student attendance history with pattern analysis.
        
        Args:
            nis: Student NIS
            start_date: Start of date range (YYYY-MM-DD)
            end_date: End of date range (YYYY-MM-DD)
            month: Month filter (YYYY-MM)
            
        Returns:
            Tuple: (attendance_data, error_message)
        """
        # Check if student exists
        student = student_repository.get_by_nis(nis)
        if not student:
            return None, "Student not found"
        
        # Parse date range
        if month:
            parsed_start, parsed_end = self._parse_month_to_date_range(month)
        else:
            parsed_start = self._parse_date(start_date)
            parsed_end = self._parse_date(end_date)
        
        # Get attendance records
        records = self.repository.get_by_student(
            nis=nis,
            start_date=parsed_start,
            end_date=parsed_end
        )
        
        # Serialize records
        records_data = []
        for record in records:
            records_data.append({
                "id": record.id,
                "attendance_date": record.attendance_date.isoformat(),
                "check_in": record.check_in.isoformat() if record.check_in else None,
                "check_out": record.check_out.isoformat() if record.check_out else None,
                "status": record.status,
                "notes": record.notes
            })
        
        # Calculate summary
        status_counts = self.repository.count_by_status(
            nis=nis,
            start_date=parsed_start,
            end_date=parsed_end
        )
        
        total = status_counts["total"]
        attended = status_counts["present"] + status_counts["late"]
        attendance_rate = round((attended / total) * 100, 1) if total > 0 else 0.0
        
        summary = {
            "total_days": total,
            "present": status_counts["present"],
            "late": status_counts["late"],
            "absent": status_counts["absent"],
            "sick": status_counts["sick"],
            "permission": status_counts["permission"],
            "attendance_rate": attendance_rate
        }
        
        # Detect patterns
        patterns = {
            "consecutive_absences": self._detect_consecutive_absences(records)
        }
        
        return {
            "student": {
                "nis": student.nis,
                "name": student.name,
                "class_id": student.class_id,
                "class_name": student.student_class.class_name if student.student_class else None
            },
            "records": records_data,
            "summary": summary,
            "patterns": patterns
        }, None
    
    def create_manual_attendance(self, data: dict) -> Tuple[Optional[dict], Optional[dict]]:
        """
        Create a manual attendance entry.
        
        Args:
            data: Attendance data from request
            
        Returns:
            Tuple: (created_attendance, validation_errors)
        """
        # Validate input
        try:
            validated_data = attendance_create_schema.load(data)
        except ValidationError as err:
            return None, err.messages
        
        # Check if student exists
        if not student_repository.exists(validated_data['student_nis']):
            return None, {"student_nis": ["Student not found"]}
        
        # Check if attendance already exists for this date
        if self.repository.exists_for_date(
            validated_data['student_nis'],
            validated_data['attendance_date']
        ):
            return None, {"attendance_date": ["Attendance record already exists for this date"]}
        
        # Validate recorded_by if provided
        if validated_data.get('recorded_by'):
            if not teacher_repository.exists(validated_data['recorded_by']):
                return None, {"recorded_by": ["Teacher not found"]}
        
        # Create attendance
        attendance = self.repository.create(validated_data)
        
        # Get student info for response
        student = attendance.student
        
        return {
            "id": attendance.id,
            "student_nis": attendance.student_nis,
            "student_name": student.name if student else None,
            "attendance_date": attendance.attendance_date.isoformat(),
            "status": attendance.status,
            "notes": attendance.notes,
            "recorded_by": attendance.recorded_by
        }, None
    
    def update_attendance(self, id: int, data: dict) -> Tuple[Optional[dict], Optional[dict]]:
        """
        Update an existing attendance record.
        
        Args:
            id: Attendance record ID
            data: Update data from request
            
        Returns:
            Tuple: (updated_attendance, validation_errors)
        """
        # Check if attendance exists
        attendance = self.repository.get_by_id(id)
        if not attendance:
            return None, {"id": ["Attendance record not found"]}
        
        # Validate input
        try:
            validated_data = attendance_update_schema.load(data)
        except ValidationError as err:
            return None, err.messages
        
        # Update attendance
        updated = self.repository.update(id, validated_data)
        
        # Get student info for response
        student = updated.student
        
        return {
            "id": updated.id,
            "student_nis": updated.student_nis,
            "student_name": student.name if student else None,
            "attendance_date": updated.attendance_date.isoformat(),
            "check_in": updated.check_in.isoformat() if updated.check_in else None,
            "check_out": updated.check_out.isoformat() if updated.check_out else None,
            "status": updated.status,
            "notes": updated.notes
        }, None
    
    def get_attendance_summary(
        self,
        class_id: Optional[str] = None,
        period: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        """
        Get aggregated attendance summary with daily breakdown.
        
        Args:
            class_id: Filter by class
            period: Month period (YYYY-MM)
            start_date: Start of custom date range
            end_date: End of custom date range
            
        Returns:
            dict: Summary with statistics and daily breakdown
        """
        # Parse dates
        if period:
            parsed_start, parsed_end = self._parse_month_to_date_range(period)
        else:
            parsed_start = self._parse_date(start_date)
            parsed_end = self._parse_date(end_date)
        
        # Get statistics
        stats = self.repository.get_summary_stats(
            class_id=class_id,
            start_date=parsed_start,
            end_date=parsed_end
        )
        
        # Get daily breakdown
        daily_breakdown = self.repository.get_daily_breakdown(
            class_id=class_id,
            start_date=parsed_start,
            end_date=parsed_end
        )
        
        # Format daily breakdown for response
        formatted_breakdown = []
        for day in daily_breakdown:
            formatted_breakdown.append({
                "date": day["date"].isoformat() if isinstance(day["date"], date) else day["date"],
                "present": day["present"],
                "late": day["late"],
                "absent": day["absent"],
                "sick": day.get("sick", 0),
                "permission": day.get("permission", 0)
            })
        
        return {
            "period": period,
            "class_id": class_id,
            "stats": stats,
            "daily_breakdown": formatted_breakdown
        }
    
    def _detect_consecutive_absences(self, records: List) -> List[dict]:
        """
        Detect patterns of consecutive absences.
        
        Args:
            records: List of AttendanceDaily records (sorted by date desc)
            
        Returns:
            List of consecutive absence patterns
        """
        if not records:
            return []
        
        # Sort by date ascending for pattern detection
        sorted_records = sorted(records, key=lambda r: r.attendance_date)
        
        patterns = []
        current_streak = []
        
        for record in sorted_records:
            if record.status in ["Absent", "Sick"]:
                current_streak.append(record)
            else:
                if len(current_streak) >= 3:  # Only report 3+ consecutive absences
                    patterns.append({
                        "start_date": current_streak[0].attendance_date.isoformat(),
                        "end_date": current_streak[-1].attendance_date.isoformat(),
                        "count": len(current_streak)
                    })
                current_streak = []
        
        # Check final streak
        if len(current_streak) >= 3:
            patterns.append({
                "start_date": current_streak[0].attendance_date.isoformat(),
                "end_date": current_streak[-1].attendance_date.isoformat(),
                "count": len(current_streak)
            })
        
        return patterns
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None
    
    def _parse_month_to_date_range(self, month: str) -> Tuple[date, date]:
        """
        Convert month string to start/end dates.
        
        Args:
            month: Month string (YYYY-MM)
            
        Returns:
            Tuple: (start_date, end_date)
        """
        try:
            year, month_num = map(int, month.split("-"))
            start_date = date(year, month_num, 1)
            _, last_day = monthrange(year, month_num)
            end_date = date(year, month_num, last_day)
            return start_date, end_date
        except (ValueError, AttributeError):
            return None, None


# Singleton instance
attendance_service = AttendanceService()
