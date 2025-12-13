import pandas as pd
from src.app.extensions import db
from src.domain.models import Machine, MachineUser
import logging

logger = logging.getLogger(__name__)

class MachineService:
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
            # We look for columns "ID", "Name" (or "Nama"), "Department"
            # Read first 20 rows
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
            dept_col = next((c for c in df.columns if c.lower() in ["department", "departemen", "dept"]), None) # Optional

            if not id_col or not name_col:
                raise ValueError(f"Missing required columns in Stat sheet. Found: {df.columns.tolist()}")

            # 4. Ensure Machine exists
            machine = Machine.query.filter_by(machine_code=machine_code).first()
            if not machine:
                machine = Machine(machine_code=machine_code, location="Unknown")
                db.session.add(machine)
                db.session.flush()

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
