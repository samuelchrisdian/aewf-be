"""
Unit tests for AttendanceService.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import date, datetime


class TestAttendanceService:
    """Test cases for AttendanceService class."""
    
    @patch('src.services.attendance_service.attendance_repository')
    def test_get_daily_attendance_returns_paginated_data(self, mock_repo):
        """Test that get_daily_attendance returns properly paginated data."""
        from src.services.attendance_service import AttendanceService
        
        # Setup mock
        mock_record = Mock()
        mock_record.id = 1
        mock_record.student_nis = "2024001"
        mock_record.attendance_date = date(2024, 1, 15)
        mock_record.check_in = datetime(2024, 1, 15, 7, 30)
        mock_record.check_out = datetime(2024, 1, 15, 14, 0)
        mock_record.status = "Present"
        mock_record.notes = None
        mock_record.recorded_by = None
        mock_record.recorder = None
        mock_record.student = Mock()
        mock_record.student.name = "John Doe"
        mock_record.student.class_id = "X-IPA-1"
        mock_record.student.student_class = Mock()
        mock_record.student.student_class.class_name = "X IPA 1"
        
        mock_query = Mock()
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [mock_record]
        mock_repo.get_daily.return_value = mock_query
        
        # Execute
        service = AttendanceService()
        service.repository = mock_repo
        result = service.get_daily_attendance(page=1, per_page=20)
        
        # Assert
        assert "data" in result
        assert "pagination" in result
        assert len(result["data"]) == 1
        assert result["data"][0]["student_nis"] == "2024001"
        assert result["data"][0]["status"] == "Present"
    
    @patch('src.services.attendance_service.attendance_repository')
    @patch('src.services.attendance_service.student_repository')
    def test_get_student_attendance_returns_history_with_patterns(
        self, mock_student_repo, mock_attendance_repo
    ):
        """Test that get_student_attendance returns history with pattern analysis."""
        from src.services.attendance_service import AttendanceService
        
        # Setup mocks
        mock_student = Mock()
        mock_student.nis = "2024001"
        mock_student.name = "John Doe"
        mock_student.class_id = "X-IPA-1"
        mock_student.student_class = Mock()
        mock_student.student_class.class_name = "X IPA 1"
        mock_student_repo.get_by_nis.return_value = mock_student
        
        mock_record = Mock()
        mock_record.id = 1
        mock_record.attendance_date = date(2024, 1, 15)
        mock_record.check_in = datetime(2024, 1, 15, 7, 30)
        mock_record.check_out = None
        mock_record.status = "Present"
        mock_record.notes = None
        
        mock_attendance_repo.get_by_student.return_value = [mock_record]
        mock_attendance_repo.count_by_status.return_value = {
            "present": 15,
            "late": 2,
            "absent": 3,
            "sick": 0,
            "permission": 0,
            "total": 20
        }
        
        # Execute
        service = AttendanceService()
        service.repository = mock_attendance_repo
        result, error = service.get_student_attendance("2024001")
        
        # Assert
        assert error is None
        assert "student" in result
        assert "records" in result
        assert "summary" in result
        assert "patterns" in result
        assert result["student"]["nis"] == "2024001"
    
    @patch('src.services.attendance_service.attendance_repository')
    @patch('src.services.attendance_service.student_repository')
    def test_get_student_attendance_returns_error_when_not_found(
        self, mock_student_repo, mock_attendance_repo
    ):
        """Test that get_student_attendance returns error when student not found."""
        from src.services.attendance_service import AttendanceService
        
        mock_student_repo.get_by_nis.return_value = None
        
        service = AttendanceService()
        result, error = service.get_student_attendance("9999999")
        
        assert result is None
        assert error == "Student not found"
    
    @patch('src.services.attendance_service.attendance_repository')
    @patch('src.services.attendance_service.student_repository')
    @patch('src.services.attendance_service.teacher_repository')
    def test_create_manual_attendance_validates_required_fields(
        self, mock_teacher_repo, mock_student_repo, mock_attendance_repo
    ):
        """Test that create_manual_attendance validates required fields."""
        from src.services.attendance_service import AttendanceService
        
        service = AttendanceService()
        
        # Missing required fields
        result, errors = service.create_manual_attendance({})
        
        assert result is None
        assert errors is not None
    
    @patch('src.services.attendance_service.attendance_repository')
    @patch('src.services.attendance_service.student_repository')
    @patch('src.services.attendance_service.teacher_repository')
    def test_create_manual_attendance_checks_student_exists(
        self, mock_teacher_repo, mock_student_repo, mock_attendance_repo
    ):
        """Test that create_manual_attendance checks if student exists."""
        from src.services.attendance_service import AttendanceService
        
        mock_student_repo.exists.return_value = False
        
        service = AttendanceService()
        result, errors = service.create_manual_attendance({
            "student_nis": "9999999",
            "attendance_date": "2024-01-15",
            "status": "Present"
        })
        
        assert result is None
        assert "student_nis" in errors
    
    @patch('src.services.attendance_service.attendance_repository')
    @patch('src.services.attendance_service.student_repository')
    @patch('src.services.attendance_service.teacher_repository')
    def test_create_manual_attendance_checks_duplicate(
        self, mock_teacher_repo, mock_student_repo, mock_attendance_repo
    ):
        """Test that create_manual_attendance checks for duplicate entry."""
        from src.services.attendance_service import AttendanceService
        
        mock_student_repo.exists.return_value = True
        mock_attendance_repo.exists_for_date.return_value = True
        
        service = AttendanceService()
        service.repository = mock_attendance_repo
        
        result, errors = service.create_manual_attendance({
            "student_nis": "2024001",
            "attendance_date": "2024-01-15",
            "status": "Present"
        })
        
        assert result is None
        assert "attendance_date" in errors
    
    @patch('src.services.attendance_service.attendance_repository')
    def test_update_attendance_returns_error_when_not_found(self, mock_repo):
        """Test that update_attendance returns error when record not found."""
        from src.services.attendance_service import AttendanceService
        
        mock_repo.get_by_id.return_value = None
        
        service = AttendanceService()
        service.repository = mock_repo
        
        result, errors = service.update_attendance(999, {"status": "Late"})
        
        assert result is None
        assert "id" in errors
    
    @patch('src.services.attendance_service.attendance_repository')
    def test_get_attendance_summary_returns_stats(self, mock_repo):
        """Test that get_attendance_summary returns aggregated stats."""
        from src.services.attendance_service import AttendanceService
        
        mock_repo.get_summary_stats.return_value = {
            "total_school_days": 20,
            "average_attendance_rate": 94.5,
            "present_count": 662,
            "late_count": 28,
            "absent_count": 10,
            "sick_count": 5,
            "permission_count": 3
        }
        mock_repo.get_daily_breakdown.return_value = []
        
        service = AttendanceService()
        service.repository = mock_repo
        
        result = service.get_attendance_summary(
            class_id="X-IPA-1",
            period="2024-01"
        )
        
        assert "stats" in result
        assert "daily_breakdown" in result
        assert result["stats"]["total_school_days"] == 20
        assert result["class_id"] == "X-IPA-1"
        assert result["period"] == "2024-01"


class TestConsecutiveAbsenceDetection:
    """Test cases for consecutive absence pattern detection."""
    
    def test_detects_consecutive_absences(self):
        """Test that consecutive absences are detected."""
        from src.services.attendance_service import AttendanceService
        
        # Create mock records with consecutive absences
        records = []
        for i in range(5):
            record = Mock()
            record.attendance_date = date(2024, 1, 10 + i)
            record.status = "Absent" if i < 3 else "Present"
            records.append(record)
        
        service = AttendanceService()
        patterns = service._detect_consecutive_absences(records)
        
        assert len(patterns) == 1
        assert patterns[0]["count"] == 3
    
    def test_ignores_short_absences(self):
        """Test that absences less than 3 days are ignored."""
        from src.services.attendance_service import AttendanceService
        
        records = []
        for i in range(4):
            record = Mock()
            record.attendance_date = date(2024, 1, 10 + i)
            record.status = "Absent" if i < 2 else "Present"
            records.append(record)
        
        service = AttendanceService()
        patterns = service._detect_consecutive_absences(records)
        
        assert len(patterns) == 0
    
    def test_handles_empty_records(self):
        """Test that empty records return empty patterns."""
        from src.services.attendance_service import AttendanceService
        
        service = AttendanceService()
        patterns = service._detect_consecutive_absences([])
        
        assert patterns == []
