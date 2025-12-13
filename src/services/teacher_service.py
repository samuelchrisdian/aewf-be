"""
Teacher service for business logic.
Handles all business operations for Teacher entity.
"""
from typing import Optional, Tuple, List
from marshmallow import ValidationError

from src.repositories.teacher_repo import teacher_repository
from src.schemas.teacher_schema import (
    teacher_create_schema,
    teacher_update_schema
)


class TeacherService:
    """Service class for Teacher business logic."""
    
    def __init__(self):
        self.repository = teacher_repository
    
    def get_teachers(self, role_filter: Optional[str] = None) -> List[dict]:
        """
        Get all teachers with optional role filter.
        
        Args:
            role_filter: Filter by role (e.g., "Wali Kelas")
            
        Returns:
            List of teacher data dicts
        """
        query = self.repository.get_all(role_filter=role_filter)
        teachers = query.all()
        
        teachers_data = []
        for teacher in teachers:
            teacher_dict = {
                "teacher_id": teacher.teacher_id,
                "name": teacher.name,
                "role": teacher.role,
                "phone": getattr(teacher, 'phone', None)
            }
            teachers_data.append(teacher_dict)
        
        return teachers_data
    
    def get_teacher(self, teacher_id: str) -> Tuple[Optional[dict], Optional[str]]:
        """
        Get a single teacher with classes they manage.
        
        Args:
            teacher_id: Teacher ID
            
        Returns:
            Tuple: (teacher_data, error_message)
        """
        teacher = self.repository.get_by_id(teacher_id)
        if not teacher:
            return None, "Teacher not found"
        
        # Get classes with student count
        classes = self.repository.get_classes_with_student_count(teacher_id)
        
        teacher_data = {
            "teacher_id": teacher.teacher_id,
            "name": teacher.name,
            "role": teacher.role,
            "phone": getattr(teacher, 'phone', None),
            "classes": classes
        }
        
        return teacher_data, None
    
    def create_teacher(self, data: dict) -> Tuple[Optional[dict], Optional[dict]]:
        """
        Create a new teacher.
        
        Args:
            data: Teacher data from request
            
        Returns:
            Tuple: (created_teacher, validation_errors)
        """
        # Validate input
        try:
            validated_data = teacher_create_schema.load(data)
        except ValidationError as err:
            return None, err.messages
        
        # Check if teacher_id already exists
        if self.repository.exists(validated_data['teacher_id']):
            return None, {"teacher_id": ["Teacher with this ID already exists"]}
        
        # Create teacher
        teacher = self.repository.create(validated_data)
        
        # Serialize response
        teacher_data = {
            "teacher_id": teacher.teacher_id,
            "name": teacher.name,
            "role": teacher.role,
            "phone": getattr(teacher, 'phone', None)
        }
        
        return teacher_data, None
    
    def update_teacher(self, teacher_id: str, data: dict) -> Tuple[Optional[dict], Optional[dict]]:
        """
        Update an existing teacher.
        
        Args:
            teacher_id: Teacher ID
            data: Update data from request
            
        Returns:
            Tuple: (updated_teacher, validation_errors)
        """
        # Check if teacher exists
        if not self.repository.exists(teacher_id):
            return None, {"teacher_id": ["Teacher not found"]}
        
        # Validate input
        try:
            validated_data = teacher_update_schema.load(data)
        except ValidationError as err:
            return None, err.messages
        
        # Update teacher
        teacher = self.repository.update(teacher_id, validated_data)
        
        # Serialize response
        teacher_data = {
            "teacher_id": teacher.teacher_id,
            "name": teacher.name,
            "role": teacher.role,
            "phone": getattr(teacher, 'phone', None)
        }
        
        return teacher_data, None
    
    def delete_teacher(self, teacher_id: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a teacher.
        Cannot delete if assigned as wali kelas.
        
        Args:
            teacher_id: Teacher ID
            
        Returns:
            Tuple: (success, error_message)
        """
        if not self.repository.exists(teacher_id):
            return False, "Teacher not found"
        
        # Check if assigned as wali kelas
        if self.repository.is_wali_kelas(teacher_id):
            return False, "Cannot delete teacher who is assigned as wali kelas"
        
        self.repository.delete(teacher_id)
        return True, None


# Singleton instance
teacher_service = TeacherService()
