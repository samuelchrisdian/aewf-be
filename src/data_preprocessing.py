import pandas as pd
from sqlalchemy.orm import Session
from src.domain.models import AttendanceDaily, Student, Class
from src.app.extensions import db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_session():
    return db.session

def clean_and_import_attendance(file_path: str):
    """
    Reads raw attendance CSV, cleans it, and imports to PostgreSQL.
    Expected columns: 'nis', 'date', 'status'
    """
    session = get_db_session()
    try:
        df = pd.read_csv(file_path)
        
        # Basic validation
        required_columns = {'nis', 'date', 'status'}
        if not required_columns.issubset(df.columns):
            raise ValueError(f"CSV missing required columns: {required_columns - set(df.columns)}")
        
        # Convert date column
        df['date'] = pd.to_datetime(df['date']).dt.date
        
        # Check against existing students
        existing_nis = {s.nis for s in session.query(Student.nis).all()}
        
        valid_records = []
        for _, row in df.iterrows():
            str_nis = str(row['nis'])
            if str_nis in existing_nis:
                # Check for duplicate record
                exists = session.query(AttendanceDaily).filter_by(
                    student_nis=str_nis, 
                    date=row['date']
                ).first()
                
                if not exists:
                    record = AttendanceDaily(
                        student_nis=str_nis,
                        date=row['date'],
                        status=row['status']
                    )
                    session.add(record)
                    valid_records.append(record)
        
        session.commit()
        logger.info(f"Imported {len(valid_records)} attendance records.")
        return len(valid_records)

    except Exception as e:
        session.rollback()
        logger.error(f"Error importing attendance: {e}")
        raise
    finally:
        session.close()

def engineer_features():
    """
    Fetches attendance records from DB and computes features for ML.
    Returns: DataFrame with features (e.g., total_absent, late_count, etc.)
    """
    session = get_db_session()
    try:
        # Fetch all records
        records = session.query(AttendanceDaily).all()
        if not records:
            return pd.DataFrame()
            
        data = [{
            'nis': r.student_nis,
            'status': r.status
        } for r in records]
        
        df = pd.DataFrame(data)
        
        # Feature Engineering
        # Pivot table to count statuses per student
        features = df.pivot_table(index='nis', columns='status', aggfunc='size', fill_value=0)
        
        # Ensure common columns exist
        for status in ['Present', 'Absent', 'Late', 'Sick', 'Permission']:
             if status not in features.columns:
                 features[status] = 0
                 
        # Compute Risk Ratios or other derived features
        features['total_attendance_days'] = features.sum(axis=1)
        features['absent_ratio'] = features['Absent'] / features['total_attendance_days']
        
        return features.reset_index()

    except Exception as e:
        logger.error(f"Error engineering features: {e}")
        return pd.DataFrame()
    finally:
        session.close()
