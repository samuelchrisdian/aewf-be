"""
Attendance Seeder - Seeds AttendanceRawLog and ImportBatch data.
"""
import random
import json
from datetime import datetime, timedelta
from typing import Dict, Any
from src.seeders.base_seeder import BaseSeeder
from src.domain.models import ImportBatch, AttendanceRawLog, MachineUser


class AttendanceSeeder(BaseSeeder):
    """
    Seeds attendance data including:
    - 14 ImportBatches (one per day for last 14 days)
    - ~600 AttendanceRawLogs with realistic patterns:
        - 90% on-time check-ins (07:15-07:45)
        - 10% late check-ins (07:45-08:30)
        - 5% absent students (no logs)
        - Random check-out patterns
    """
    
    DAYS_TO_SEED = 14
    
    def clear_data(self) -> int:
        """Clear attendance-related tables."""
        deleted = 0
        
        try:
            # Delete in reverse FK order
            deleted += self.db.query(AttendanceRawLog).delete()
            deleted += self.db.query(ImportBatch).delete()
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Warning: Could not clear tables (may not exist): {e}")
        
        return deleted
    
    def _generate_checkin_time(self, base_date: datetime) -> datetime:
        """
        Generate check-in time with realistic distribution.
        90% on-time (07:15-07:45), 10% late (07:45-08:30)
        """
        if random.random() < 0.9:
            # On-time: 07:15 - 07:45
            minutes = random.randint(15, 45)
        else:
            # Late: 07:45 - 08:30
            minutes = random.randint(45, 90)
        
        return base_date.replace(hour=7, minute=0, second=0, microsecond=0) + timedelta(minutes=minutes)
    
    def _generate_checkout_time(self, base_date: datetime) -> datetime:
        """
        Generate check-out time.
        Time range: 14:30 - 15:00
        """
        minutes = random.randint(30, 60)
        return base_date.replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(minutes=minutes)
    
    def _generate_staff_time(self, base_date: datetime) -> datetime:
        """Generate random scan time for staff throughout the day."""
        hour = random.randint(6, 18)
        minute = random.randint(0, 59)
        return base_date.replace(hour=hour, minute=minute, second=random.randint(0, 59), microsecond=0)
    
    def seed(self) -> Dict[str, Any]:
        """Seed import batches and attendance raw logs."""
        result = {'batches': 0, 'logs': 0}
        
        # Get all machine users
        machine_users = self.db.query(MachineUser).all()
        if not machine_users:
            return result
        
        # Separate students and staff
        student_users = [u for u in machine_users if u.department == 'Student']
        staff_users = [u for u in machine_users if u.department != 'Student']
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for day_offset in range(self.DAYS_TO_SEED, 0, -1):
            current_date = today - timedelta(days=day_offset)
            
            # Skip weekends
            if current_date.weekday() >= 5:
                continue
            
            # Create import batch for this day
            batch = ImportBatch(
                filename=f"auto_seeded_{current_date.strftime('%Y-%m-%d')}.xls",
                file_type='attendance_logs',
                status='completed',
                created_at=current_date.replace(hour=8, minute=0),
                records_processed=0
            )
            self.db.add(batch)
            self.db.flush()  # Get batch ID
            result['batches'] += 1
            
            logs_for_day = 0
            
            # Generate logs for student users
            for user in student_users:
                # 5% chance of being completely absent
                if random.random() < 0.05:
                    continue
                
                # Check-in log
                checkin_time = self._generate_checkin_time(current_date)
                raw_data = {
                    'ID': user.machine_user_id,
                    'Name': user.machine_user_name,
                    'DateTime': checkin_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'Device': 'MAIN_GATE',
                }
                
                checkin_log = AttendanceRawLog(
                    batch_id=batch.id,
                    machine_user_id_fk=user.id,
                    event_time=checkin_time,
                    raw_data=raw_data
                )
                self.db.add(checkin_log)
                result['logs'] += 1
                logs_for_day += 1
                
                # 85% chance of checkout (15% forget to scan out)
                if random.random() < 0.85:
                    checkout_time = self._generate_checkout_time(current_date)
                    raw_data_out = {
                        'ID': user.machine_user_id,
                        'Name': user.machine_user_name,
                        'DateTime': checkout_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'Device': 'MAIN_GATE',
                    }
                    
                    checkout_log = AttendanceRawLog(
                        batch_id=batch.id,
                        machine_user_id_fk=user.id,
                        event_time=checkout_time,
                        raw_data=raw_data_out
                    )
                    self.db.add(checkout_log)
                    result['logs'] += 1
                    logs_for_day += 1
            
            # Generate random logs for staff (1-3 scans per day)
            for user in staff_users:
                num_scans = random.randint(1, 3)
                for _ in range(num_scans):
                    scan_time = self._generate_staff_time(current_date)
                    raw_data = {
                        'ID': user.machine_user_id,
                        'Name': user.machine_user_name,
                        'DateTime': scan_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'Device': 'MAIN_GATE',
                    }
                    
                    log = AttendanceRawLog(
                        batch_id=batch.id,
                        machine_user_id_fk=user.id,
                        event_time=scan_time,
                        raw_data=raw_data
                    )
                    self.db.add(log)
                    result['logs'] += 1
                    logs_for_day += 1
            
            # Update batch with processed count
            batch.records_processed = logs_for_day
        
        self.db.commit()
        return result
