"""
Machine service for business logic operations.
Handles CRUD operations and data processing for machines.
"""
import pandas as pd
from typing import Optional, Tuple, List
from src.app.extensions import db
from src.domain.models import Machine, MachineUser, StudentMachineMap
from src.repositories.machine_repo import machine_repository
from src.schemas.machine_schema import (
    machine_create_schema,
    machine_update_schema
)
from src.utils.pagination import paginate_query
import datetime
import logging

logger = logging.getLogger(__name__)


class MachineService:
    """Service class for Machine business logic."""
    
    def __init__(self):
        self.repository = machine_repository
    
    def get_machines(
        self,
        page: int = 1,
        per_page: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        order: str = 'asc'
    ) -> dict:
        """
        Get paginated list of machines with user counts.
        
        Args:
            page: Page number
            per_page: Items per page
            status: Filter by status
            search: Search by machine_code or location
            sort_by: Field to sort by
            order: Sort order
            
        Returns:
            dict: Paginated machines with data and pagination info
        """
        query = self.repository.get_all(
            status=status,
            search=search,
            sort_by=sort_by,
            order=order
        )
        
        # Paginate
        result = paginate_query(query, page, per_page)
        
        # Add user counts to each machine
        machines_data = []
        for machine in result["data"]:
            machines_data.append(self._serialize_machine(machine))
        
        result["data"] = machines_data
        return result
    
    def get_machine(self, machine_id: int) -> Tuple[Optional[dict], Optional[str]]:
        """
        Get a single machine by ID with details.
        
        Args:
            machine_id: Machine ID
            
        Returns:
            Tuple of (machine_data, error_message)
        """
        machine = self.repository.get_by_id(machine_id)
        if not machine:
            return None, "Machine not found"
        
        return self._serialize_machine(machine, include_users=False), None
    
    def create_machine(self, data: dict) -> Tuple[Optional[dict], Optional[dict]]:
        """
        Create a new machine.
        
        Args:
            data: Machine data
            
        Returns:
            Tuple of (machine_data, errors)
        """
        # Validate input
        errors = machine_create_schema.validate(data)
        if errors:
            return None, errors
        
        # Check if machine_code already exists
        if self.repository.exists(data.get('machine_code', '')):
            return None, {"machine_code": ["Machine code already exists"]}
        
        # Create machine
        validated_data = machine_create_schema.load(data)
        machine = self.repository.create(validated_data)
        
        return self._serialize_machine(machine), None
    
    def update_machine(self, machine_id: int, data: dict) -> Tuple[Optional[dict], Optional[dict]]:
        """
        Update an existing machine.
        
        Args:
            machine_id: Machine ID
            data: Update data
            
        Returns:
            Tuple of (machine_data, errors)
        """
        # Check if machine exists
        if not self.repository.get_by_id(machine_id):
            return None, {"id": ["Machine not found"]}
        
        # Validate input
        errors = machine_update_schema.validate(data)
        if errors:
            return None, errors
        
        # Update machine
        validated_data = machine_update_schema.load(data)
        machine = self.repository.update(machine_id, validated_data)
        
        return self._serialize_machine(machine), None
    
    def delete_machine(self, machine_id: int) -> Tuple[bool, Optional[str]]:
        """
        Delete a machine.
        
        Args:
            machine_id: Machine ID
            
        Returns:
            Tuple of (success, error_message)
        """
        machine = self.repository.get_by_id(machine_id)
        if not machine:
            return False, "Machine not found"
        
        # Check if machine has users
        if self.repository.has_users(machine_id):
            return False, "Cannot delete machine with active users"
        
        self.repository.delete(machine_id)
        return True, None
    
    def get_machine_users(
        self,
        machine_id: int,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        mapped_only: Optional[bool] = None
    ) -> Tuple[Optional[dict], Optional[str]]:
        """
        Get paginated users for a machine.
        
        Args:
            machine_id: Machine ID
            page: Page number
            per_page: Items per page
            search: Search term
            mapped_only: Filter by mapping status
            
        Returns:
            Tuple of (paginated_data, error_message)
        """
        machine = self.repository.get_by_id(machine_id)
        if not machine:
            return None, "Machine not found"
        
        query = self.repository.get_users(
            machine_id=machine_id,
            search=search,
            mapped_only=mapped_only
        )
        
        result = paginate_query(query, page, per_page)
        
        # Serialize users
        users_data = []
        for user in result["data"]:
            users_data.append(self._serialize_machine_user(user))
        
        result["data"] = users_data
        return result, None
    
    def _serialize_machine(self, machine: Machine, include_users: bool = False) -> dict:
        """Serialize a Machine object to dict."""
        data = {
            "id": machine.id,
            "machine_code": machine.machine_code,
            "location": machine.location,
            "status": machine.status or 'active',
            "user_count": self.repository.get_user_count(machine.id),
            "last_sync": machine.last_sync.isoformat() if machine.last_sync else None
        }
        
        if include_users:
            data["users"] = [
                self._serialize_machine_user(user) for user in machine.users
            ]
        
        return data
    
    def _serialize_machine_user(self, user: MachineUser) -> dict:
        """Serialize a MachineUser object to dict."""
        return {
            "id": user.id,
            "machine_user_id": user.machine_user_id,
            "machine_user_name": user.machine_user_name,
            "department": user.department,
            "is_mapped": user.student_map is not None
        }
    
    # --- Legacy method for backward compatibility ---
    @staticmethod
    def sync_users_from_excel(file_path: str, machine_code: str) -> dict:
        """
        Syncs machine users from the 'Stat' sheet of the machine excel file.
        """
        results = {
            'users_synced': 0,
            'users_updated': 0,
            'errors': []
        }

        try:
            # 1. Find sheet containing "stat"
            xl = pd.ExcelFile(file_path)
            stat_sheet = next((s for s in xl.sheet_names if "stat" in s.lower()), None)
            
            if not stat_sheet:
                raise ValueError("No sheet found with 'stat' in name (e.g., 'Statistik').")

            # 2. Scan rows to find header
            df_preview = pd.read_excel(file_path, sheet_name=stat_sheet, header=None, nrows=20)
            header_row_idx = None
            
            for idx, row in df_preview.iterrows():
                row_val = [str(x).lower().strip() for x in row.values if pd.notna(x)]
                if "id" in row_val and ("name" in row_val or "nama" in row_val):
                    header_row_idx = idx
                    break
            
            if header_row_idx is None:
                raise ValueError("Could not find table header (ID, Name/Nama) in Stat sheet.")

            # 3. Parse data
            df = pd.read_excel(file_path, sheet_name=stat_sheet, header=header_row_idx)
            
            # Normalize columns
            df.columns = [str(c).strip() for c in df.columns]
            
            # Identify columns
            id_col = next((c for c in df.columns if c.lower() == "id"), None)
            name_col = next((c for c in df.columns if c.lower() in ["name", "nama"]), None)
            dept_col = next((c for c in df.columns if c.lower() in ["department", "departemen", "dept"]), None)

            if not id_col or not name_col:
                raise ValueError(f"Missing required columns in Stat sheet. Found: {df.columns.tolist()}")

            # 4. Ensure Machine exists
            machine = Machine.query.filter_by(machine_code=machine_code).first()
            if not machine:
                machine = Machine(machine_code=machine_code, location="Unknown")
                db.session.add(machine)
                db.session.flush()
            
            # Update last_sync
            machine.last_sync = datetime.datetime.utcnow()

            # 5. Process Users
            for _, row in df.iterrows():
                uid = row[id_col]
                if pd.isna(uid):
                    continue
                
                uid_str = str(int(uid)) if isinstance(uid, float) else str(uid)
                name = row[name_col]
                dept = row[dept_col] if dept_col and pd.notna(row[dept_col]) else None
                
                if pd.isna(name):
                    continue
                
                # Check exist
                m_user = MachineUser.query.filter_by(
                    machine_id=machine.id, 
                    machine_user_id=uid_str
                ).first()
                
                if m_user:
                    # Update if changed
                    if m_user.machine_user_name != name or m_user.department != dept:
                        m_user.machine_user_name = name
                        m_user.department = dept
                        results['users_updated'] += 1
                else:
                    m_user = MachineUser(
                        machine_id=machine.id,
                        machine_user_id=uid_str,
                        machine_user_name=name,
                        department=dept
                    )
                    db.session.add(m_user)
                    results['users_synced'] += 1
            
            db.session.commit()
            return results

        except Exception as e:
            db.session.rollback()
            raise e


# Singleton instance
machine_service = MachineService()
