"""
Student repository for database operations.
Handles all direct database interactions for Student model.
"""
from typing import Optional, List, Tuple
from sqlalchemy import or_, func
from src.domain.models import Student, AttendanceDaily
from src.app.extensions import db


class StudentRepository:
    """Repository class for Student entity database operations."""
    
    def get_by_nis(self, nis: str) -> Optional[Student]:
        """
        Get a student by NIS (primary key).
        
        Args:
            nis: Student NIS
            
        Returns:
            Student or None if not found
        """
        return db.session.query(Student).filter(Student.nis == nis).first()
    
    def exists(self, nis: str) -> bool:
        """
        Check if a student with given NIS exists.
        
        Args:
            nis: Student NIS
            
        Returns:
            bool: True if exists
        """
        return db.session.query(
            db.session.query(Student).filter(Student.nis == nis).exists()
        ).scalar()
    
    def get_all(
        self,
        class_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        order: str = 'asc'
    ):
        """
        Get query for all students with optional filters.
        
        Args:
            class_id: Filter by class ID
            is_active: Filter by active status
            search: Search by name (partial match)
            sort_by: Field to sort by (name, nis, class_id)
            order: Sort order ('asc' or 'desc')
            
        Returns:
            SQLAlchemy query object (not executed)
        """
        query = db.session.query(Student)
        
        # Apply filters
        if class_id:
            query = query.filter(Student.class_id == class_id)
        
        if is_active is not None:
            query = query.filter(Student.is_active == is_active)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Student.name.ilike(search_pattern),
                    Student.nis.ilike(search_pattern)
                )
            )
        
        # Apply sorting
        if sort_by:
            sort_column = getattr(Student, sort_by, None)
            if sort_column is not None:
                if order.lower() == 'desc':
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())
        else:
            # Default sort by name
            query = query.order_by(Student.name.asc())
        
        return query
    
    def create(self, student_data: dict) -> Student:
        """
        Create a new student.
        
        Args:
            student_data: Dictionary with student fields
            
        Returns:
            Created Student instance
        """
        student = Student(**student_data)
        db.session.add(student)
        db.session.commit()
        return student
    
    def update(self, nis: str, update_data: dict) -> Optional[Student]:
        """
        Update an existing student.
        
        Args:
            nis: Student NIS
            update_data: Dictionary with fields to update
            
        Returns:
            Updated Student or None if not found
        """
        student = self.get_by_nis(nis)
        if not student:
            return None
        
        for key, value in update_data.items():
            if hasattr(student, key):
                setattr(student, key, value)
        
        db.session.commit()
        return student
    
    def soft_delete(self, nis: str) -> bool:
        """
        Soft delete a student by setting is_active to False.
        
        Args:
            nis: Student NIS
            
        Returns:
            bool: True if deleted, False if not found
        """
        student = self.get_by_nis(nis)
        if not student:
            return False
        
        student.is_active = False
        db.session.commit()
        return True
    
    def count_by_class(self, class_id: str, active_only: bool = True) -> int:
        """
        Count students in a class.
        
        Args:
            class_id: Class ID
            active_only: Count only active students
            
        Returns:
            int: Number of students
        """
        query = db.session.query(func.count(Student.nis)).filter(
            Student.class_id == class_id
        )
        
        if active_only:
            query = query.filter(Student.is_active == True)
        
        return query.scalar() or 0
    
    def get_by_class_ids(self, class_ids: List[str]) -> List[Student]:
        """
        Get students belonging to given class IDs.
        
        Args:
            class_ids: List of class IDs
            
        Returns:
            List of Students
        """
        return db.session.query(Student).filter(
            Student.class_id.in_(class_ids)
        ).all()
    
    def get_attendance_summary(self, nis: str) -> dict:
        """
        Calculate attendance summary for a student.
        
        Args:
            nis: Student NIS
            
        Returns:
            dict: Attendance statistics
        """
        # Get all attendance records for this student
        records = db.session.query(AttendanceDaily).filter(
            AttendanceDaily.student_nis == nis
        ).all()
        
        total = len(records)
        if total == 0:
            return {
                "total_days": 0,
                "present": 0,
                "late": 0,
                "absent": 0,
                "sick": 0,
                "permission": 0,
                "attendance_rate": 0.0
            }
        
        # Count by status
        status_counts = {
            "Present": 0,
            "Late": 0,
            "Absent": 0,
            "Sick": 0,
            "Permission": 0
        }
        
        for record in records:
            status = record.status
            if status in status_counts:
                status_counts[status] += 1
        
        # Calculate attendance rate (Present + Late / Total * 100)
        attended = status_counts["Present"] + status_counts["Late"]
        attendance_rate = round((attended / total) * 100, 1) if total > 0 else 0.0
        
        return {
            "total_days": total,
            "present": status_counts["Present"],
            "late": status_counts["Late"],
            "absent": status_counts["Absent"],
            "sick": status_counts["Sick"],
            "permission": status_counts["Permission"],
            "attendance_rate": attendance_rate
        }


# Singleton instance
student_repository = StudentRepository()
