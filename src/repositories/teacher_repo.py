"""
Teacher repository for database operations.
Handles all direct database interactions for Teacher model.
"""
from typing import Optional, List
from sqlalchemy import func
from src.domain.models import Teacher, Class, Student
from src.app.extensions import db


class TeacherRepository:
    """Repository class for Teacher entity database operations."""
    
    def get_by_id(self, teacher_id: str) -> Optional[Teacher]:
        """
        Get a teacher by ID (primary key).
        
        Args:
            teacher_id: Teacher ID
            
        Returns:
            Teacher or None if not found
        """
        return db.session.query(Teacher).filter(
            Teacher.teacher_id == teacher_id
        ).first()
    
    def exists(self, teacher_id: str) -> bool:
        """
        Check if a teacher with given ID exists.
        
        Args:
            teacher_id: Teacher ID
            
        Returns:
            bool: True if exists
        """
        return db.session.query(
            db.session.query(Teacher).filter(
                Teacher.teacher_id == teacher_id
            ).exists()
        ).scalar()
    
    def get_all(self, role_filter: Optional[str] = None):
        """
        Get query for all teachers with optional role filter.
        
        Args:
            role_filter: Filter by role (e.g., "Wali Kelas")
            
        Returns:
            SQLAlchemy query object
        """
        query = db.session.query(Teacher)
        
        if role_filter:
            query = query.filter(Teacher.role == role_filter)
        
        return query.order_by(Teacher.name.asc())
    
    def get_classes_by_teacher(self, teacher_id: str) -> List[Class]:
        """
        Get classes managed by a teacher (as wali kelas).
        
        Args:
            teacher_id: Teacher ID
            
        Returns:
            List of Class objects
        """
        return db.session.query(Class).filter(
            Class.wali_kelas_id == teacher_id
        ).all()
    
    def get_classes_with_student_count(self, teacher_id: str) -> List[dict]:
        """
        Get classes with student count for a teacher.
        
        Args:
            teacher_id: Teacher ID
            
        Returns:
            List of dicts with class info and student count
        """
        results = db.session.query(
            Class,
            func.count(Student.nis).filter(Student.is_active == True).label('student_count')
        ).outerjoin(
            Student, Class.class_id == Student.class_id
        ).filter(
            Class.wali_kelas_id == teacher_id
        ).group_by(Class.class_id).all()
        
        return [
            {
                "class_id": cls.class_id,
                "class_name": cls.class_name,
                "student_count": count or 0
            }
            for cls, count in results
        ]
    
    def create(self, teacher_data: dict) -> Teacher:
        """
        Create a new teacher.
        
        Args:
            teacher_data: Dictionary with teacher fields
            
        Returns:
            Created Teacher instance
        """
        teacher = Teacher(**teacher_data)
        db.session.add(teacher)
        db.session.commit()
        return teacher
    
    def update(self, teacher_id: str, update_data: dict) -> Optional[Teacher]:
        """
        Update an existing teacher.
        
        Args:
            teacher_id: Teacher ID
            update_data: Dictionary with fields to update
            
        Returns:
            Updated Teacher or None if not found
        """
        teacher = self.get_by_id(teacher_id)
        if not teacher:
            return None
        
        for key, value in update_data.items():
            if hasattr(teacher, key):
                setattr(teacher, key, value)
        
        db.session.commit()
        return teacher
    
    def delete(self, teacher_id: str) -> bool:
        """
        Delete a teacher (hard delete).
        
        Args:
            teacher_id: Teacher ID
            
        Returns:
            bool: True if deleted, False if not found
        """
        teacher = self.get_by_id(teacher_id)
        if not teacher:
            return False
        
        db.session.delete(teacher)
        db.session.commit()
        return True
    
    def is_wali_kelas(self, teacher_id: str) -> bool:
        """
        Check if teacher is assigned as wali kelas for any class.
        
        Args:
            teacher_id: Teacher ID
            
        Returns:
            bool: True if assigned as wali kelas
        """
        count = db.session.query(func.count(Class.class_id)).filter(
            Class.wali_kelas_id == teacher_id
        ).scalar()
        
        return (count or 0) > 0


# Singleton instance
teacher_repository = TeacherRepository()
