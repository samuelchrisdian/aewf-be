"""
Unit tests for Risk service.
Tests for MLService integration and hybrid prediction logic.
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

    @pytest.fixture
    def mock_ml_result_high(self):
        """Mock ML prediction result for high risk."""
        return {
            "nis": "2024001",
            "risk_tier": "RED",
            "risk_probability": 0.85,
            "is_rule_overridden": True,
            "prediction_method": "rule",
            "rule_reason": "absent_ratio (18%) > 15%",
            "factors": {
                "absent_ratio": 0.18,
                "absent_count": 6,
                "late_ratio": 0.05,
                "late_count": 2,
                "trend_score": -0.15,
                "total_days": 30,
                "attendance_ratio": 0.75,
            },
            "response_time_ms": 12.5,
        }

    @pytest.fixture
    def mock_ml_result_low(self):
        """Mock ML prediction result for low risk."""
        return {
            "nis": "2024002",
            "risk_tier": "GREEN",
            "risk_probability": 0.15,
            "is_rule_overridden": False,
            "prediction_method": "ml",
            "factors": {
                "absent_ratio": 0.02,
                "absent_count": 1,
                "late_ratio": 0.03,
                "late_count": 1,
                "trend_score": 0.05,
                "total_days": 30,
                "attendance_ratio": 0.95,
            },
            "response_time_ms": 10.2,
        }

    # --- get_at_risk_students tests ---

    def test_get_at_risk_students_returns_paginated_list(
        self, risk_service, mock_repository
    ):
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
                "alert_generated": True,
            }
        ]

        with patch.object(risk_service, "repository") as mock_repo:
            mock_repo.get_at_risk_students.return_value = (mock_students, 1)

            students, pagination = risk_service.get_at_risk_students(
                level="high", page=1, per_page=20
            )

            assert len(students) == 1
            assert students[0]["student_nis"] == "2024001"
            assert pagination["total"] == 1
            assert pagination["page"] == 1

    def test_get_at_risk_students_filters_by_level(self, risk_service):
        """Test that filtering by level works correctly."""
        with patch.object(risk_service, "repository") as mock_repo:
            mock_repo.get_at_risk_students.return_value = ([], 0)

            risk_service.get_at_risk_students(level="high")

            mock_repo.get_at_risk_students.assert_called_once()
            call_args = mock_repo.get_at_risk_students.call_args
            assert call_args.kwargs["level"] == "high"

    def test_get_at_risk_students_filters_by_class(self, risk_service):
        """Test that filtering by class works correctly."""
        with patch.object(risk_service, "repository") as mock_repo:
            mock_repo.get_at_risk_students.return_value = ([], 0)

            risk_service.get_at_risk_students(class_id="X-IPA-1")

            mock_repo.get_at_risk_students.assert_called_once()
            call_args = mock_repo.get_at_risk_students.call_args
            assert call_args.kwargs["class_id"] == "X-IPA-1"

    # --- get_student_risk tests ---

    def test_get_student_risk_returns_error_for_nonexistent(self, risk_service):
        """Test that get_student_risk returns error for nonexistent student."""
        with patch("src.services.risk_service.student_repository") as mock_student_repo:
            mock_student_repo.get_by_nis.return_value = None

            result, error = risk_service.get_student_risk("NONEXISTENT")

            assert result is None
            assert error == "Student not found"

    def test_get_student_risk_returns_ml_prediction(
        self, risk_service, mock_ml_result_high
    ):
        """Test that get_student_risk returns ML prediction with detailed factors."""
        mock_student = Mock()
        mock_student.name = "John Doe"
        mock_student.class_id = "X-IPA-1"
        mock_student.nis = "2024001"
        mock_student.student_class = Mock()
        mock_student.student_class.class_name = "X IPA 1"

        with patch("src.services.risk_service.student_repository") as mock_student_repo:
            mock_student_repo.get_by_nis.return_value = mock_student

            with patch.object(risk_service, "repository") as mock_repo:
                mock_repo.get_student_risk.return_value = None

                with patch("src.services.risk_service.MLService") as mock_ml:
                    mock_ml.predict_risk.return_value = mock_ml_result_high

                    result, error = risk_service.get_student_risk("2024001")

                    assert error is None
                    assert result["risk_level"] == "high"
                    assert result["risk_probability"] == 0.85
                    assert "factors" in result
                    assert result["factors"]["absent_ratio"] == 0.18
                    assert result["prediction_method"] == "rule"
                    assert result["is_rule_triggered"] is True
                    assert "recommendations" in result

    def test_get_student_risk_includes_recommendations(
        self, risk_service, mock_ml_result_high
    ):
        """Test that get_student_risk includes tier-specific recommendations."""
        mock_student = Mock()
        mock_student.name = "John Doe"
        mock_student.class_id = "X-IPA-1"
        mock_student.student_class = Mock()
        mock_student.student_class.class_name = "X IPA 1"

        with patch("src.services.risk_service.student_repository") as mock_student_repo:
            mock_student_repo.get_by_nis.return_value = mock_student

            with patch.object(risk_service, "repository") as mock_repo:
                mock_repo.get_student_risk.return_value = None

                with patch("src.services.risk_service.MLService") as mock_ml:
                    mock_ml.predict_risk.return_value = mock_ml_result_high

                    with patch(
                        "src.services.risk_service.get_tier_recommendations"
                    ) as mock_recs:
                        mock_recs.return_value = ["Contact parent/guardian immediately"]

                        result, error = risk_service.get_student_risk("2024001")

                        assert error is None
                        assert "recommendations" in result
                        mock_recs.assert_called_once_with("RED")

    # --- get_alerts tests ---

    def test_get_alerts_filters_by_status(self, risk_service):
        """Test that get_alerts filters by status."""
        with patch.object(risk_service, "repository") as mock_repo:
            mock_repo.get_alerts.return_value = ([], 0)

            risk_service.get_alerts(status="pending")

            mock_repo.get_alerts.assert_called_once()
            call_args = mock_repo.get_alerts.call_args
            assert call_args.kwargs["status"] == "pending"

    def test_get_alerts_returns_paginated_results(self, risk_service):
        """Test that get_alerts returns paginated results."""
        mock_alerts = [
            {
                "id": 1,
                "student_nis": "2024001",
                "alert_type": "high_risk",
                "status": "pending",
                "message": "High risk detected",
            }
        ]

        with patch.object(risk_service, "repository") as mock_repo:
            mock_repo.get_alerts.return_value = (mock_alerts, 1)

            alerts, pagination = risk_service.get_alerts(page=1, per_page=20)

            assert len(alerts) == 1
            assert pagination["total"] == 1

    # --- take_alert_action tests ---

    def test_take_alert_action_returns_error_for_nonexistent(self, risk_service):
        """Test that take_alert_action returns error for nonexistent alert."""
        with patch.object(risk_service, "repository") as mock_repo:
            mock_repo.get_alert_by_id.return_value = None

            success, error = risk_service.take_alert_action(
                alert_id=999, action="contacted_parent"
            )

            assert success is False
            assert error == "Alert not found"

    def test_take_alert_action_updates_status(self, risk_service):
        """Test that take_alert_action updates alert status."""
        mock_alert = Mock()
        mock_alert.id = 1

        with patch.object(risk_service, "repository") as mock_repo:
            mock_repo.get_alert_by_id.return_value = mock_alert
            mock_repo.update_alert_action.return_value = True

            success, error = risk_service.take_alert_action(
                alert_id=1,
                action="contacted_parent",
                notes="Called parent",
                status="resolved",
            )

            assert success is True
            assert error is None
            mock_repo.update_alert_action.assert_called_once()

    # --- get_risk_history tests ---

    def test_get_risk_history_returns_error_for_nonexistent(self, risk_service):
        """Test that get_risk_history returns error for nonexistent student."""
        with patch("src.services.risk_service.student_repository") as mock_student_repo:
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
                "calculated_at": "2024-01-15T10:30:00",
            },
            {
                "id": 2,
                "risk_level": "medium",
                "risk_score": 50,
                "calculated_at": "2024-01-10T10:30:00",
            },
        ]

        with patch("src.services.risk_service.student_repository") as mock_student_repo:
            mock_student_repo.get_by_nis.return_value = mock_student

            with patch.object(risk_service, "repository") as mock_repo:
                mock_repo.get_risk_history.return_value = mock_history

                result, error = risk_service.get_risk_history("2024001")

                assert error is None
                assert result["student_nis"] == "2024001"
                assert len(result["history"]) == 2

    # --- recalculate_risks tests ---

    def test_recalculate_uses_ml_service(self, risk_service, mock_ml_result_low):
        """Test that recalculate uses MLService.predict_risk."""
        with patch.object(risk_service, "repository") as mock_repo:
            mock_repo.get_all_active_students.return_value = ["2024001", "2024002"]
            mock_repo.save_risk_history.return_value = Mock()
            mock_repo.get_alerts.return_value = ([], 0)
            mock_repo.create_alert.return_value = Mock()

            with patch("src.services.risk_service.MLService") as mock_ml:
                mock_ml.predict_risk.return_value = mock_ml_result_low

                results = risk_service.recalculate_risks()

                assert results["processed"] == 2
                assert results["low_risk"] == 2
                assert mock_ml.predict_risk.call_count == 2

    def test_recalculate_tracks_prediction_methods(
        self, risk_service, mock_ml_result_high
    ):
        """Test that recalculate tracks prediction methods used."""
        with patch.object(risk_service, "repository") as mock_repo:
            mock_repo.get_all_active_students.return_value = ["2024001"]
            mock_repo.save_risk_history.return_value = Mock()
            mock_repo.get_alerts.return_value = ([], 0)
            mock_repo.create_alert.return_value = Mock()

            with patch("src.services.risk_service.MLService") as mock_ml:
                mock_ml.predict_risk.return_value = mock_ml_result_high

                results = risk_service.recalculate_risks()

                assert "prediction_methods" in results
                assert results["prediction_methods"]["rule"] == 1

    def test_recalculate_generates_alerts_for_high_risk(
        self, risk_service, mock_ml_result_high
    ):
        """Test that recalculate generates alerts for high-risk students."""
        with patch.object(risk_service, "repository") as mock_repo:
            mock_repo.get_all_active_students.return_value = ["2024001"]
            mock_repo.save_risk_history.return_value = Mock()
            mock_repo.get_alerts.return_value = ([], 0)
            mock_repo.create_alert.return_value = Mock()

            with patch("src.services.risk_service.MLService") as mock_ml:
                mock_ml.predict_risk.return_value = mock_ml_result_high

                results = risk_service.recalculate_risks()

                assert results["high_risk"] == 1
                assert results["alerts_generated"] == 1
                mock_repo.create_alert.assert_called_once()

    # --- helper method tests ---

    def test_map_risk_tier_to_level_red(self, risk_service):
        """Test that RED maps to high."""
        result = risk_service._map_risk_tier_to_level("RED")
        assert result == "high"

    def test_map_risk_tier_to_level_yellow(self, risk_service):
        """Test that YELLOW maps to medium."""
        result = risk_service._map_risk_tier_to_level("YELLOW")
        assert result == "medium"

    def test_map_risk_tier_to_level_green(self, risk_service):
        """Test that GREEN maps to low."""
        result = risk_service._map_risk_tier_to_level("GREEN")
        assert result == "low"

    # Legacy compatibility tests
    def test_map_risk_color_to_level_red(self, risk_service):
        """Test that Red maps to high (legacy)."""
        result = risk_service._map_risk_color_to_level("Red")
        assert result == "high"

    def test_map_risk_color_to_level_yellow(self, risk_service):
        """Test that Yellow maps to medium (legacy)."""
        result = risk_service._map_risk_color_to_level("Yellow")
        assert result == "medium"

    def test_map_risk_color_to_level_green(self, risk_service):
        """Test that Green maps to low (legacy)."""
        result = risk_service._map_risk_color_to_level("Green")
        assert result == "low"

    def test_estimate_risk_score_red(self, risk_service):
        """Test that Red returns high score (legacy)."""
        result = risk_service._estimate_risk_score("Red")
        assert result == 85

    def test_estimate_risk_score_green(self, risk_service):
        """Test that Green returns low score (legacy)."""
        result = risk_service._estimate_risk_score("Green")
        assert result == 15

    def test_calculate_risk_score_from_probability(self, risk_service):
        """Test that calculate_risk_score uses probability for ML predictions."""
        ml_result = {
            "risk_tier": "YELLOW",
            "risk_probability": 0.55,
            "is_rule_overridden": False,
        }

        score = risk_service._calculate_risk_score(ml_result)

        assert score == 55  # probability * 100

    def test_calculate_risk_score_for_rule_triggered(self, risk_service):
        """Test that calculate_risk_score uses tier score for rule-triggered predictions."""
        ml_result = {
            "risk_tier": "RED",
            "risk_probability": 1.0,
            "is_rule_overridden": True,
        }

        score = risk_service._calculate_risk_score(ml_result)

        assert score == 85  # Fixed score for RED tier
