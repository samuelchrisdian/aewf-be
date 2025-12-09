from sqlalchemy.orm import Session
from src.models import Student, Class, Teacher
from src.db_config import SessionLocal
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_session():
    return SessionLocal()

def import_master_data(file_path: str):
    """
    Imports master data from an Excel file.
    Expected sheets: 'Students', 'Classes', 'Teachers'
    """
    session = get_db_session()
    try:
        # Import Teachers
        try:
            df_teachers = pd.read_excel(file_path, sheet_name='Teachers')
            for _, row in df_teachers.iterrows():
                teacher = session.query(Teacher).filter(Teacher.teacher_id == str(row['teacher_id'])).first()
                if not teacher:
                    teacher = Teacher(
                        teacher_id=str(row['teacher_id']),
                        name=row['name'],
                        role=row.get('role', 'Teacher')
                    )
                    session.add(teacher)
            session.commit()
            logger.info("Teachers imported successfully.")
        except Exception as e:
            logger.error(f"Error importing teachers: {e}")
            session.rollback()

        # Import Classes
        try:
            df_classes = pd.read_excel(file_path, sheet_name='Classes')
            for _, row in df_classes.iterrows():
                class_obj = session.query(Class).filter(Class.class_id == str(row['class_id'])).first()
                if not class_obj:
                    class_obj = Class(
                        class_id=str(row['class_id']),
                        class_name=row['class_name'],
                        wali_kelas_id=str(row['wali_kelas_id']) if pd.notna(row['wali_kelas_id']) else None
                    )
                    session.add(class_obj)
            session.commit()
            logger.info("Classes imported successfully.")
        except Exception as e:
            logger.error(f"Error importing classes: {e}")
            session.rollback()

        # Import Students
        try:
            df_students = pd.read_excel(file_path, sheet_name='Students')
            for _, row in df_students.iterrows():
                student = session.query(Student).filter(Student.nis == str(row['nis'])).first()
                if not student:
                    student = Student(
                        nis=str(row['nis']),
                        name=row['name'],
                        class_id=str(row['class_id'])
                    )
                    session.add(student)
            session.commit()
            logger.info("Students imported successfully.")
        except Exception as e:
            logger.error(f"Error importing students: {e}")
            session.rollback()

    except Exception as e:
        logger.error(f"General error during import: {e}")
    finally:
        session.close()

def create_student(nis: str, name: str, class_id: str):
    session = get_db_session()
    try:
        student = Student(nis=nis, name=name, class_id=class_id)
        session.add(student)
        session.commit()
        return student
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating student: {e}")
        raise
    finally:
        session.close()

def get_student(nis: str):
    session = get_db_session()
    try:
        return session.query(Student).filter(Student.nis == nis).first()
    finally:
        session.close()

def get_students_by_teacher(teacher_id: str):
    """
    Returns a list of students that belong to the classes where the teacher is a wali kelas.
    """
    session = get_db_session()
    try:
        # Check if teacher exists
        teacher = session.query(Teacher).filter(Teacher.teacher_id == teacher_id).first()
        if not teacher:
            return []
        
        # Get classes for this teacher
        classes = session.query(Class).filter(Class.wali_kelas_id == teacher_id).all()
        class_ids = [c.class_id for c in classes]
        
        # Get students in these classes
        students = session.query(Student).filter(Student.class_id.in_(class_ids)).all()
        return students
    finally:
        session.close()
