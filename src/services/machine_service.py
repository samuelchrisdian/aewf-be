"""
Machine service for business logic operations.
Handles CRUD operations and data processing for machines.
"""

import pandas as pd
from typing import Optional, Tuple, List
from src.app.extensions import db
from src.domain.models import Machine, MachineUser, StudentMachineMap
from src.repositories.machine_repo import machine_repository
from src.schemas.machine_schema import machine_create_schema, machine_update_schema
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
        order: str = "asc",
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
            status=status, search=search, sort_by=sort_by, order=order
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
        if self.repository.exists(data.get("machine_code", "")):
            return None, {"machine_code": ["Machine code already exists"]}

        # Create machine
        validated_data = machine_create_schema.load(data)
        machine = self.repository.create(validated_data)

        return self._serialize_machine(machine), None

    def update_machine(
        self, machine_id: int, data: dict
    ) -> Tuple[Optional[dict], Optional[dict]]:
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
        mapped_only: Optional[bool] = None,
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
            machine_id=machine_id, search=search, mapped_only=mapped_only
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
            "status": machine.status or "active",
            "user_count": self.repository.get_user_count(machine.id),
            "last_sync": machine.last_sync.isoformat() if machine.last_sync else None,
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
            "is_mapped": user.student_map is not None,
        }

    @staticmethod
    def sync_users_from_excel(
        file_path: str, machine_code: str, auto_create_machine: bool = False
    ) -> dict:
        """
        Syncs machine users from the 'Stat' sheet of the machine excel file.
        """
        results = {"users_synced": 0, "users_updated": 0, "errors": []}

        try:
            # 1. Ensure Machine Exists (Strict Mode Recommended)
            machine = Machine.query.filter_by(machine_code=machine_code).first()
            if not machine:
                if auto_create_machine:
                    machine = Machine(machine_code=machine_code, location="Unknown")
                    db.session.add(machine)
                    db.session.flush()
                else:
                    raise ValueError(
                        f"Machine '{machine_code}' not found in database. Please register the machine first."
                    )

            # 2. Find sheet containing "stat" (Case Insensitive)
            xl = pd.ExcelFile(file_path)
            stat_sheet = next((s for s in xl.sheet_names if "stat" in s.lower()), None)

            if not stat_sheet:
                # Fallback: Check if maybe it's named "Laporan" or just try the first sheet if desperate
                raise ValueError(
                    "No sheet found with 'stat' in name (e.g., 'Att. Stat.', 'Statistik')."
                )

            # 3. Scan rows to find header
            # Read as object/str to preserve original formatting during preview
            df_preview = pd.read_excel(
                file_path, sheet_name=stat_sheet, header=None, nrows=20
            )
            header_row_idx = None

            for idx, row in df_preview.iterrows():
                # Convert row to list of lowercase strings for checking
                row_val = [str(x).lower().strip() for x in row.values if pd.notna(x)]

                # Syarat Header: Ada 'ID' DAN ('Name' atau 'Nama')
                if "id" in row_val and any(x in row_val for x in ["name", "nama"]):
                    header_row_idx = idx
                    break

            if header_row_idx is None:
                raise ValueError(
                    "Could not find table header (ID, Name/Nama) in Stat sheet."
                )

            # 4. Parse data
            # dtype=str is CRUCIAL to prevent ID '001' becoming 1 or '190' becoming 190.0
            df = pd.read_excel(
                file_path, sheet_name=stat_sheet, header=header_row_idx, dtype=str
            )

            # Normalize columns (strip spaces)
            df.columns = [str(c).strip() for c in df.columns]

            # Identify columns dynamically
            id_col = next((c for c in df.columns if c.lower() == "id"), None)
            name_col = next(
                (c for c in df.columns if c.lower() in ["name", "nama"]), None
            )
            dept_col = next(
                (
                    c
                    for c in df.columns
                    if c.lower() in ["department", "departemen", "dept"]
                ),
                None,
            )

            if not id_col or not name_col:
                raise ValueError(
                    f"Missing required columns in Stat sheet. Found: {df.columns.tolist()}"
                )

            # 5. Process Users
            # Cache existing users to minimize DB queries inside loop
            existing_users = {
                u.machine_user_id: u
                for u in MachineUser.query.filter_by(machine_id=machine.id).all()
            }

            for _, row in df.iterrows():
                uid = row[id_col]
                name = row[name_col]

                # Validation: Skip empty IDs or Headers read as data
                if (
                    pd.isna(uid)
                    or pd.isna(name)
                    or str(uid).lower() in ["id", "nan", "none"]
                ):
                    continue

                # Clean Data - Ensure ID is read as string to avoid type mismatch
                uid_str = str(uid).strip().replace(".0", "")  # Remove .0 just in case
                name_clean = str(name).strip()
                dept_clean = (
                    str(row[dept_col]).strip()
                    if dept_col and pd.notna(row[dept_col])
                    else None
                )

                # FILTER: Only process users from 'SMP' department
                # Skip GTT, GTY, OB, and other departments
                if dept_clean and dept_clean.upper() != "SMP":
                    continue

                # Skip invalid rows (sub-headers usually have empty IDs, but just in case)
                if not uid_str:
                    continue

                # Upsert Logic
                if uid_str in existing_users:
                    m_user = existing_users[uid_str]
                    # Update only if changed
                    if (
                        m_user.machine_user_name != name_clean
                        or m_user.department != dept_clean
                    ):
                        m_user.machine_user_name = name_clean
                        m_user.department = dept_clean
                        results["users_updated"] += 1
                else:
                    new_user = MachineUser(
                        machine_id=machine.id,
                        machine_user_id=uid_str,
                        machine_user_name=name_clean,
                        department=dept_clean,
                    )
                    db.session.add(new_user)
                    results["users_synced"] += 1

            # Update last sync time
            machine.last_sync = datetime.datetime.utcnow()

            db.session.commit()
            return results

        except Exception as e:
            db.session.rollback()
            # Log error properly here
            raise e


# Singleton instance
machine_service = MachineService()
