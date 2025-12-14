"""
Unit tests for Risk service.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime

from src.services.risk_service import RiskService


class TestRiskService:
    """Unit tests for RiskService class."""
    
    @pytest.fixture
    def risk_service(self):
        """Create a RiskService instance with mocked repository."""
        service = RiskService()
        return service
    
    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository."""
        return Mock()
    
    # --- get_at_risk_students tests ---
    
    def test_get_at_risk_students_returns_paginated_list(self, risk_service, mock_repository):
        """Test that get_at_risk_students returns paginated results."""
        mock_students = [
            {
                "student_nis": "2024001",
                "student_name": "John Doe",
                "class_id": "X-IPA-1",
                "risk_level": "high",
                "risk_score": 85,
                "factors": {"attendance_rate": 78.5},
                "last_updated": "2024-01-15T10:30:00",
                "alert_generated": True
            }
        ]
        
        with patch.object(risk_service, 'repository') as mock_repo:
            mock_repo.get_at_risk_students.return_value = (mock_students, 1)
            
            students, pagination = risk_service.get_at_risk_students(
                level="high",
                page=1,
                per_page=20
            )
            
            assert len(students) == 1
            assert students[0]["student_nis"] == "2024001"
            assert pagination["total"] == 1
            assert pagination["page"] == 1
    
    def test_get_at_risk_students_filters_by_level(self, risk_service):
        """Test that filtering by level works correctly."""
        with patch.object(risk_service, 'repository') as mock_repo:
            mock_repo.get_at_risk_students.return_value = ([], 0)
            
            risk_service.get_at_risk_students(level="high")
            
            mock_repo.get_at_risk_students.assert_called_once()
            call_args = mock_repo.get_at_risk_students.call_args
            assert call_args.kwargs['level'] == "high"
    
    def test_get_at_risk_students_filters_by_class(self, risk_service):
        """Test that filtering by class works correctly."""
        with patch.object(risk_service, 'repository') as mock_repo:
            mock_repo.get_at_risk_students.return_value = ([], 0)
            
            risk_service.get_at_risk_students(class_id="X-IPA-1")
            
            mock_repo.get_at_risk_students.assert_called_once()
            call_args = mock_repo.get_at_risk_students.call_args
            assert call_args.kwargs['class_id'] == "X-IPA-1"
    
    # --- get_student_risk tests ---
    
    def test_get_student_risk_returns_error_for_nonexistent(self, risk_service):
        """Test that get_student_risk returns error for nonexistent student."""
        with patch('src.services.risk_service.student_repository') as mock_student_repo:
            mock_student_repo.get_by_nis.return_value = None
            
            result, error = risk_service.get_student_risk("NONEXISTENT")
            
            assert result is None
            assert error == "Student not found"
    
    def test_get_student_risk_returns_factors(self, risk_service):
        """Test that get_student_risk returns risk factors."""
        mock_student = Mock()
        mock_student.name = "John Doe"
        mock_student.class_id = "X-IPA-1"
        mock_student.nis = "2024001"
        mock_student.student_class = Mock()
        mock_student.student_class.class_name = "X IPA 1"
        
        with patch('src.services.risk_service.student_repository') as mock_student_repo:
            mock_student_repo.get_by_nis.return_value = mock_student
            
            with patch.object(risk_service, 'repository') as mock_repo:
                mock_repo.get_student_risk.return_value = {
                    "student_nis": "2024001",
                    "student_name": "John Doe",
                    "class_id": "X-IPA-1",
                    "risk_level": "high",
                    "risk_score": 85,
                    "factors": {"attendance_rate": 78.5}
                }
                
                result, error = risk_service.get_student_risk("2024001")
                
                assert error is None
                assert result["risk_level"] == "high"
                assert "factors" in result
    
    # --- get_alerts tests ---
    
    def test_get_alerts_filters_by_status(self, risk_service):
        """Test that get_alerts filters by status."""
        with patch.object(risk_service, 'repository') as mock_repo:
            mock_repo.get_alerts.return_value = ([], 0)
            
            risk_service.get_alerts(status="pending")
            
            mock_repo.get_alerts.assert_called_once()
            call_args = mock_repo.get_alerts.call_args
            assert call_args.kwargs['status'] == "pending"
    
    def test_get_alerts_returns_paginated_results(self, risk_service):
        """Test that get_alerts returns paginated results."""
        mock_alerts = [
            {
                "id": 1,
                "student_nis": "2024001",
                "alert_type": "high_risk",
                "status": "pending",
                "message": "High risk detected"
            }
        ]
        
        with patch.object(risk_service, 'repository') as mock_repo:
            mock_repo.get_alerts.return_value = (mock_alerts, 1)
            
            alerts, pagination = risk_service.get_alerts(page=1, per_page=20)
            
            assert len(alerts) == 1
            assert pagination["total"] == 1
    
    # --- take_alert_action tests ---
    
    def test_take_alert_action_returns_error_for_nonexistent(self, risk_service):
        """Test that take_alert_action returns error for nonexistent alert."""
        with patch.object(risk_service, 'repository') as mock_repo:
            mock_repo.get_alert_by_id.return_value = None
            
            success, error = risk_service.take_alert_action(
                alert_id=999,
                action="contacted_parent"
            )
            
            assert success is False
            assert error == "Alert not found"
    
    def test_take_alert_action_updates_status(self, risk_service):
        """Test that take_alert_action updates alert status."""
        mock_alert = Mock()
        mock_alert.id = 1
        
        with patch.object(risk_service, 'repository') as mock_repo:
            mock_repo.get_alert_by_id.return_value = mock_alert
            mock_repo.update_alert_action.return_value = True
            
            success, error = risk_service.take_alert_action(
                alert_id=1,
                action="contacted_parent",
                notes="Called parent",
                status="resolved"
            )
            
            assert success is True
            assert error is None
            mock_repo.update_alert_action.assert_called_once()
    
    # --- get_risk_history tests ---
    
    def test_get_risk_history_returns_error_for_nonexistent(self, risk_service):
        """Test that get_risk_history returns error for nonexistent student."""
        with patch('src.services.risk_service.student_repository') as mock_student_repo:
            mock_student_repo.get_by_nis.return_value = None
            
            result, error = risk_service.get_risk_history("NONEXISTENT")
            
            assert result is None
            assert error == "Student not found"
    
    def test_get_risk_history_returns_timeline(self, risk_service):
        """Test that get_risk_history returns risk timeline."""
        mock_student = Mock()
        mock_student.name = "John Doe"
        mock_student.class_id = "X-IPA-1"
        
        mock_history = [
            {
                "id": 1,
                "risk_level": "high",
                "risk_score": 85,
                "calculated_at": "2024-01-15T10:30:00"
            },
            {
                "id": 2,
                "risk_level": "medium",
                "risk_score": 50,
                "calculated_at": "2024-01-10T10:30:00"
            }
        ]
        
        with patch('src.services.risk_service.student_repository') as mock_student_repo:
            mock_student_repo.get_by_nis.return_value = mock_student
            
            with patch.object(risk_service, 'repository') as mock_repo:
                mock_repo.get_risk_history.return_value = mock_history
                
                result, error = risk_service.get_risk_history("2024001")
                
                assert error is None
                assert result["student_nis"] == "2024001"
                assert len(result["history"]) == 2
    
    # --- recalculate_risks tests ---
    
    def test_recalculate_processes_all_students(self, risk_service):
        """Test that recalculate processes all active students."""
        with patch.object(risk_service, 'repository') as mock_repo:
            mock_repo.get_all_active_students.return_value = ["2024001", "2024002"]
            mock_repo.save_risk_history.return_value = Mock()
            mock_repo.get_alerts.return_value = ([], 0)
            mock_repo.create_alert.return_value = Mock()
            
            with patch('src.services.risk_service.assess_risk') as mock_assess:
                mock_assess.return_value = {"risk": "Green", "rationale": "Low risk"}
                
                results = risk_service.recalculate_risks()
                
                assert results["processed"] == 2
                assert results["low_risk"] == 2
    
    # --- helper method tests ---
    
    def test_map_risk_color_to_level_red(self, risk_service):
        """Test that Red maps to high."""
        result = risk_service._map_risk_color_to_level("Red")
        assert result == "high"
    
    def test_map_risk_color_to_level_yellow(self, risk_service):
        """Test that Yellow maps to medium."""
        result = risk_service._map_risk_color_to_level("Yellow")
        assert result == "medium"
    
    def test_map_risk_color_to_level_green(self, risk_service):
        """Test that Green maps to low."""
        result = risk_service._map_risk_color_to_level("Green")
        assert result == "low"
    
    def test_estimate_risk_score_red(self, risk_service):
        """Test that Red returns high score."""
        result = risk_service._estimate_risk_score("Red")
        assert result == 85
    
    def test_estimate_risk_score_green(self, risk_service):
        """Test that Green returns low score."""
        result = risk_service._estimate_risk_score("Green")
        assert result == 15
