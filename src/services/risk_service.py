"""
Risk service for business logic.
Handles all business operations for risk management and EWS.
Uses the new MLService for hybrid ML + Rule-based predictions.
"""

from typing import Optional, List, Any
from datetime import date, datetime
import logging

from src.repositories.risk_repo import risk_repository
from src.repositories.student_repo import student_repository
from src.repositories.teacher_repo import teacher_repository
from src.services.ml_service import MLService, get_tier_recommendations

logger = logging.getLogger(__name__)

# Risk tier mapping from MLService (RED/YELLOW/GREEN) to level (high/medium/low)
TIER_TO_LEVEL = {"RED": "high", "YELLOW": "medium", "GREEN": "low"}

# Risk score mapping based on tier
TIER_TO_SCORE = {"RED": 85, "YELLOW": 50, "GREEN": 15}


class RiskService:
    """Service class for Risk Management business logic."""

    def __init__(self):
        self.repository = risk_repository

    def get_at_risk_students(
        self,
        level: Optional[str] = None,
        class_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        current_user: Optional[Any] = None,
    ) -> tuple:
        """
        Get list of at-risk students with role-based filtering.

        Args:
            level: Filter by risk level
            class_id: Filter by class
            page: Page number
            per_page: Items per page
            current_user: Current authenticated user (for role-based filtering)

        Returns:
            tuple: (students list, pagination dict)
        """
        # Role-based filtering
        class_ids = None
        if current_user and current_user.role == "Teacher":
            # Get classes managed by this teacher (wali kelas)
            teacher_classes = teacher_repository.get_classes_by_teacher(
                current_user.username
            )
            if teacher_classes:
                class_ids = [cls.class_id for cls in teacher_classes]
            else:
                # Teacher has no classes, return empty result
                class_ids = []

        students, total = self.repository.get_at_risk_students(
            level=level,
            class_id=class_id,
            class_ids=class_ids,
            page=page,
            per_page=per_page,
        )

        import math

        pagination = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": math.ceil(total / per_page) if per_page > 0 else 0,
        }

        return students, pagination

    def get_student_risk(self, nis: str) -> tuple:
        """
        Get detailed risk information for a student using ML prediction.

        Args:
            nis: Student NIS

        Returns:
            tuple: (risk_data, error)
        """
        # Check if student exists
        student = student_repository.get_by_nis(nis)
        if not student:
            return None, "Student not found"

        # Check cached risk data first
        cached_risk = self.repository.get_student_risk(nis)

        # Always run ML prediction for fresh data
        ml_result = MLService.predict_risk(nis)

        risk_tier = ml_result.get("risk_tier", "GREEN")
        risk_level = TIER_TO_LEVEL.get(risk_tier, "low")
        risk_score = self._calculate_risk_score(ml_result)

        risk_data = {
            "student_nis": nis,
            "student_name": student.name,
            "class_id": student.class_id,
            "class_name": (
                student.student_class.class_name if student.student_class else None
            ),
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_probability": ml_result.get("risk_probability", 0.0),
            "explanation_text": ml_result.get("explanation_text", ""),
            "factors": ml_result.get("factors", {}),
            "prediction_method": ml_result.get("prediction_method", "unknown"),
            "is_rule_triggered": ml_result.get("is_rule_overridden", False),
            "rule_reason": ml_result.get("rule_reason"),
            "recommendations": get_tier_recommendations(risk_tier),
            "last_updated": datetime.utcnow().isoformat(),
            "response_time_ms": ml_result.get("response_time_ms", 0),
            "alert_generated": False,
        }

        return risk_data, None

    def get_alerts(
        self,
        status: Optional[str] = None,
        class_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple:
        """
        Get risk alerts.

        Args:
            status: Filter by status
            class_id: Filter by class
            page: Page number
            per_page: Items per page

        Returns:
            tuple: (alerts list, pagination dict)
        """
        alerts, total = self.repository.get_alerts(
            status=status, class_id=class_id, page=page, per_page=per_page
        )

        import math

        pagination = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": math.ceil(total / per_page) if per_page > 0 else 0,
        }

        return alerts, pagination

    def take_alert_action(
        self,
        alert_id: int,
        action: str,
        notes: Optional[str] = None,
        follow_up_date: Optional[date] = None,
        status: str = "acknowledged",
    ) -> tuple:
        """
        Take action on a risk alert.

        Args:
            alert_id: Alert ID
            action: Action taken
            notes: Action notes
            follow_up_date: Follow-up date
            status: New status

        Returns:
            tuple: (success, error)
        """
        alert = self.repository.get_alert_by_id(alert_id)
        if not alert:
            return False, "Alert not found"

        success = self.repository.update_alert_action(
            alert_id=alert_id,
            action=action,
            notes=notes,
            follow_up_date=follow_up_date,
            status=status,
        )

        return success, None

    def get_risk_history(self, nis: str) -> tuple:
        """
        Get risk history for a student.

        Args:
            nis: Student NIS

        Returns:
            tuple: (history list, error)
        """
        # Check if student exists
        student = student_repository.get_by_nis(nis)
        if not student:
            return None, "Student not found"

        history = self.repository.get_risk_history(nis)

        return {
            "student_nis": nis,
            "student_name": student.name,
            "class_id": student.class_id,
            "history": history,
        }, None

    def recalculate_risks(
        self, class_id: Optional[str] = None, student_nis: Optional[str] = None
    ) -> dict:
        """
        Recalculate risk scores for students using ML predictions.

        Args:
            class_id: Optional class filter
            student_nis: Optional single student

        Returns:
            dict: Recalculation results with detailed statistics
        """
        results = {
            "processed": 0,
            "high_risk": 0,
            "medium_risk": 0,
            "low_risk": 0,
            "errors": 0,
            "alerts_generated": 0,
            "prediction_methods": {"ml": 0, "rule": 0, "heuristic": 0, "error": 0},
        }

        # Get students to process
        if student_nis:
            student_list = [student_nis]
        else:
            student_list = self.repository.get_all_active_students(class_id)

        for nis in student_list:
            try:
                # Run ML prediction
                ml_result = MLService.predict_risk(nis)

                risk_tier = ml_result.get("risk_tier", "GREEN")
                risk_level = TIER_TO_LEVEL.get(risk_tier, "low")
                risk_score = self._calculate_risk_score(ml_result)
                prediction_method = ml_result.get("prediction_method", "unknown")

                # Build factors dictionary
                factors = {
                    "ml_probability": ml_result.get("risk_probability", 0.0),
                    "prediction_method": prediction_method,
                    "is_rule_triggered": ml_result.get("is_rule_overridden", False),
                    **ml_result.get("factors", {}),
                }

                if ml_result.get("rule_reason"):
                    factors["rule_reason"] = ml_result.get("rule_reason")

                # Add explanation_text from ML interpretation
                if ml_result.get("explanation_text"):
                    factors["explanation_text"] = ml_result.get("explanation_text")

                # Save to history
                self.repository.save_risk_history(
                    student_nis=nis,
                    risk_level=risk_level,
                    risk_score=risk_score,
                    factors=factors,
                )

                results["processed"] += 1

                # Track prediction method
                if prediction_method in results["prediction_methods"]:
                    results["prediction_methods"][prediction_method] += 1

                # Count by level
                if risk_level == "high":
                    results["high_risk"] += 1
                    # Generate alert for high risk
                    self._generate_alert_if_needed(nis, ml_result)
                    results["alerts_generated"] += 1
                elif risk_level == "medium":
                    results["medium_risk"] += 1
                else:
                    results["low_risk"] += 1

            except Exception as e:
                logger.error(f"Error processing student {nis}: {e}")
                results["errors"] += 1
                results["prediction_methods"]["error"] += 1

        return results

    def _calculate_risk_score(self, ml_result: dict) -> int:
        """
        Calculate risk score based on ML prediction.

        Uses probability for more granular scoring:
        - If rule triggered: Use tier-based score
        - Otherwise: Scale probability to 0-100
        """
        risk_tier = ml_result.get("risk_tier", "GREEN")
        probability = ml_result.get("risk_probability", 0.0)
        is_rule_triggered = ml_result.get("is_rule_overridden", False)

        if is_rule_triggered:
            # Rule triggered = fixed high score
            return TIER_TO_SCORE.get(risk_tier, 15)

        # Scale probability to score (0-100)
        return int(probability * 100)

    def _map_risk_tier_to_level(self, tier: str) -> str:
        """Map ML tier (RED/YELLOW/GREEN) to level (high/medium/low)."""
        return TIER_TO_LEVEL.get(tier, "low")

    # Legacy methods for backward compatibility
    def _map_risk_color_to_level(self, color: str) -> str:
        """Map EWS color to risk level (legacy compatibility)."""
        mapping = {
            "Red": "high",
            "RED": "high",
            "Yellow": "medium",
            "YELLOW": "medium",
            "Green": "low",
            "GREEN": "low",
            "Unknown": "low",
            "Error": "low",
        }
        return mapping.get(color, "low")

    def _estimate_risk_score(self, color: str) -> int:
        """Estimate risk score from color (legacy compatibility)."""
        scores = {
            "Red": 85,
            "RED": 85,
            "Yellow": 50,
            "YELLOW": 50,
            "Green": 15,
            "GREEN": 15,
            "Unknown": 0,
            "Error": 0,
        }
        return scores.get(color, 0)

    def _generate_alert_if_needed(self, nis: str, ml_result: dict) -> None:
        """Generate an alert for high-risk student if not already pending."""
        try:
            # Check for existing pending alert
            alerts, _ = self.repository.get_alerts(status="pending")
            existing = [a for a in alerts if a["student_nis"] == nis]

            if not existing:
                # Build detailed alert message
                factors = ml_result.get("factors", {})
                probability = ml_result.get("risk_probability", 0)
                method = ml_result.get("prediction_method", "unknown")

                message_parts = [f"High risk detected (probability: {probability:.1%})"]

                if ml_result.get("rule_reason"):
                    message_parts.append(
                        f"Rule triggered: {ml_result.get('rule_reason')}"
                    )

                if factors.get("absent_ratio"):
                    message_parts.append(f"Absent ratio: {factors['absent_ratio']:.1%}")

                if factors.get("trend_score") and factors.get("trend_score") < 0:
                    message_parts.append(
                        f"Declining trend: {factors['trend_score']:.2f}"
                    )

                self.repository.create_alert(
                    student_nis=nis,
                    alert_type="high_risk",
                    message=" | ".join(message_parts),
                )
        except Exception as e:
            logger.error(f"Error generating alert for {nis}: {e}")


# Singleton instance
risk_service = RiskService()
