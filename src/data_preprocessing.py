"""
Data Preprocessing Module (Legacy Wrapper)

This module wraps the new ML preprocessing module for backward compatibility.
All actual preprocessing logic is now in src/ml/preprocessing.py

@deprecated Use src.ml.preprocessing instead
"""

# Re-export from the new module for backward compatibility
from src.ml.preprocessing import (
    engineer_features,
    engineer_features_from_df,
    engineer_features_for_student,
    get_feature_columns,
    prepare_features_for_model,
    FEATURE_COLUMNS,
    ABSENT_RATIO_THRESHOLD,
    ABSENT_COUNT_THRESHOLD,
)


# Legacy function - keep for backward compatibility
def clean_and_import_attendance(file_path: str):
    """
    Legacy function for importing attendance from CSV.

    @deprecated This functionality is now handled by IngestionService
    """
    import pandas as pd
    from src.domain.models import AttendanceDaily, Student
    from src.app.extensions import db
    import logging

    logger = logging.getLogger(__name__)
    session = db.session

    try:
        df = pd.read_csv(file_path)

        # Basic validation
        required_columns = {"nis", "date", "status"}
        if not required_columns.issubset(df.columns):
            raise ValueError(
                f"CSV missing required columns: {required_columns - set(df.columns)}"
            )

        # Convert date column
        df["date"] = pd.to_datetime(df["date"]).dt.date

        # Check against existing students
        existing_nis = {s.nis for s in session.query(Student.nis).all()}

        valid_records = []
        for _, row in df.iterrows():
            str_nis = str(row["nis"])
            if str_nis in existing_nis:
                # Check for duplicate record
                exists = (
                    session.query(AttendanceDaily)
                    .filter_by(student_nis=str_nis, attendance_date=row["date"])
                    .first()
                )

                if not exists:
                    record = AttendanceDaily(
                        student_nis=str_nis,
                        attendance_date=row["date"],
                        status=row["status"],
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
