import pandas as pd
from sqlalchemy.orm import Session
from src.domain.models import AttendanceDaily, Student
from src.app.extensions import db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_session():
    return db.session

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
    # session lifecycle handled by Flask
