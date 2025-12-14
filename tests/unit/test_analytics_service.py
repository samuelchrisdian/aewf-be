"""
Unit tests for AnalyticsService.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import date


class TestAnalyticsService:
    """Test cases for AnalyticsService class."""
    
    @patch('src.services.analytics_service.analytics_repository')
    def test_get_trends_weekly(self, mock_repo):
        """Test that get_trends returns weekly data correctly."""
        from src.services.analytics_service import AnalyticsService
        
        mock_repo.get_attendance_trends.return_value = [
            {
                "period": "2024-01-01",
                "period_end": "2024-01-07",
                "period_label": "Week of Jan 01",
                "present": 300,
                "late": 20,
                "absent": 10,
                "attendance_rate": 96.4
            }
        ]
        
        service = AnalyticsService()
        service.repository = mock_repo
        result = service.get_trends(period="weekly")
        
        assert result["period"] == "weekly"
        assert "trends" in result
        assert len(result["trends"]) == 1
        mock_repo.get_attendance_trends.assert_called_once()
    
    @patch('src.services.analytics_service.analytics_repository')
    def test_get_trends_monthly(self, mock_repo):
        """Test that get_trends returns monthly data correctly."""
        from src.services.analytics_service import AnalyticsService
        
        mock_repo.get_attendance_trends.return_value = [
            {
                "period": "2024-01",
                "period_label": "Jan 2024",
                "attendance_rate": 95.0
            }
        ]
        
        service = AnalyticsService()
        service.repository = mock_repo
        result = service.get_trends(period="monthly")
        
        assert result["period"] == "monthly"
        assert "trends" in result
    
    @patch('src.services.analytics_service.analytics_repository')
    def test_get_trends_with_date_range(self, mock_repo):
        """Test that get_trends accepts date range parameters."""
        from src.services.analytics_service import AnalyticsService
        
        mock_repo.get_attendance_trends.return_value = []
        
        service = AnalyticsService()
        service.repository = mock_repo
        result = service.get_trends(
            period="weekly",
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        
        assert result["period"] == "weekly"
        mock_repo.get_attendance_trends.assert_called_once()
    
    @patch('src.services.analytics_service.analytics_repository')
    def test_get_class_comparison_returns_classes(self, mock_repo):
        """Test that get_class_comparison returns class data."""
        from src.services.analytics_service import AnalyticsService
        
        mock_repo.get_class_comparison.return_value = [
            {
                "class_id": "X-IPA-1",
                "class_name": "X IPA 1",
                "attendance_rate": 95.2,
                "average_late": 1.2,
                "at_risk_count": 2
            },
            {
                "class_id": "X-IPA-2",
                "class_name": "X IPA 2",
                "attendance_rate": 93.5,
                "average_late": 1.5,
                "at_risk_count": 3
            }
        ]
        
        service = AnalyticsService()
        service.repository = mock_repo
        result = service.get_class_comparison()
        
        assert "classes" in result
        assert len(result["classes"]) == 2
        assert "total_classes" in result
        assert result["total_classes"] == 2
        assert "average_attendance_rate" in result
    
    @patch('src.services.analytics_service.analytics_repository')
    def test_get_class_comparison_identifies_best_class(self, mock_repo):
        """Test that get_class_comparison identifies best performing class."""
        from src.services.analytics_service import AnalyticsService
        
        mock_repo.get_class_comparison.return_value = [
            {"class_id": "X-IPA-1", "class_name": "X IPA 1", "attendance_rate": 98.0},
            {"class_id": "X-IPA-2", "class_name": "X IPA 2", "attendance_rate": 85.0}
        ]
        
        service = AnalyticsService()
        service.repository = mock_repo
        result = service.get_class_comparison()
        
        assert result["best_performing"]["class_id"] == "X-IPA-1"
        assert result["best_performing"]["attendance_rate"] == 98.0
    
    @patch('src.services.analytics_service.analytics_repository')
    def test_get_class_comparison_identifies_needs_attention(self, mock_repo):
        """Test that get_class_comparison identifies class needing attention."""
        from src.services.analytics_service import AnalyticsService
        
        mock_repo.get_class_comparison.return_value = [
            {"class_id": "X-IPA-1", "class_name": "X IPA 1", "attendance_rate": 98.0},
            {"class_id": "X-IPA-2", "class_name": "X IPA 2", "attendance_rate": 85.0}
        ]
        
        service = AnalyticsService()
        service.repository = mock_repo
        result = service.get_class_comparison()
        
        assert result["needs_attention"]["class_id"] == "X-IPA-2"
        assert result["needs_attention"]["attendance_rate"] == 85.0
    
    @patch('src.services.analytics_service.analytics_repository')
    @patch('src.services.analytics_service.student_repository')
    def test_get_student_patterns_returns_data(self, mock_student_repo, mock_analytics_repo):
        """Test that get_student_patterns returns pattern data."""
        from src.services.analytics_service import AnalyticsService
        
        mock_student = Mock()
        mock_student.nis = "2024001"
        mock_student_repo.get_by_nis.return_value = mock_student
        
        mock_analytics_repo.get_student_patterns.return_value = {
            "student": {"nis": "2024001", "name": "John Doe"},
            "summary": {"attendance_rate": 92.5},
            "trend": {"direction": "stable"},
            "weekly_pattern": [],
            "consecutive_absences": []
        }
        
        service = AnalyticsService()
        service.repository = mock_analytics_repo
        result, error = service.get_student_patterns("2024001")
        
        assert error is None
        assert result is not None
        assert "student" in result
        assert "summary" in result
        assert "trend" in result
    
    @patch('src.services.analytics_service.analytics_repository')
    @patch('src.services.analytics_service.student_repository')
    def test_get_student_patterns_returns_error_for_nonexistent(
        self, mock_student_repo, mock_analytics_repo
    ):
        """Test that get_student_patterns returns error for nonexistent student."""
        from src.services.analytics_service import AnalyticsService
        
        mock_student_repo.get_by_nis.return_value = None
        
        service = AnalyticsService()
        result, error = service.get_student_patterns("9999999")
        
        assert result is None
        assert error == "Student not found"


class TestAnalyticsServiceDateParsing:
    """Test cases for date parsing in AnalyticsService."""
    
    def test_parse_valid_date(self):
        """Test parsing valid date string."""
        from src.services.analytics_service import AnalyticsService
        
        service = AnalyticsService()
        result = service._parse_date("2024-01-15")
        
        assert result == date(2024, 1, 15)
    
    def test_parse_invalid_date(self):
        """Test parsing invalid date string returns None."""
        from src.services.analytics_service import AnalyticsService
        
        service = AnalyticsService()
        result = service._parse_date("invalid-date")
        
        assert result is None
    
    def test_parse_none_date(self):
        """Test parsing None returns None."""
        from src.services.analytics_service import AnalyticsService
        
        service = AnalyticsService()
        result = service._parse_date(None)
        
        assert result is None
