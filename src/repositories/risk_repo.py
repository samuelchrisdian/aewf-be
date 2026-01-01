"""
Risk repository for database operations.
Handles all database operations for risk management.
"""

from typing import Optional, List
from datetime import date, datetime, timedelta
from sqlalchemy import func, desc, and_

from src.db_config import SessionLocal
from src.domain.models import (
    RiskAlert,
    RiskHistory,
    Student,
    Class,
    Teacher,
    AttendanceDaily,
)


class RiskRepository:
    """Repository class for Risk database operations."""

    def get_at_risk_students(
        self,
        level: Optional[str] = None,
        class_id: Optional[str] = None,
        class_ids: Optional[List[str]] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple:
        """
        Get list of at-risk students with their latest risk scores.

        Args:
            level: Filter by risk level ('high', 'medium', 'low')
            class_id: Filter by class (single)
            class_ids: Filter by multiple class IDs (for teacher role)
            page: Page number
            per_page: Items per page

        Returns:
            tuple: (list of students, total count)
        """
        session = SessionLocal()
        try:
            # Subquery to get the latest risk history for each student
            latest_risk = (
                session.query(
                    RiskHistory.student_nis,
                    func.max(RiskHistory.calculated_at).label("latest"),
                )
                .group_by(RiskHistory.student_nis)
                .subquery()
            )

            # Main query joining with latest risk
            query = (
                session.query(
                    RiskHistory,
                    Student.name.label("student_name"),
                    Student.class_id,
                    Class.class_name,
                )
                .join(
                    latest_risk,
                    and_(
                        RiskHistory.student_nis == latest_risk.c.student_nis,
                        RiskHistory.calculated_at == latest_risk.c.latest,
                    ),
                )
                .join(Student, RiskHistory.student_nis == Student.nis)
                .outerjoin(Class, Student.class_id == Class.class_id)
            )

            # Apply filters
            if level:
                query = query.filter(RiskHistory.risk_level == level)
            if class_id:
                query = query.filter(Student.class_id == class_id)
            elif class_ids is not None:
                if len(class_ids) == 0:
                    # Teacher has no classes, return empty
                    return [], 0
                query = query.filter(Student.class_id.in_(class_ids))

            # Order by risk score descending
            query = query.order_by(desc(RiskHistory.risk_score))

            # Get total count
            total = query.count()

            # Paginate
            offset = (page - 1) * per_page
            results = query.offset(offset).limit(per_page).all()

            # Format results
            students = []
            for risk_history, student_name, student_class_id, class_name in results:
                # Check if there's an active alert
                alert = (
                    session.query(RiskAlert)
                    .filter(
                        RiskAlert.student_nis == risk_history.student_nis,
                        RiskAlert.status == "pending",
                    )
                    .first()
                )

                students.append(
                    {
                        "student_nis": risk_history.student_nis,
                        "student_name": student_name,
                        "class_id": student_class_id,
                        "risk_level": risk_history.risk_level,
                        "risk_score": risk_history.risk_score,
                        "factors": risk_history.factors or {},
                        "last_updated": (
                            risk_history.calculated_at.isoformat()
                            if risk_history.calculated_at
                            else None
                        ),
                        "alert_generated": alert is not None,
                    }
                )

            return students, total

        finally:
            session.close()

    def get_student_risk(self, nis: str) -> Optional[dict]:
        """
        Get detailed risk information for a specific student.

        Args:
            nis: Student NIS

        Returns:
            dict: Student risk details or None if not found
        """
        session = SessionLocal()
        try:
            # Get student info
            student = session.query(Student).filter(Student.nis == nis).first()
            if not student:
                return None

            # Get latest risk history
            risk_history = (
                session.query(RiskHistory)
                .filter(RiskHistory.student_nis == nis)
                .order_by(desc(RiskHistory.calculated_at))
                .first()
            )

            # Get class info
            class_info = (
                session.query(Class).filter(Class.class_id == student.class_id).first()
            )

            # Check for active alert
            alert = (
                session.query(RiskAlert)
                .filter(RiskAlert.student_nis == nis, RiskAlert.status == "pending")
                .first()
            )

            return {
                "student_nis": student.nis,
                "student_name": student.name,
                "class_id": student.class_id,
                "class_name": class_info.class_name if class_info else None,
                "risk_level": risk_history.risk_level if risk_history else "unknown",
                "risk_score": risk_history.risk_score if risk_history else 0,
                "factors": risk_history.factors if risk_history else {},
                "last_updated": (
                    risk_history.calculated_at.isoformat() if risk_history else None
                ),
                "alert_generated": alert is not None,
            }

        finally:
            session.close()

    def get_alerts(
        self,
        status: Optional[str] = None,
        class_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple:
        """
        Get list of risk alerts.

        Args:
            status: Filter by status ('pending', 'acknowledged', 'resolved')
            class_id: Filter by class
            page: Page number
            per_page: Items per page

        Returns:
            tuple: (list of alerts, total count)
        """
        session = SessionLocal()
        try:
            query = (
                session.query(
                    RiskAlert,
                    Student.name.label("student_name"),
                    Student.class_id,
                    Class.class_name,
                    Teacher.name.label("assignee_name"),
                )
                .join(Student, RiskAlert.student_nis == Student.nis)
                .outerjoin(Class, Student.class_id == Class.class_id)
                .outerjoin(Teacher, RiskAlert.assigned_to == Teacher.teacher_id)
            )

            # Apply filters
            if status:
                query = query.filter(RiskAlert.status == status)
            if class_id:
                query = query.filter(Student.class_id == class_id)

            # Order by created_at descending
            query = query.order_by(desc(RiskAlert.created_at))

            # Get total count
            total = query.count()

            # Paginate
            offset = (page - 1) * per_page
            results = query.offset(offset).limit(per_page).all()

            # Format results
            alerts = []
            for (
                alert,
                student_name,
                student_class_id,
                class_name,
                assignee_name,
            ) in results:
                alerts.append(
                    {
                        "id": alert.id,
                        "student_nis": alert.student_nis,
                        "student_name": student_name,
                        "class_id": student_class_id,
                        "class_name": class_name,
                        "alert_type": alert.alert_type,
                        "message": alert.message,
                        "created_at": (
                            alert.created_at.isoformat() if alert.created_at else None
                        ),
                        "status": alert.status,
                        "assigned_to": alert.assigned_to,
                        "assignee_name": assignee_name,
                        "action_taken": alert.action_taken,
                        "action_notes": alert.action_notes,
                        "follow_up_date": (
                            alert.follow_up_date.isoformat()
                            if alert.follow_up_date
                            else None
                        ),
                        "resolved_at": (
                            alert.resolved_at.isoformat() if alert.resolved_at else None
                        ),
                    }
                )

            return alerts, total

        finally:
            session.close()

    def get_alert_by_id(self, alert_id: int) -> Optional[RiskAlert]:
        """Get a single alert by ID."""
        session = SessionLocal()
        try:
            return session.query(RiskAlert).filter(RiskAlert.id == alert_id).first()
        finally:
            session.close()

    def update_alert_action(
        self,
        alert_id: int,
        action: str,
        notes: Optional[str] = None,
        follow_up_date: Optional[date] = None,
        status: str = "acknowledged",
    ) -> bool:
        """
        Update an alert with action taken.

        Args:
            alert_id: Alert ID
            action: Action taken
            notes: Action notes
            follow_up_date: Follow-up date
            status: New status

        Returns:
            bool: True if updated, False if not found
        """
        session = SessionLocal()
        try:
            alert = session.query(RiskAlert).filter(RiskAlert.id == alert_id).first()
            if not alert:
                return False

            alert.action_taken = action
            alert.action_notes = notes
            alert.follow_up_date = follow_up_date
            alert.status = status

            if status == "resolved":
                alert.resolved_at = datetime.utcnow()

            session.commit()
            return True

        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_risk_history(self, nis: str, limit: int = 30) -> List[dict]:
        """
        Get risk history for a student.

        Args:
            nis: Student NIS
            limit: Maximum records to return

        Returns:
            list: Risk history records
        """
        session = SessionLocal()
        try:
            records = (
                session.query(RiskHistory)
                .filter(RiskHistory.student_nis == nis)
                .order_by(desc(RiskHistory.calculated_at))
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": record.id,
                    "student_nis": record.student_nis,
                    "risk_level": record.risk_level,
                    "risk_score": record.risk_score,
                    "factors": record.factors or {},
                    "calculated_at": (
                        record.calculated_at.isoformat()
                        if record.calculated_at
                        else None
                    ),
                }
                for record in records
            ]

        finally:
            session.close()

    def create_alert(
        self,
        student_nis: str,
        alert_type: str,
        message: str,
        assigned_to: Optional[str] = None,
    ) -> RiskAlert:
        """
        Create a new risk alert.

        Args:
            student_nis: Student NIS
            alert_type: Type of alert
            message: Alert message
            assigned_to: Teacher ID to assign

        Returns:
            RiskAlert: Created alert
        """
        session = SessionLocal()
        try:
            alert = RiskAlert(
                student_nis=student_nis,
                alert_type=alert_type,
                message=message,
                assigned_to=assigned_to,
                status="pending",
            )
            session.add(alert)
            session.commit()
            session.refresh(alert)
            return alert

        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def save_risk_history(
        self,
        student_nis: str,
        risk_level: str,
        risk_score: int,
        factors: Optional[dict] = None,
    ) -> RiskHistory:
        """
        Save a risk calculation result.

        Args:
            student_nis: Student NIS
            risk_level: Risk level ('high', 'medium', 'low')
            risk_score: Risk score (0-100)
            factors: Risk factors dict

        Returns:
            RiskHistory: Created record
        """
        session = SessionLocal()
        try:
            history = RiskHistory(
                student_nis=student_nis,
                risk_level=risk_level,
                risk_score=risk_score,
                factors=factors,
            )
            session.add(history)
            session.commit()
            session.refresh(history)
            return history

        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_all_active_students(self, class_id: Optional[str] = None) -> List[str]:
        """
        Get all active student NIS values.

        Args:
            class_id: Optional class filter

        Returns:
            list: List of student NIS
        """
        session = SessionLocal()
        try:
            query = session.query(Student.nis).filter(Student.is_active == True)

            if class_id:
                query = query.filter(Student.class_id == class_id)

            return [nis for (nis,) in query.all()]

        finally:
            session.close()

    def get_all_with_details(self, class_id: Optional[str] = None) -> List:
        """
        Get all at-risk students with full details.

        Args:
            class_id: Optional class filter

        Returns:
            list: List of RiskHistory records with student details
        """
        session = SessionLocal()
        try:
            # Subquery to get the latest risk history for each student
            latest_risk = (
                session.query(
                    RiskHistory.student_nis,
                    func.max(RiskHistory.calculated_at).label("latest"),
                )
                .group_by(RiskHistory.student_nis)
                .subquery()
            )

            # Main query joining with latest risk
            query = (
                session.query(RiskHistory)
                .join(
                    latest_risk,
                    and_(
                        RiskHistory.student_nis == latest_risk.c.student_nis,
                        RiskHistory.calculated_at == latest_risk.c.latest,
                    ),
                )
                .join(Student, RiskHistory.student_nis == Student.nis)
            )

            # Apply class filter if provided
            if class_id:
                query = query.filter(Student.class_id == class_id)

            from sqlalchemy.orm import joinedload

            # Order by risk score descending
            query = query.order_by(desc(RiskHistory.risk_score)).options(
                joinedload(RiskHistory.student)
            )

            return query.all()

        finally:
            session.close()

    def count_by_class(self, class_id: str) -> int:
        """
        Count at-risk students in a class.

        Args:
            class_id: Class ID

        Returns:
            int: Count of at-risk students
        """
        session = SessionLocal()
        try:
            # Subquery to get the latest risk history for each student
            latest_risk = (
                session.query(
                    RiskHistory.student_nis,
                    func.max(RiskHistory.calculated_at).label("latest"),
                )
                .group_by(RiskHistory.student_nis)
                .subquery()
            )

            # Count students with risk in this class
            count = (
                session.query(RiskHistory)
                .join(
                    latest_risk,
                    and_(
                        RiskHistory.student_nis == latest_risk.c.student_nis,
                        RiskHistory.calculated_at == latest_risk.c.latest,
                    ),
                )
                .join(Student, RiskHistory.student_nis == Student.nis)
                .filter(Student.class_id == class_id)
                .count()
            )

            return count

        finally:
            session.close()


# Singleton instance
risk_repository = RiskRepository()
