"""
Unit tests for DashboardService.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import date


class TestDashboardService:
    """Test cases for DashboardService class."""
    
    @patch('src.services.dashboard_service.dashboard_repository')
    def test_get_dashboard_stats_returns_all_sections(self, mock_repo):
        """Test that get_dashboard_stats returns all required sections."""
        from src.services.dashboard_service import DashboardService
        
        # Setup mocks
        mock_repo.get_entity_counts.return_value = {
            "total_students": 450,
            "active_students": 445,
            "total_classes": 15,
            "total_teachers": 45
        }
        mock_repo.get_today_attendance.return_value = {
            "date": "2024-01-15",
            "present": 400,
            "late": 25,
            "absent": 10,
            "sick": 5,
            "permission": 5,
            "rate": 95.5
        }
        mock_repo.get_month_attendance.return_value = {
            "average_rate": 93.5,
            "trend": "+1.2%",
            "total_lates": 125,
            "total_absents": 89
        }
        mock_repo.get_risk_summary.return_value = {
            "high_risk": 12,
            "medium_risk": 28,
            "low_risk": 405
        }
        
        # Execute
        service = DashboardService()
        service.repository = mock_repo
        result = service.get_dashboard_stats()
        
        # Assert all sections present
        assert "overview" in result
        assert "today_attendance" in result
        assert "this_month" in result
        assert "risk_summary" in result
    
    @patch('src.services.dashboard_service.dashboard_repository')
    def test_get_dashboard_stats_overview_fields(self, mock_repo):
        """Test that overview section has correct fields."""
        from src.services.dashboard_service import DashboardService
        
        mock_repo.get_entity_counts.return_value = {
            "total_students": 450,
            "active_students": 445,
            "total_classes": 15,
            "total_teachers": 45
        }
        mock_repo.get_today_attendance.return_value = {}
        mock_repo.get_month_attendance.return_value = {}
        mock_repo.get_risk_summary.return_value = {}
        
        service = DashboardService()
        service.repository = mock_repo
        result = service.get_dashboard_stats()
        
        overview = result["overview"]
        assert overview["total_students"] == 450
        assert overview["active_students"] == 445
        assert overview["total_classes"] == 15
        assert overview["total_teachers"] == 45
    
    @patch('src.services.dashboard_service.dashboard_repository')
    def test_get_dashboard_stats_today_attendance_fields(self, mock_repo):
        """Test that today_attendance section has correct fields."""
        from src.services.dashboard_service import DashboardService
        
        mock_repo.get_entity_counts.return_value = {}
        mock_repo.get_today_attendance.return_value = {
            "date": "2024-01-15",
            "present": 400,
            "late": 25,
            "absent": 10,
            "rate": 95.5
        }
        mock_repo.get_month_attendance.return_value = {}
        mock_repo.get_risk_summary.return_value = {}
        
        service = DashboardService()
        service.repository = mock_repo
        result = service.get_dashboard_stats()
        
        today = result["today_attendance"]
        assert "date" in today
        assert "present" in today
        assert "late" in today
        assert "absent" in today
        assert "rate" in today
    
    @patch('src.services.dashboard_service.dashboard_repository')
    def test_get_dashboard_stats_this_month_fields(self, mock_repo):
        """Test that this_month section has correct fields."""
        from src.services.dashboard_service import DashboardService
        
        mock_repo.get_entity_counts.return_value = {}
        mock_repo.get_today_attendance.return_value = {}
        mock_repo.get_month_attendance.return_value = {
            "average_rate": 93.5,
            "trend": "+1.2%",
            "total_lates": 125,
            "total_absents": 89
        }
        mock_repo.get_risk_summary.return_value = {}
        
        service = DashboardService()
        service.repository = mock_repo
        result = service.get_dashboard_stats()
        
        month = result["this_month"]
        assert month["average_rate"] == 93.5
        assert month["trend"] == "+1.2%"
        assert month["total_lates"] == 125
        assert month["total_absents"] == 89
    
    @patch('src.services.dashboard_service.dashboard_repository')
    def test_get_dashboard_stats_risk_summary_fields(self, mock_repo):
        """Test that risk_summary section has correct fields."""
        from src.services.dashboard_service import DashboardService
        
        mock_repo.get_entity_counts.return_value = {}
        mock_repo.get_today_attendance.return_value = {}
        mock_repo.get_month_attendance.return_value = {}
        mock_repo.get_risk_summary.return_value = {
            "high_risk": 12,
            "medium_risk": 28,
            "low_risk": 405
        }
        
        service = DashboardService()
        service.repository = mock_repo
        result = service.get_dashboard_stats()
        
        risk = result["risk_summary"]
        assert risk["high_risk"] == 12
        assert risk["medium_risk"] == 28
        assert risk["low_risk"] == 405
