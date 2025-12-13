import pandas as pd
import datetime
from src.app.extensions import db
from src.domain.models import ImportBatch, Machine, MachineUser, AttendanceRawLog
import logging
import json

logger = logging.getLogger(__name__)

class IngestionService:
    @staticmethod
    def import_logs_from_excel(file_path: str, filename: str, machine_code: str) -> dict:
        """
        Imports raw logs from 'Log' sheet.
        """
        batch = ImportBatch(
            filename=filename,
            file_type='logs',
            status='processing'
        )
        db.session.add(batch)
        db.session.flush()

        results = {
            'batch_id': batch.id,
            'logs_imported': 0,
            'errors': []
        }

        try:
            # 1. Find log sheet
            xl = pd.ExcelFile(file_path)
            log_sheet = next((s for s in xl.sheet_names if "log" in s.lower()), None)
            
            if not log_sheet:
                raise ValueError("No sheet found with 'log' in name.")

            # 2. Find Header
            # Look for "ID", "Time" or "DateTime" or "Waktu"
            df_preview = pd.read_excel(file_path, sheet_name=log_sheet, header=None, nrows=20)
            header_row_idx = None
            
            for idx, row in df_preview.iterrows():
                row_val = [str(x).lower().strip() for x in row.values if pd.notna(x)]
                if "id" in row_val and any(x in row_val for x in ["time", "datetime", "waktu"]):
                    header_row_idx = idx
                    break
            
            if header_row_idx is None:
                raise ValueError("Could not find table header (ID, Time) in Log sheet.")

            df = pd.read_excel(file_path, sheet_name=log_sheet, header=header_row_idx)
            df.columns = [str(c).strip() for c in df.columns]
            
            # Columns
            id_col = next((c for c in df.columns if c.lower() == "id"), None)
            time_col = next((c for c in df.columns if c.lower() in ["datetime", "time", "waktu"]), None)
            
            if not id_col or not time_col:
                raise ValueError("Missing ID or Time column in Log sheet.")
            
            # 3. Get Machine
            machine = Machine.query.filter_by(machine_code=machine_code).first()
            if not machine:
                 raise ValueError(f"Machine {machine_code} not found. Running Sync Users first is recommended.")

            # 4. Import Logs
            count = 0
            for index, row in df.iterrows():
                try:
                    uid = row[id_col]
                    if pd.isna(uid): continue
                    
                    uid_str = str(int(uid)) if isinstance(uid, float) else str(uid)
                    
                    # Parse Time
                    raw_time = row[time_col]
                    event_time = pd.to_datetime(raw_time)
                    
                    # Verify MachineUser
                    m_user = MachineUser.query.filter_by(
                        machine_id=machine.id, 
                        machine_user_id=uid_str
                    ).first()
                    
                    if not m_user:
                        # Log error but don't stop? Or strict? 
                        # Plan says: "Log error and skip"
                        results['errors'].append(f"Row {index}: User {uid_str} not found in machine {machine_code}")
                        continue
                    
                    # Create Raw Log
                    log_entry = AttendanceRawLog(
                        batch_id=batch.id,
                        machine_user_id_fk=m_user.id,
                        event_time=event_time,
                        raw_data=json.loads(row.to_json())
                    )
                    db.session.add(log_entry)
                    count += 1
                
                except Exception as row_err:
                    results['errors'].append(f"Row {index}: {str(row_err)}")

            batch.records_processed = count
            batch.status = 'completed' if not results['errors'] else 'completed_with_errors'
            batch.error_log = results['errors']
            
            results['logs_imported'] = count
            db.session.commit()
            return results

        except Exception as e:
            db.session.rollback()
            batch.status = 'failed'
            batch.error_log = [str(e)]
            db.session.commit()
            raise e
