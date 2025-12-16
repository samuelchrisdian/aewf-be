"""
Machine Seeder - Seeds Machine and MachineUser data with variations.
"""
from typing import Dict, Any, List
from src.seeders.base_seeder import BaseSeeder
from src.seeders.master_seeder import MasterSeeder
from src.domain.models import Machine, MachineUser, StudentMachineMap


class MachineSeeder(BaseSeeder):
    """
    Seeds machine data including:
    - 1 Machine (MAIN_GATE)
    - 40 MachineUsers:
        - 20 perfect matches (exact student names)
        - 10 typo/variation matches (for fuzzy testing)
        - 10 unmapped users (staff/guests)
    """
    
    # Machine data
    MACHINE = {
        'machine_code': 'MAIN_GATE',
        'location': 'Main Entrance Gate'
    }
    
    # Category B: Typo/Variation matches (student_name -> machine_name)
    # These should trigger fuzzy matching with 85-95% confidence
    TYPO_VARIATIONS = [
        ('Shem Hearing', 'Shem'),              # Missing last name
        ('Graciela Putri', 'Graciella Putri'),  # Typo
        ('Ahmad Rizki', 'Ahmad Riski'),         # Different spelling
        ('Bella Safira', 'Bella Safirah'),      # Extra 'h'
        ('Cindy Maharani', 'Cindi Maharani'),   # y→i
        ('Dimas Prasetyo', 'Dimas Prasetio'),   # y→i
        ('Elsa Damayanti', 'Elsa Damayati'),    # Missing 'n'
        ('Fahri Kurniawan', 'Fahri Kurniwan'),  # Missing 'a'
        ('Gita Permata', 'Gita P'),             # Abbreviated
        ('Hendra Wijaya', 'Hendra W'),          # Abbreviated
    ]
    
    # Category C: Unmapped users (staff, teachers, guests)
    UNMAPPED_USERS = [
        {'name': 'Pak Security Anton', 'department': 'Security'},
        {'name': 'Bu Kantin Erna', 'department': 'Cafeteria'},
        {'name': 'Cleaning Service Joko', 'department': 'Maintenance'},
        {'name': 'IT Support Rahmat', 'department': 'IT'},
        {'name': 'Library Staff Nurul', 'department': 'Library'},
        {'name': 'School Guard Bambang', 'department': 'Security'},
        {'name': 'Cafeteria Staff Wati', 'department': 'Cafeteria'},
        {'name': 'Maintenance Agus', 'department': 'Maintenance'},
        {'name': 'Driver Pak Yanto', 'department': 'Transport'},
        {'name': 'Guest Visitor 001', 'department': 'Guest'},
    ]
    
    def clear_data(self) -> int:
        """Clear machine-related tables (respecting FK order)."""
        deleted = 0
        
        try:
            # Delete in reverse FK order
            deleted += self.db.query(StudentMachineMap).delete()
            deleted += self.db.query(MachineUser).delete()
            deleted += self.db.query(Machine).delete()
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Warning: Could not clear tables (may not exist): {e}")
        
        return deleted
    
    def seed(self) -> Dict[str, Any]:
        """Seed machine and machine users."""
        result = {
            'machines': 0, 
            'machine_users': 0,
            'perfect_matches': 0,
            'typo_matches': 0,
            'unmapped': 0
        }
        
        # Create machine
        machine = Machine(**self.MACHINE)
        self.db.add(machine)
        self.db.flush()  # Get the machine ID
        result['machines'] = 1
        
        user_id_counter = 195  # Starting user ID as per spec
        
        # Category A: Perfect matches (students 11-30 only, skip first 10 for typo matches)
        all_students = MasterSeeder.get_all_students()
        typo_student_names = [t[0] for t in self.TYPO_VARIATIONS]
        
        for student in all_students:
            if student['name'] not in typo_student_names:
                # Perfect match - exact name
                machine_user = MachineUser(
                    machine_id=machine.id,
                    machine_user_id=str(user_id_counter),
                    machine_user_name=student['name'],  # Exact match
                    department='Student'
                )
                self.db.add(machine_user)
                user_id_counter += 1
                result['perfect_matches'] += 1
                result['machine_users'] += 1
        
        # Category B: Typo/variation matches
        for student_name, machine_name in self.TYPO_VARIATIONS:
            machine_user = MachineUser(
                machine_id=machine.id,
                machine_user_id=str(user_id_counter),
                machine_user_name=machine_name,  # Variation/typo
                department='Student'
            )
            self.db.add(machine_user)
            user_id_counter += 1
            result['typo_matches'] += 1
            result['machine_users'] += 1
        
        # Category C: Unmapped users
        for staff in self.UNMAPPED_USERS:
            machine_user = MachineUser(
                machine_id=machine.id,
                machine_user_id=str(user_id_counter),
                machine_user_name=staff['name'],
                department=staff['department']
            )
            self.db.add(machine_user)
            user_id_counter += 1
            result['unmapped'] += 1
            result['machine_users'] += 1
        
        self.db.commit()
        return result
    
    @classmethod
    def get_typo_variations(cls) -> List[tuple]:
        """Get typo variations for reference by mapping seeder."""
        return cls.TYPO_VARIATIONS
