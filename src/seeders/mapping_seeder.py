"""
Mapping Seeder - Pre-generates StudentMachineMap suggestions.
"""
from datetime import datetime
from typing import Dict, Any
from thefuzz import fuzz
from src.seeders.base_seeder import BaseSeeder
from src.seeders.master_seeder import MasterSeeder
from src.seeders.machine_seeder import MachineSeeder
from src.domain.models import StudentMachineMap, MachineUser, Student


class MappingSeeder(BaseSeeder):
    """
    Pre-generates mapping suggestions:
    - Category A (perfect matches): status='verified', score=100
    - Category B (typo matches): status='suggested', score=85-95
    - Category C (unmapped): No mapping records
    """
    
    def clear_data(self) -> int:
        """Clear mapping table."""
        deleted = 0
        
        try:
            deleted = self.db.query(StudentMachineMap).delete()
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Warning: Could not clear tables (may not exist): {e}")
        
        return deleted
    
    def _calculate_confidence(self, machine_name: str, student_name: str) -> int:
        """Calculate fuzzy match confidence score."""
        return fuzz.token_sort_ratio(machine_name.lower(), student_name.lower())
    
    def _find_student_by_name(self, name: str) -> Student:
        """Find a student by exact name match."""
        return self.db.query(Student).filter(Student.name == name).first()
    
    def _find_best_match(self, machine_name: str, students: list) -> tuple:
        """Find the best matching student for a machine user name."""
        best_student = None
        best_score = 0
        
        for student in students:
            score = self._calculate_confidence(machine_name, student.name)
            if score > best_score:
                best_score = score
                best_student = student
        
        return best_student, best_score
    
    def seed(self) -> Dict[str, Any]:
        """Seed mapping suggestions."""
        result = {'verified': 0, 'suggested': 0, 'total': 0}
        
        # Get all machine users and students
        machine_users = self.db.query(MachineUser).filter(
            MachineUser.department == 'Student'
        ).all()
        students = self.db.query(Student).all()
        
        if not machine_users or not students:
            return result
        
        # Get typo variations for reference
        typo_variations = MachineSeeder.get_typo_variations()
        typo_machine_names = [t[1] for t in typo_variations]
        
        # Create a dict for quick student lookup by name
        student_by_name = {s.name: s for s in students}
        
        for machine_user in machine_users:
            machine_name = machine_user.machine_user_name
            
            # Check if this is a perfect match (Category A)
            if machine_name in student_by_name:
                student = student_by_name[machine_name]
                mapping = StudentMachineMap(
                    machine_user_id_fk=machine_user.id,
                    student_nis=student.nis,
                    status='verified',
                    confidence_score=100,
                    verified_at=datetime.utcnow(),
                    verified_by='system_seed'
                )
                self.db.add(mapping)
                result['verified'] += 1
                result['total'] += 1
            
            # Check if this is a typo match (Category B)
            elif machine_name in typo_machine_names:
                # Find the original student name from variations
                for student_name, typo_name in typo_variations:
                    if typo_name == machine_name:
                        student = student_by_name.get(student_name)
                        if student:
                            score = self._calculate_confidence(machine_name, student.name)
                            mapping = StudentMachineMap(
                                machine_user_id_fk=machine_user.id,
                                student_nis=student.nis,
                                status='suggested',
                                confidence_score=score,
                                verified_at=None,
                                verified_by=None
                            )
                            self.db.add(mapping)
                            result['suggested'] += 1
                            result['total'] += 1
                        break
            
            # Category C (unmapped) - no mapping created
        
        self.db.commit()
        return result
