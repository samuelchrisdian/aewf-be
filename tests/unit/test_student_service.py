"""
Unit tests for StudentService.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestStudentService:
    """Test cases for StudentService class."""
    
    @patch('src.services.student_service.student_repository')
    @patch('src.services.student_service.class_repository')
    def test_get_students_returns_paginated_data(self, mock_class_repo, mock_student_repo):
        """Test that get_students returns properly paginated data."""
        from src.services.student_service import StudentService
        
        # Setup mock
        mock_student = Mock()
        mock_student.nis = "2024001"
        mock_student.name = "John Doe"
        mock_student.class_id = "X-IPA-1"
        mock_student.parent_phone = "08123456789"
        mock_student.is_active = True
        mock_student.student_class = Mock()
        mock_student.student_class.class_name = "X IPA 1"
        
        mock_query = Mock()
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [mock_student]
        mock_student_repo.get_all.return_value = mock_query
        
        # Execute
        service = StudentService()
        service.repository = mock_student_repo
        result = service.get_students(page=1, per_page=20)
        
        # Assert
        assert "data" in result
        assert "pagination" in result
        assert len(result["data"]) == 1
        assert result["data"][0]["nis"] == "2024001"
        assert result["pagination"]["total"] == 1
    
    @patch('src.services.student_service.student_repository')
    def test_get_student_returns_data_with_attendance_summary(self, mock_student_repo):
        """Test that get_student returns student with attendance summary."""
        from src.services.student_service import StudentService
        
        # Setup mock
        mock_student = Mock()
        mock_student.nis = "2024001"
        mock_student.name = "John Doe"
        mock_student.class_id = "X-IPA-1"
        mock_student.parent_phone = "08123456789"
        mock_student.is_active = True
        mock_student.student_class = Mock()
        mock_student.student_class.class_name = "X IPA 1"
        
        mock_student_repo.get_by_nis.return_value = mock_student
        mock_student_repo.get_attendance_summary.return_value = {
            "total_days": 100,
            "present": 90,
            "late": 5,
            "absent": 5,
            "sick": 0,
            "permission": 0,
            "attendance_rate": 95.0
        }
        
        # Execute
        service = StudentService()
        service.repository = mock_student_repo
        result, error = service.get_student("2024001")
        
        # Assert
        assert error is None
        assert result["nis"] == "2024001"
        assert "attendance_summary" in result
        assert result["attendance_summary"]["attendance_rate"] == 95.0
    
    @patch('src.services.student_service.student_repository')
    def test_get_student_returns_error_when_not_found(self, mock_student_repo):
        """Test that get_student returns error when student not found."""
        from src.services.student_service import StudentService
        
        mock_student_repo.get_by_nis.return_value = None
        
        service = StudentService()
        service.repository = mock_student_repo
        result, error = service.get_student("9999999")
        
        assert result is None
        assert error == "Student not found"
    
    @patch('src.services.student_service.student_repository')
    @patch('src.services.student_service.class_repository')
    def test_create_student_validates_required_fields(self, mock_class_repo, mock_student_repo):
        """Test that create_student validates required fields."""
        from src.services.student_service import StudentService
        
        service = StudentService()
        
        # Missing required field
        result, errors = service.create_student({"name": "John"})
        
        assert result is None
        assert errors is not None
        assert "nis" in errors or "class_id" in errors
    
    @patch('src.services.student_service.student_repository')
    @patch('src.services.student_service.class_repository')
    def test_create_student_checks_nis_uniqueness(self, mock_class_repo, mock_student_repo):
        """Test that create_student checks for duplicate NIS."""
        from src.services.student_service import StudentService
        
        mock_student_repo.exists.return_value = True
        
        service = StudentService()
        service.repository = mock_student_repo
        
        result, errors = service.create_student({
            "nis": "2024001",
            "name": "John Doe",
            "class_id": "X-IPA-1"
        })
        
        assert result is None
        assert "nis" in errors
    
    @patch('src.services.student_service.student_repository')
    @patch('src.services.student_service.class_repository')
    def test_create_student_checks_class_exists(self, mock_class_repo, mock_student_repo):
        """Test that create_student checks if class exists."""
        from src.services.student_service import StudentService
        
        mock_student_repo.exists.return_value = False
        mock_class_repo.exists.return_value = False
        
        service = StudentService()
        service.repository = mock_student_repo
        
        result, errors = service.create_student({
            "nis": "2024001",
            "name": "John Doe",
            "class_id": "X-IPA-1"
        })
        
        assert result is None
        assert "class_id" in errors
    
    @patch('src.services.student_service.student_repository')
    def test_delete_student_soft_deletes(self, mock_student_repo):
        """Test that delete_student performs soft delete."""
        from src.services.student_service import StudentService
        
        mock_student_repo.exists.return_value = True
        mock_student_repo.soft_delete.return_value = True
        
        service = StudentService()
        service.repository = mock_student_repo
        
        success, error = service.delete_student("2024001")
        
        assert success is True
        assert error is None
        mock_student_repo.soft_delete.assert_called_once_with("2024001")
    
    @patch('src.services.student_service.student_repository')
    def test_delete_student_returns_error_when_not_found(self, mock_student_repo):
        """Test that delete_student returns error when not found."""
        from src.services.student_service import StudentService
        
        mock_student_repo.exists.return_value = False
        
        service = StudentService()
        service.repository = mock_student_repo
        
        success, error = service.delete_student("9999999")
        
        assert success is False
        assert error == "Student not found"
