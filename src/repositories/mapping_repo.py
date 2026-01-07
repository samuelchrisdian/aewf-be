"""
Mapping repository for database operations.
Handles all direct database interactions for StudentMachineMap model.
"""

from typing import Optional, List
from sqlalchemy import func
from src.domain.models import MachineUser, StudentMachineMap, Student, Machine
from src.app.extensions import db


class MappingRepository:
    """Repository class for StudentMachineMap entity database operations."""

    def get_by_id(self, mapping_id: int) -> Optional[StudentMachineMap]:
        """
        Get a mapping by ID.

        Args:
            mapping_id: Mapping ID

        Returns:
            StudentMachineMap or None if not found
        """
        return (
            db.session.query(StudentMachineMap)
            .filter(StudentMachineMap.id == mapping_id)
            .first()
        )

    def get_all(self, status: Optional[str] = None, machine_id: Optional[int] = None):
        """
        Get query for all mappings with optional filters.

        Args:
            status: Filter by status (suggested, verified, rejected)
            machine_id: Filter by machine ID

        Returns:
            SQLAlchemy query object
        """
        query = db.session.query(StudentMachineMap).join(
            MachineUser, StudentMachineMap.machine_user_id_fk == MachineUser.id
        )

        if status:
            query = query.filter(StudentMachineMap.status == status)

        if machine_id:
            query = query.filter(MachineUser.machine_id == machine_id)

        return query.order_by(StudentMachineMap.id.desc())

    def get_unmapped_users(self, machine_id: Optional[int] = None):
        """
        Get machine users that don't have any mapping.

        Args:
            machine_id: Optional filter by machine ID

        Returns:
            SQLAlchemy query for unmapped MachineUsers
        """
        # Subquery for mapped user IDs
        mapped_ids = db.session.query(StudentMachineMap.machine_user_id_fk).subquery()

        query = db.session.query(MachineUser).filter(MachineUser.id.notin_(mapped_ids))

        if machine_id:
            query = query.filter(MachineUser.machine_id == machine_id)

        return query.order_by(MachineUser.machine_user_name.asc())

    def get_unmapped_students(
        self,
        class_id: Optional[str] = None,
        is_active: Optional[bool] = True,
        search: Optional[str] = None,
    ):
        """
        Get students that don't have any mapping to a machine user.

        Args:
            class_id: Optional filter by class ID
            is_active: Optional filter by active status (default True)
            search: Optional search by student name/NIS

        Returns:
            SQLAlchemy query for unmapped Students
        """
        from sqlalchemy import or_

        # Subquery for mapped student NIS
        mapped_student_nis = db.session.query(
            StudentMachineMap.student_nis
        ).subquery()

        # Base query: students whose NIS not in mapped list
        query = db.session.query(Student).filter(Student.nis.notin_(mapped_student_nis))

        if class_id:
            query = query.filter(Student.class_id == class_id)

        if is_active is not None:
            query = query.filter(Student.is_active == is_active)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(Student.name.ilike(search_pattern), Student.nis.ilike(search_pattern))
            )

        return query.order_by(Student.name.asc())

    def get_stats(self) -> dict:
        """
        Get mapping statistics.

        Returns:
            dict: Mapping statistics
        """
        # Total machine users
        total_users = db.session.query(func.count(MachineUser.id)).scalar() or 0

        # Count by status
        verified_count = (
            db.session.query(func.count(StudentMachineMap.id))
            .filter(StudentMachineMap.status == "verified")
            .scalar()
            or 0
        )

        suggested_count = (
            db.session.query(func.count(StudentMachineMap.id))
            .filter(StudentMachineMap.status == "suggested")
            .scalar()
            or 0
        )

        mapped_count = verified_count + suggested_count
        unmapped_count = total_users - mapped_count

        # Calculate mapping rate
        mapping_rate = (
            round((mapped_count / total_users * 100), 1) if total_users > 0 else 0.0
        )

        return {
            "total_machine_users": total_users,
            "mapped_count": mapped_count,
            "verified_count": verified_count,
            "suggested_count": suggested_count,
            "unmapped_count": max(0, unmapped_count),
            "mapping_rate": mapping_rate,
        }

    def delete(self, mapping_id: int) -> bool:
        """
        Delete a mapping.

        Args:
            mapping_id: Mapping ID

        Returns:
            bool: True if deleted, False if not found
        """
        mapping = self.get_by_id(mapping_id)
        if not mapping:
            return False

        db.session.delete(mapping)
        db.session.commit()
        return True

    def bulk_update_status(self, updates: List[dict], admin_username: str) -> dict:
        """
        Bulk update mapping statuses.

        Args:
            updates: List of dicts with mapping_id, status, reason
            admin_username: Username of admin performing verification

        Returns:
            dict: Results with success/failed counts
        """
        import datetime

        results = {"verified": 0, "rejected": 0, "failed": 0, "errors": []}

        for item in updates:
            mapping_id = item.get("mapping_id")
            status = item.get("status")

            mapping = self.get_by_id(mapping_id)
            if not mapping:
                results["failed"] += 1
                results["errors"].append(f"Mapping {mapping_id} not found")
                continue

            if status == "verified":
                mapping.status = "verified"
                mapping.verified_at = datetime.datetime.utcnow()
                mapping.verified_by = admin_username
                results["verified"] += 1
            elif status == "rejected":
                # Delete the mapping on rejection
                db.session.delete(mapping)
                results["rejected"] += 1

        db.session.commit()
        return results

    def get_all_mappings(
        self,
        status: Optional[str] = None,
        machine_id: Optional[int] = None,
        class_id: Optional[str] = None,
        search: Optional[str] = None,
    ):
        """
        Get query for all mappings with full details.

        Args:
            status: Filter by status (suggested, verified, rejected)
            machine_id: Filter by machine ID
            class_id: Filter by student class ID
            search: Search by student or machine user name

        Returns:
            SQLAlchemy query object
        """
        from sqlalchemy import or_

        query = (
            db.session.query(StudentMachineMap)
            .join(MachineUser, StudentMachineMap.machine_user_id_fk == MachineUser.id)
            .join(Student, StudentMachineMap.student_nis == Student.nis)
        )

        if status:
            query = query.filter(StudentMachineMap.status == status)

        if machine_id:
            query = query.filter(MachineUser.machine_id == machine_id)

        if class_id:
            query = query.filter(Student.class_id == class_id)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Student.name.ilike(search_pattern),
                    Student.nis.ilike(search_pattern),
                    MachineUser.machine_user_name.ilike(search_pattern),
                    MachineUser.machine_user_id.ilike(search_pattern),
                )
            )

        return query.order_by(StudentMachineMap.id.desc())

    def get_by_student_nis(self, student_nis: str) -> Optional[StudentMachineMap]:
        """
        Get mapping by student NIS.

        Args:
            student_nis: Student NIS

        Returns:
            StudentMachineMap or None if not found
        """
        return (
            db.session.query(StudentMachineMap)
            .filter(StudentMachineMap.student_nis == student_nis)
            .first()
        )

    def delete_by_student_nis(self, student_nis: str) -> bool:
        """
        Delete mapping by student NIS.

        Args:
            student_nis: Student NIS

        Returns:
            bool: True if deleted, False if not found
        """
        mapping = self.get_by_student_nis(student_nis)
        if not mapping:
            return False

        db.session.delete(mapping)
        db.session.commit()
        return True


# Singleton instance
mapping_repository = MappingRepository()
