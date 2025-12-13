"""
Unit tests for TeacherService.
"""
import pytest
from unittest.mock import Mock, patch


class TestTeacherService:
    """Test cases for TeacherService class."""
    
    @patch('src.services.teacher_service.teacher_repository')
    def test_get_teachers_returns_list(self, mock_teacher_repo):
        """Test that get_teachers returns list of teachers."""
        from src.services.teacher_service import TeacherService
        
        # Setup mock
        mock_teacher = Mock()
        mock_teacher.teacher_id = "T001"
        mock_teacher.name = "Mrs. Sarah"
        mock_teacher.role = "Wali Kelas"
        
        mock_query = Mock()
        mock_query.all.return_value = [mock_teacher]
        mock_teacher_repo.get_all.return_value = mock_query
        
        # Execute
        service = TeacherService()
        service.repository = mock_teacher_repo
        result = service.get_teachers()
        
        # Assert
        assert len(result) == 1
        assert result[0]["teacher_id"] == "T001"
        assert result[0]["name"] == "Mrs. Sarah"
    
    @patch('src.services.teacher_service.teacher_repository')
    def test_get_teachers_applies_role_filter(self, mock_teacher_repo):
        """Test that get_teachers applies role filter."""
        from src.services.teacher_service import TeacherService
        
        mock_query = Mock()
        mock_query.all.return_value = []
        mock_teacher_repo.get_all.return_value = mock_query
        
        service = TeacherService()
        service.repository = mock_teacher_repo
        service.get_teachers(role_filter="Wali Kelas")
        
        mock_teacher_repo.get_all.assert_called_once_with(role_filter="Wali Kelas")
    
    @patch('src.services.teacher_service.teacher_repository')
    def test_get_teacher_returns_detailed_data(self, mock_teacher_repo):
        """Test that get_teacher returns teacher with classes."""
        from src.services.teacher_service import TeacherService
        
        # Setup mock
        mock_teacher = Mock()
        mock_teacher.teacher_id = "T001"
        mock_teacher.name = "Mrs. Sarah"
        mock_teacher.role = "Wali Kelas"
        
        mock_teacher_repo.get_by_id.return_value = mock_teacher
        mock_teacher_repo.get_classes_with_student_count.return_value = [
            {"class_id": "X-IPA-1", "class_name": "X IPA 1", "student_count": 35}
        ]
        
        # Execute
        service = TeacherService()
        service.repository = mock_teacher_repo
        result, error = service.get_teacher("T001")
        
        # Assert
        assert error is None
        assert result["teacher_id"] == "T001"
        assert len(result["classes"]) == 1
        assert result["classes"][0]["class_id"] == "X-IPA-1"
    
    @patch('src.services.teacher_service.teacher_repository')
    def test_get_teacher_returns_error_when_not_found(self, mock_teacher_repo):
        """Test that get_teacher returns error when teacher not found."""
        from src.services.teacher_service import TeacherService
        
        mock_teacher_repo.get_by_id.return_value = None
        
        service = TeacherService()
        service.repository = mock_teacher_repo
        result, error = service.get_teacher("T999")
        
        assert result is None
        assert error == "Teacher not found"
    
    @patch('src.services.teacher_service.teacher_repository')
    def test_create_teacher_validates_required_fields(self, mock_teacher_repo):
        """Test that create_teacher validates required fields."""
        from src.services.teacher_service import TeacherService
        
        service = TeacherService()
        
        # Missing required field
        result, errors = service.create_teacher({"name": "Test Teacher"})
        
        assert result is None
        assert errors is not None
        assert "teacher_id" in errors
    
    @patch('src.services.teacher_service.teacher_repository')
    def test_create_teacher_checks_teacher_id_uniqueness(self, mock_teacher_repo):
        """Test that create_teacher checks for duplicate teacher_id."""
        from src.services.teacher_service import TeacherService
        
        mock_teacher_repo.exists.return_value = True
        
        service = TeacherService()
        service.repository = mock_teacher_repo
        
        result, errors = service.create_teacher({
            "teacher_id": "T001",
            "name": "Mrs. Sarah"
        })
        
        assert result is None
        assert "teacher_id" in errors
    
    @patch('src.services.teacher_service.teacher_repository')
    def test_delete_teacher_fails_when_is_wali_kelas(self, mock_teacher_repo):
        """Test that delete_teacher fails when teacher is wali kelas."""
        from src.services.teacher_service import TeacherService
        
        mock_teacher_repo.exists.return_value = True
        mock_teacher_repo.is_wali_kelas.return_value = True
        
        service = TeacherService()
        service.repository = mock_teacher_repo
        
        success, error = service.delete_teacher("T001")
        
        assert success is False
        assert "wali kelas" in error.lower()
    
    @patch('src.services.teacher_service.teacher_repository')
    def test_delete_teacher_succeeds_when_not_wali_kelas(self, mock_teacher_repo):
        """Test that delete_teacher succeeds when teacher is not wali kelas."""
        from src.services.teacher_service import TeacherService
        
        mock_teacher_repo.exists.return_value = True
        mock_teacher_repo.is_wali_kelas.return_value = False
        mock_teacher_repo.delete.return_value = True
        
        service = TeacherService()
        service.repository = mock_teacher_repo
        
        success, error = service.delete_teacher("T001")
        
        assert success is True
        assert error is None
