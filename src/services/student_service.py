"""
Student service for business logic.
Handles all business operations for Student entity.
"""
from typing import Optional, Tuple, Any
from marshmallow import ValidationError

from src.repositories.student_repo import student_repository
from src.repositories.class_repo import class_repository
from src.schemas.student_schema import (
    student_create_schema,
    student_update_schema,
    student_schema,
    student_list_schema
)
from src.utils.pagination import paginate
from src.utils.validators import validate_phone_format


class StudentService:
    """Service class for Student business logic."""
    
    def __init__(self):
        self.repository = student_repository
    
    def get_students(
        self,
        page: int = 1,
        per_page: int = 20,
        class_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        order: str = 'asc'
    ) -> dict:
        """
        Get paginated list of students with filters.
        
        Args:
            page: Page number
            per_page: Items per page
            class_id: Filter by class ID
            is_active: Filter by active status
            search: Search by name/NIS
            sort_by: Sort field
            order: Sort order
            
        Returns:
            dict: {
                "data": [serialized students],
                "pagination": {...}
            }
        """
        # Validate sort field
        allowed_sort_fields = ['name', 'nis', 'class_id']
        if sort_by and sort_by not in allowed_sort_fields:
            sort_by = 'name'
        
        # Get query with filters
        query = self.repository.get_all(
            class_id=class_id,
            is_active=is_active,
            search=search,
            sort_by=sort_by,
            order=order
        )
        
        # Paginate
        result = paginate(query, page, per_page)
        
        # Serialize students with class name
        students_data = []
        for student in result["items"]:
            student_dict = {
                "nis": student.nis,
                "name": student.name,
                "class_id": student.class_id,
                "class_name": student.student_class.class_name if student.student_class else None,
                "parent_phone": student.parent_phone,
                "is_active": student.is_active
            }
            students_data.append(student_dict)
        
        return {
            "data": students_data,
            "pagination": result["pagination"]
        }
    
    def get_student(self, nis: str) -> Tuple[Optional[dict], Optional[str]]:
        """
        Get a single student with full details and attendance summary.
        
        Args:
            nis: Student NIS
            
        Returns:
            Tuple: (student_data, error_message)
        """
        student = self.repository.get_by_nis(nis)
        if not student:
            return None, "Student not found"
        
        # Get attendance summary
        attendance_summary = self.repository.get_attendance_summary(nis)
        
        # Serialize
        student_data = {
            "nis": student.nis,
            "name": student.name,
            "class_id": student.class_id,
            "class_name": student.student_class.class_name if student.student_class else None,
            "parent_phone": student.parent_phone,
            "is_active": student.is_active,
            "attendance_summary": attendance_summary
        }
        
        return student_data, None
    
    def create_student(self, data: dict) -> Tuple[Optional[dict], Optional[dict]]:
        """
        Create a new student.
        
        Args:
            data: Student data from request
            
        Returns:
            Tuple: (created_student, validation_errors)
        """
        # Validate input
        try:
            validated_data = student_create_schema.load(data)
        except ValidationError as err:
            return None, err.messages
        
        # Check if NIS already exists
        if self.repository.exists(validated_data['nis']):
            return None, {"nis": ["Student with this NIS already exists"]}
        
        # Check if class exists
        if not class_repository.exists(validated_data['class_id']):
            return None, {"class_id": ["Class not found"]}
        
        # Validate phone format if provided
        if validated_data.get('parent_phone'):
            if not validate_phone_format(validated_data['parent_phone']):
                return None, {"parent_phone": ["Invalid phone number format"]}
        
        # Create student
        student = self.repository.create(validated_data)
        
        # Serialize response
        student_data = {
            "nis": student.nis,
            "name": student.name,
            "class_id": student.class_id,
            "class_name": student.student_class.class_name if student.student_class else None,
            "parent_phone": student.parent_phone,
            "is_active": student.is_active
        }
        
        return student_data, None
    
    def update_student(self, nis: str, data: dict) -> Tuple[Optional[dict], Optional[dict]]:
        """
        Update an existing student.
        
        Args:
            nis: Student NIS
            data: Update data from request
            
        Returns:
            Tuple: (updated_student, validation_errors)
        """
        # Check if student exists
        if not self.repository.exists(nis):
            return None, {"nis": ["Student not found"]}
        
        # Validate input
        try:
            validated_data = student_update_schema.load(data)
        except ValidationError as err:
            return None, err.messages
        
        # Check if class exists (if being updated)
        if 'class_id' in validated_data:
            if not class_repository.exists(validated_data['class_id']):
                return None, {"class_id": ["Class not found"]}
        
        # Validate phone format if provided
        if validated_data.get('parent_phone'):
            if not validate_phone_format(validated_data['parent_phone']):
                return None, {"parent_phone": ["Invalid phone number format"]}
        
        # Update student
        student = self.repository.update(nis, validated_data)
        
        # Serialize response
        student_data = {
            "nis": student.nis,
            "name": student.name,
            "class_id": student.class_id,
            "class_name": student.student_class.class_name if student.student_class else None,
            "parent_phone": student.parent_phone,
            "is_active": student.is_active
        }
        
        return student_data, None
    
    def delete_student(self, nis: str) -> Tuple[bool, Optional[str]]:
        """
        Soft delete a student.
        
        Args:
            nis: Student NIS
            
        Returns:
            Tuple: (success, error_message)
        """
        if not self.repository.exists(nis):
            return False, "Student not found"
        
        self.repository.soft_delete(nis)
        return True, None


# Singleton instance
student_service = StudentService()
