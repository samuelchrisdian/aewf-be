"""
Risk service for business logic.
Handles all business operations for risk management and EWS.
"""
from typing import Optional, List
from datetime import date, datetime
import logging

from src.repositories.risk_repo import risk_repository
from src.repositories.student_repo import student_repository
from src.ews_engine import assess_risk

logger = logging.getLogger(__name__)


class RiskService:
    """Service class for Risk Management business logic."""
    
    def __init__(self):
        self.repository = risk_repository
    
    def get_at_risk_students(
        self,
        level: Optional[str] = None,
        class_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> tuple:
        """
        Get list of at-risk students.
        
        Args:
            level: Filter by risk level
            class_id: Filter by class
            page: Page number
            per_page: Items per page
            
        Returns:
            tuple: (students list, pagination dict)
        """
        students, total = self.repository.get_at_risk_students(
            level=level,
            class_id=class_id,
            page=page,
            per_page=per_page
        )
        
        import math
        pagination = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": math.ceil(total / per_page) if per_page > 0 else 0
        }
        
        return students, pagination
    
    def get_student_risk(self, nis: str) -> tuple:
        """
        Get detailed risk information for a student.
        
        Args:
            nis: Student NIS
            
        Returns:
            tuple: (risk_data, error)
        """
        # Check if student exists
        student = student_repository.get_by_nis(nis)
        if not student:
            return None, "Student not found"
        
        risk_data = self.repository.get_student_risk(nis)
        if not risk_data:
            # Run assessment if no history exists
            risk_result = assess_risk(nis)
            risk_data = {
                "student_nis": nis,
                "student_name": student.name,
                "class_id": student.class_id,
                "class_name": student.student_class.class_name if student.student_class else None,
                "risk_level": self._map_risk_color_to_level(risk_result.get("risk", "Unknown")),
                "risk_score": self._estimate_risk_score(risk_result.get("risk", "Unknown")),
                "factors": {"rationale": risk_result.get("rationale", "")},
                "last_updated": datetime.utcnow().isoformat(),
                "alert_generated": False
            }
        
        return risk_data, None
    
    def get_alerts(
        self,
        status: Optional[str] = None,
        class_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
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
            status=status,
            class_id=class_id,
            page=page,
            per_page=per_page
        )
        
        import math
        pagination = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": math.ceil(total / per_page) if per_page > 0 else 0
        }
        
        return alerts, pagination
    
    def take_alert_action(
        self,
        alert_id: int,
        action: str,
        notes: Optional[str] = None,
        follow_up_date: Optional[date] = None,
        status: str = "acknowledged"
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
            status=status
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
            "history": history
        }, None
    
    def recalculate_risks(
        self,
        class_id: Optional[str] = None,
        student_nis: Optional[str] = None
    ) -> dict:
        """
        Recalculate risk scores for students.
        
        Args:
            class_id: Optional class filter
            student_nis: Optional single student
            
        Returns:
            dict: Recalculation results
        """
        results = {
            "processed": 0,
            "high_risk": 0,
            "medium_risk": 0,
            "low_risk": 0,
            "errors": 0,
            "alerts_generated": 0
        }
        
        # Get students to process
        if student_nis:
            student_list = [student_nis]
        else:
            student_list = self.repository.get_all_active_students(class_id)
        
        for nis in student_list:
            try:
                # Run EWS assessment
                risk_result = assess_risk(nis)
                risk_level = self._map_risk_color_to_level(risk_result.get("risk", "Unknown"))
                risk_score = self._estimate_risk_score(risk_result.get("risk", "Unknown"))
                
                # Extract factors from rationale
                factors = {
                    "rationale": risk_result.get("rationale", ""),
                    "raw_risk": risk_result.get("risk", "Unknown")
                }
                
                # Save to history
                self.repository.save_risk_history(
                    student_nis=nis,
                    risk_level=risk_level,
                    risk_score=risk_score,
                    factors=factors
                )
                
                results["processed"] += 1
                
                # Count by level
                if risk_level == "high":
                    results["high_risk"] += 1
                    # Generate alert for high risk
                    self._generate_alert_if_needed(nis, risk_result)
                    results["alerts_generated"] += 1
                elif risk_level == "medium":
                    results["medium_risk"] += 1
                else:
                    results["low_risk"] += 1
                    
            except Exception as e:
                logger.error(f"Error processing student {nis}: {e}")
                results["errors"] += 1
        
        return results
    
    def _map_risk_color_to_level(self, color: str) -> str:
        """Map EWS color to risk level."""
        mapping = {
            "Red": "high",
            "Yellow": "medium",
            "Green": "low",
            "Unknown": "low",
            "Error": "low"
        }
        return mapping.get(color, "low")
    
    def _estimate_risk_score(self, color: str) -> int:
        """Estimate risk score from color."""
        scores = {
            "Red": 85,
            "Yellow": 50,
            "Green": 15,
            "Unknown": 0,
            "Error": 0
        }
        return scores.get(color, 0)
    
    def _generate_alert_if_needed(self, nis: str, risk_result: dict) -> None:
        """Generate an alert for high-risk student if not already pending."""
        try:
            # Check for existing pending alert
            alerts, _ = self.repository.get_alerts(status="pending")
            existing = [a for a in alerts if a["student_nis"] == nis]
            
            if not existing:
                self.repository.create_alert(
                    student_nis=nis,
                    alert_type="high_risk",
                    message=risk_result.get("rationale", "High risk detected")
                )
        except Exception as e:
            logger.error(f"Error generating alert for {nis}: {e}")


# Singleton instance
risk_service = RiskService()
