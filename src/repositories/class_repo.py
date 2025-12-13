"""
Class repository for database operations.
Handles all direct database interactions for Class model.
"""
from typing import Optional, List
from sqlalchemy import func
from src.domain.models import Class, Student
from src.app.extensions import db


class ClassRepository:
    """Repository class for Class entity database operations."""
    
    def get_by_id(self, class_id: str) -> Optional[Class]:
        """
        Get a class by ID (primary key).
        
        Args:
            class_id: Class ID
            
        Returns:
            Class or None if not found
        """
        return db.session.query(Class).filter(Class.class_id == class_id).first()
    
    def exists(self, class_id: str) -> bool:
        """
        Check if a class with given ID exists.
        
        Args:
            class_id: Class ID
            
        Returns:
            bool: True if exists
        """
        return db.session.query(
            db.session.query(Class).filter(Class.class_id == class_id).exists()
        ).scalar()
    
    def get_all(self):
        """
        Get query for all classes.
        
        Returns:
            SQLAlchemy query object
        """
        return db.session.query(Class).order_by(Class.class_name.asc())
    
    def get_all_with_student_count(self) -> List[dict]:
        """
        Get all classes with student count.
        
        Returns:
            List of dicts with class info and student count
        """
        results = db.session.query(
            Class,
            func.count(Student.nis).filter(Student.is_active == True).label('student_count')
        ).outerjoin(
            Student, Class.class_id == Student.class_id
        ).group_by(Class.class_id).order_by(Class.class_name.asc()).all()
        
        return [
            {
                "class": cls,
                "student_count": count or 0
            }
            for cls, count in results
        ]
    
    def create(self, class_data: dict) -> Class:
        """
        Create a new class.
        
        Args:
            class_data: Dictionary with class fields
            
        Returns:
            Created Class instance
        """
        class_obj = Class(**class_data)
        db.session.add(class_obj)
        db.session.commit()
        return class_obj
    
    def update(self, class_id: str, update_data: dict) -> Optional[Class]:
        """
        Update an existing class.
        
        Args:
            class_id: Class ID
            update_data: Dictionary with fields to update
            
        Returns:
            Updated Class or None if not found
        """
        class_obj = self.get_by_id(class_id)
        if not class_obj:
            return None
        
        for key, value in update_data.items():
            if hasattr(class_obj, key):
                setattr(class_obj, key, value)
        
        db.session.commit()
        return class_obj
    
    def delete(self, class_id: str) -> bool:
        """
        Delete a class (hard delete).
        
        Args:
            class_id: Class ID
            
        Returns:
            bool: True if deleted, False if not found
        """
        class_obj = self.get_by_id(class_id)
        if not class_obj:
            return False
        
        db.session.delete(class_obj)
        db.session.commit()
        return True
    
    def has_active_students(self, class_id: str) -> bool:
        """
        Check if a class has active students.
        
        Args:
            class_id: Class ID
            
        Returns:
            bool: True if has active students
        """
        count = db.session.query(func.count(Student.nis)).filter(
            Student.class_id == class_id,
            Student.is_active == True
        ).scalar()
        
        return (count or 0) > 0
    
    def get_student_count(self, class_id: str, active_only: bool = True) -> int:
        """
        Get student count for a class.
        
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


# Singleton instance
class_repository = ClassRepository()
