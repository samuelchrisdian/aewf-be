"""
Master Data Seeder - Seeds Teachers, Classes, and Students.
"""
from typing import Dict, Any
from src.seeders.base_seeder import BaseSeeder
from src.domain.models import Teacher, Class, Student


class MasterSeeder(BaseSeeder):
    """
    Seeds school master data including:
    - 5 Teachers (3 wali kelas + 2 subject teachers)
    - 3 Classes (9A, 9B, 9C)
    - 30 Students (10 per class)
    """
    
    # Teacher data
    TEACHERS = [
        {'teacher_id': 'TCH_BUDI', 'name': 'Budi Santoso', 'role': 'Wali Kelas'},
        {'teacher_id': 'TCH_SITI', 'name': 'Siti Aminah', 'role': 'Wali Kelas'},
        {'teacher_id': 'TCH_AHMAD', 'name': 'Ahmad Hidayat', 'role': 'Wali Kelas'},
        {'teacher_id': 'TCH_DEWI', 'name': 'Dewi Lestari', 'role': 'Subject Teacher'},
        {'teacher_id': 'TCH_RUDI', 'name': 'Rudi Hermawan', 'role': 'Subject Teacher'},
    ]
    
    # Class data
    CLASSES = [
        {'class_id': 'CLASS_9A', 'class_name': '9A', 'wali_kelas_id': 'TCH_BUDI'},
        {'class_id': 'CLASS_9B', 'class_name': '9B', 'wali_kelas_id': 'TCH_SITI'},
        {'class_id': 'CLASS_9C', 'class_name': '9C', 'wali_kelas_id': 'TCH_AHMAD'},
    ]
    
    # Student data - Class 9A (NIS 2024001-2024010)
    STUDENTS_9A = [
        {'nis': '2024001', 'name': 'Shem Hearing', 'class_id': 'CLASS_9A', 'parent_phone': '081234567001'},
        {'nis': '2024002', 'name': 'Graciela Putri', 'class_id': 'CLASS_9A', 'parent_phone': '081234567002'},
        {'nis': '2024003', 'name': 'Ahmad Rizki', 'class_id': 'CLASS_9A', 'parent_phone': '081234567003'},
        {'nis': '2024004', 'name': 'Bella Safira', 'class_id': 'CLASS_9A', 'parent_phone': '081234567004'},
        {'nis': '2024005', 'name': 'Cindy Maharani', 'class_id': 'CLASS_9A', 'parent_phone': '081234567005'},
        {'nis': '2024006', 'name': 'Dimas Prasetyo', 'class_id': 'CLASS_9A', 'parent_phone': '081234567006'},
        {'nis': '2024007', 'name': 'Elsa Damayanti', 'class_id': 'CLASS_9A', 'parent_phone': '081234567007'},
        {'nis': '2024008', 'name': 'Fahri Kurniawan', 'class_id': 'CLASS_9A', 'parent_phone': '081234567008'},
        {'nis': '2024009', 'name': 'Gita Permata', 'class_id': 'CLASS_9A', 'parent_phone': '081234567009'},
        {'nis': '2024010', 'name': 'Hendra Wijaya', 'class_id': 'CLASS_9A', 'parent_phone': '081234567010'},
    ]
    
    # Student data - Class 9B (NIS 2024011-2024020)
    STUDENTS_9B = [
        {'nis': '2024011', 'name': 'Indra Permana', 'class_id': 'CLASS_9B', 'parent_phone': '081234567011'},
        {'nis': '2024012', 'name': 'Jasmine Oktavia', 'class_id': 'CLASS_9B', 'parent_phone': '081234567012'},
        {'nis': '2024013', 'name': 'Kevin Pratama', 'class_id': 'CLASS_9B', 'parent_phone': '081234567013'},
        {'nis': '2024014', 'name': 'Linda Wulandari', 'class_id': 'CLASS_9B', 'parent_phone': '081234567014'},
        {'nis': '2024015', 'name': 'Michael Santoso', 'class_id': 'CLASS_9B', 'parent_phone': '081234567015'},
        {'nis': '2024016', 'name': 'Nabila Azzahra', 'class_id': 'CLASS_9B', 'parent_phone': '081234567016'},
        {'nis': '2024017', 'name': 'Oscar Wirawan', 'class_id': 'CLASS_9B', 'parent_phone': '081234567017'},
        {'nis': '2024018', 'name': 'Patricia Dewi', 'class_id': 'CLASS_9B', 'parent_phone': '081234567018'},
        {'nis': '2024019', 'name': 'Qiana Rahma', 'class_id': 'CLASS_9B', 'parent_phone': '081234567019'},
        {'nis': '2024020', 'name': 'Rizky Hidayat', 'class_id': 'CLASS_9B', 'parent_phone': '081234567020'},
    ]
    
    # Student data - Class 9C (NIS 2024021-2024030)
    STUDENTS_9C = [
        {'nis': '2024021', 'name': 'Sari Indah', 'class_id': 'CLASS_9C', 'parent_phone': '081234567021'},
        {'nis': '2024022', 'name': 'Taufik Rahman', 'class_id': 'CLASS_9C', 'parent_phone': '081234567022'},
        {'nis': '2024023', 'name': 'Umi Kalsum', 'class_id': 'CLASS_9C', 'parent_phone': '081234567023'},
        {'nis': '2024024', 'name': 'Vino Bastian', 'class_id': 'CLASS_9C', 'parent_phone': '081234567024'},
        {'nis': '2024025', 'name': 'Winda Sari', 'class_id': 'CLASS_9C', 'parent_phone': '081234567025'},
        {'nis': '2024026', 'name': 'Xander Putra', 'class_id': 'CLASS_9C', 'parent_phone': '081234567026'},
        {'nis': '2024027', 'name': 'Yolanda Fitri', 'class_id': 'CLASS_9C', 'parent_phone': '081234567027'},
        {'nis': '2024028', 'name': 'Zainal Abidin', 'class_id': 'CLASS_9C', 'parent_phone': '081234567028'},
        {'nis': '2024029', 'name': 'Agung Prasetya', 'class_id': 'CLASS_9C', 'parent_phone': '081234567029'},
        {'nis': '2024030', 'name': 'Bunga Citra', 'class_id': 'CLASS_9C', 'parent_phone': '081234567030'},
    ]
    
    def clear_data(self) -> int:
        """Clear all master data tables (respecting FK order)."""
        deleted = 0
        
        try:
            # Delete in reverse FK order
            deleted += self.db.query(Student).delete()
            deleted += self.db.query(Class).delete()
            deleted += self.db.query(Teacher).delete()
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Warning: Could not clear tables (may not exist): {e}")
        
        return deleted
    
    def seed(self) -> Dict[str, Any]:
        """Seed teachers, classes, and students."""
        result = {'teachers': 0, 'classes': 0, 'students': 0}
        
        # Seed teachers
        for t_data in self.TEACHERS:
            teacher = Teacher(**t_data)
            self.db.add(teacher)
            result['teachers'] += 1
        
        self.db.flush()
        
        # Seed classes
        for c_data in self.CLASSES:
            class_obj = Class(**c_data)
            self.db.add(class_obj)
            result['classes'] += 1
        
        self.db.flush()
        
        # Seed students
        all_students = self.STUDENTS_9A + self.STUDENTS_9B + self.STUDENTS_9C
        for s_data in all_students:
            student = Student(**s_data)
            self.db.add(student)
            result['students'] += 1
        
        self.db.commit()
        return result
    
    @classmethod
    def get_all_students(cls):
        """Get all student data for reference by other seeders."""
        return cls.STUDENTS_9A + cls.STUDENTS_9B + cls.STUDENTS_9C
