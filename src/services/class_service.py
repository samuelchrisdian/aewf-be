"""
Class service for business logic.
Handles all business operations for Class entity.
"""
from typing import Optional, Tuple, List
from marshmallow import ValidationError
from sqlalchemy import func

from src.repositories.class_repo import class_repository
from src.repositories.teacher_repo import teacher_repository
from src.domain.models import AttendanceDaily, Student
from src.app.extensions import db
from src.schemas.class_schema import (
    class_create_schema,
    class_update_schema
)


class ClassService:
    """Service class for Class business logic."""
    
    def __init__(self):
        self.repository = class_repository
    
    def get_classes(self) -> List[dict]:
        """
        Get all classes with student count and wali kelas info.
        
        Returns:
            List of class data dicts
        """
        results = self.repository.get_all_with_student_count()
        
        classes_data = []
        for item in results:
            cls = item["class"]
            class_dict = {
                "class_id": cls.class_id,
                "class_name": cls.class_name,
                "wali_kelas_id": cls.wali_kelas_id,
                "wali_kelas_name": cls.wali_kelas.name if cls.wali_kelas else None,
                "student_count": item["student_count"]
            }
            classes_data.append(class_dict)
        
        return classes_data
    
    def get_class(self, class_id: str) -> Tuple[Optional[dict], Optional[str]]:
        """
        Get a single class with full details.
        
        Args:
            class_id: Class ID
            
        Returns:
            Tuple: (class_data, error_message)
        """
        cls = self.repository.get_by_id(class_id)
        if not cls:
            return None, "Class not found"
        
        # Get student count
        student_count = self.repository.get_student_count(class_id)
        
        # Calculate attendance stats
        attendance_stats = self._calculate_attendance_stats(class_id)
        
        # Build wali kelas info
        wali_kelas = None
        if cls.wali_kelas:
            wali_kelas = {
                "teacher_id": cls.wali_kelas.teacher_id,
                "name": cls.wali_kelas.name,
                "phone": getattr(cls.wali_kelas, 'phone', None)
            }
        
        class_data = {
            "class_id": cls.class_id,
            "class_name": cls.class_name,
            "wali_kelas": wali_kelas,
            "student_count": student_count,
            "attendance_stats": attendance_stats
        }
        
        return class_data, None
    
    def create_class(self, data: dict) -> Tuple[Optional[dict], Optional[dict]]:
        """
        Create a new class.
        
        Args:
            data: Class data from request
            
        Returns:
            Tuple: (created_class, validation_errors)
        """
        # Validate input
        try:
            validated_data = class_create_schema.load(data)
        except ValidationError as err:
            return None, err.messages
        
        # Check if class_id already exists
        if self.repository.exists(validated_data['class_id']):
            return None, {"class_id": ["Class with this ID already exists"]}
        
        # Check if wali_kelas exists (if provided)
        if validated_data.get('wali_kelas_id'):
            if not teacher_repository.exists(validated_data['wali_kelas_id']):
                return None, {"wali_kelas_id": ["Teacher not found"]}
        
        # Create class
        cls = self.repository.create(validated_data)
        
        # Serialize response
        class_data = {
            "class_id": cls.class_id,
            "class_name": cls.class_name,
            "wali_kelas_id": cls.wali_kelas_id,
            "wali_kelas_name": cls.wali_kelas.name if cls.wali_kelas else None,
            "student_count": 0
        }
        
        return class_data, None
    
    def update_class(self, class_id: str, data: dict) -> Tuple[Optional[dict], Optional[dict]]:
        """
        Update an existing class.
        
        Args:
            class_id: Class ID
            data: Update data from request
            
        Returns:
            Tuple: (updated_class, validation_errors)
        """
        # Check if class exists
        if not self.repository.exists(class_id):
            return None, {"class_id": ["Class not found"]}
        
        # Validate input
        try:
            validated_data = class_update_schema.load(data)
        except ValidationError as err:
            return None, err.messages
        
        # Check if wali_kelas exists (if being updated)
        if 'wali_kelas_id' in validated_data and validated_data['wali_kelas_id']:
            if not teacher_repository.exists(validated_data['wali_kelas_id']):
                return None, {"wali_kelas_id": ["Teacher not found"]}
        
        # Update class
        cls = self.repository.update(class_id, validated_data)
        
        # Get student count
        student_count = self.repository.get_student_count(class_id)
        
        # Serialize response
        class_data = {
            "class_id": cls.class_id,
            "class_name": cls.class_name,
            "wali_kelas_id": cls.wali_kelas_id,
            "wali_kelas_name": cls.wali_kelas.name if cls.wali_kelas else None,
            "student_count": student_count
        }
        
        return class_data, None
    
    def delete_class(self, class_id: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a class.
        Cannot delete if has active students.
        
        Args:
            class_id: Class ID
            
        Returns:
            Tuple: (success, error_message)
        """
        if not self.repository.exists(class_id):
            return False, "Class not found"
        
        # Check for active students
        if self.repository.has_active_students(class_id):
            return False, "Cannot delete class with active students"
        
        self.repository.delete(class_id)
        return True, None
    
    def _calculate_attendance_stats(self, class_id: str) -> dict:
        """
        Calculate attendance statistics for a class.
        
        Args:
            class_id: Class ID
            
        Returns:
            dict: {average_rate, at_risk_students}
        """
        # Get all active students in this class
        students = db.session.query(Student).filter(
            Student.class_id == class_id,
            Student.is_active == True
        ).all()
        
        if not students:
            return {
                "average_rate": 0.0,
                "at_risk_students": 0
            }
        
        student_nis_list = [s.nis for s in students]
        
        # Get attendance records for these students
        total_records = 0
        total_attended = 0
        at_risk_count = 0
        
        for nis in student_nis_list:
            records = db.session.query(AttendanceDaily).filter(
                AttendanceDaily.student_nis == nis
            ).all()
            
            if not records:
                continue
            
            total = len(records)
            attended = sum(1 for r in records if r.status in ['Present', 'Late'])
            
            total_records += total
            total_attended += attended
            
            # Consider at-risk if attendance rate < 85%
            rate = (attended / total * 100) if total > 0 else 0
            if rate < 85:
                at_risk_count += 1
        
        average_rate = round((total_attended / total_records * 100), 1) if total_records > 0 else 0.0
        
        return {
            "average_rate": average_rate,
            "at_risk_students": at_risk_count
        }


# Singleton instance
class_service = ClassService()
