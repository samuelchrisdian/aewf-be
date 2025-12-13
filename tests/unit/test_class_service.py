"""
Unit tests for ClassService.
"""
import pytest
from unittest.mock import Mock, patch


class TestClassService:
    """Test cases for ClassService class."""
    
    @patch('src.services.class_service.class_repository')
    def test_get_classes_returns_list_with_student_count(self, mock_class_repo):
        """Test that get_classes returns classes with student count."""
        from src.services.class_service import ClassService
        
        # Setup mock
        mock_class = Mock()
        mock_class.class_id = "X-IPA-1"
        mock_class.class_name = "X IPA 1"
        mock_class.wali_kelas_id = "T001"
        mock_class.wali_kelas = Mock()
        mock_class.wali_kelas.name = "Mrs. Sarah"
        
        mock_class_repo.get_all_with_student_count.return_value = [
            {"class": mock_class, "student_count": 35}
        ]
        
        # Execute
        service = ClassService()
        service.repository = mock_class_repo
        result = service.get_classes()
        
        # Assert
        assert len(result) == 1
        assert result[0]["class_id"] == "X-IPA-1"
        assert result[0]["student_count"] == 35
        assert result[0]["wali_kelas_name"] == "Mrs. Sarah"
    
    @patch('src.services.class_service.class_repository')
    @patch('src.services.class_service.db')
    def test_get_class_returns_detailed_data(self, mock_db, mock_class_repo):
        """Test that get_class returns class with full details."""
        from src.services.class_service import ClassService
        
        # Setup mock
        mock_class = Mock()
        mock_class.class_id = "X-IPA-1"
        mock_class.class_name = "X IPA 1"
        mock_class.wali_kelas_id = "T001"
        mock_class.wali_kelas = Mock()
        mock_class.wali_kelas.teacher_id = "T001"
        mock_class.wali_kelas.name = "Mrs. Sarah"
        
        mock_class_repo.get_by_id.return_value = mock_class
        mock_class_repo.get_student_count.return_value = 35
        
        # Mock attendance stats query
        mock_db.session.query.return_value.filter.return_value.all.return_value = []
        
        # Execute
        service = ClassService()
        service.repository = mock_class_repo
        result, error = service.get_class("X-IPA-1")
        
        # Assert
        assert error is None
        assert result["class_id"] == "X-IPA-1"
        assert result["student_count"] == 35
        assert result["wali_kelas"]["teacher_id"] == "T001"
    
    @patch('src.services.class_service.class_repository')
    def test_get_class_returns_error_when_not_found(self, mock_class_repo):
        """Test that get_class returns error when class not found."""
        from src.services.class_service import ClassService
        
        mock_class_repo.get_by_id.return_value = None
        
        service = ClassService()
        service.repository = mock_class_repo
        result, error = service.get_class("X-IPA-999")
        
        assert result is None
        assert error == "Class not found"
    
    @patch('src.services.class_service.class_repository')
    @patch('src.services.class_service.teacher_repository')
    def test_create_class_validates_required_fields(self, mock_teacher_repo, mock_class_repo):
        """Test that create_class validates required fields."""
        from src.services.class_service import ClassService
        
        service = ClassService()
        
        # Missing required field
        result, errors = service.create_class({"class_name": "Test Class"})
        
        assert result is None
        assert errors is not None
        assert "class_id" in errors
    
    @patch('src.services.class_service.class_repository')
    @patch('src.services.class_service.teacher_repository')
    def test_create_class_checks_class_id_uniqueness(self, mock_teacher_repo, mock_class_repo):
        """Test that create_class checks for duplicate class_id."""
        from src.services.class_service import ClassService
        
        mock_class_repo.exists.return_value = True
        
        service = ClassService()
        service.repository = mock_class_repo
        
        result, errors = service.create_class({
            "class_id": "X-IPA-1",
            "class_name": "X IPA 1"
        })
        
        assert result is None
        assert "class_id" in errors
    
    @patch('src.services.class_service.class_repository')
    def test_delete_class_fails_with_active_students(self, mock_class_repo):
        """Test that delete_class fails when class has active students."""
        from src.services.class_service import ClassService
        
        mock_class_repo.exists.return_value = True
        mock_class_repo.has_active_students.return_value = True
        
        service = ClassService()
        service.repository = mock_class_repo
        
        success, error = service.delete_class("X-IPA-1")
        
        assert success is False
        assert "active students" in error.lower()
    
    @patch('src.services.class_service.class_repository')
    def test_delete_class_succeeds_without_active_students(self, mock_class_repo):
        """Test that delete_class succeeds when no active students."""
        from src.services.class_service import ClassService
        
        mock_class_repo.exists.return_value = True
        mock_class_repo.has_active_students.return_value = False
        mock_class_repo.delete.return_value = True
        
        service = ClassService()
        service.repository = mock_class_repo
        
        success, error = service.delete_class("X-IPA-1")
        
        assert success is True
        assert error is None
