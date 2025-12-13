import pandas as pd
import re
import math
from src.app.extensions import db
from src.domain.models import Teacher, Class, Student

class MasterDataService:
    @staticmethod
    def import_from_excel(file_path: str) -> dict:
        """
        Imports School Master Data from Excel file.
        Expects specific format for Teachers, Classes, and Students.
        """
        results = {
            'classes_processed': 0,
            'students_imported': 0,
            'errors': []
        }
        
        try:
            # Read first few rows for metadata (Class/Teacher info)
            # Assuming the file structure has Class/Teacher info in specific cells in early rows
            # or we iterate through sheets if multiple classes are in multiple sheets?
            # Specification says "Daftar_Absen_Siswa.xls"
            
            # Logic:
            # 1. Read first 10 rows without header to find Class/Teacher info
            df_meta = pd.read_excel(file_path, header=None, nrows=10)
            
            class_name = None
            teacher_name = None
            
            # Regex patterns
            class_pattern = r'(?:Kls|Kelas)\s*:?\s*([0-9A-Z]+)'
            teacher_pattern = r'Wali\s+Kelas\s*:?\s*(.+)'
            
            for index, row in df_meta.iterrows():
                row_str = " ".join([str(x) for x in row.values if pd.notna(x)])
                
                # Search for Class Match
                if not class_name:
                    match = re.search(class_pattern, row_str, re.IGNORECASE)
                    if match:
                        class_name = match.group(1).strip()
                
                # Search for Teacher Match
                if not teacher_name:
                    match = re.search(teacher_pattern, row_str, re.IGNORECASE)
                    if match:
                        teacher_name = match.group(1).strip()
            
            if not class_name:
                raise ValueError("Could not extract Class Name from file header.")
            
            # Upsert Teacher
            teacher_id = "T_" + re.sub(r'\s+', '_', teacher_name).upper() if teacher_name else "UNKNOWN"
            if teacher_name:
                teacher = Teacher.query.get(teacher_id)
                if not teacher:
                    teacher = Teacher(teacher_id=teacher_id, name=teacher_name, role="Wali Kelas")
                    db.session.add(teacher)
            
            # Upsert Class
            class_obj = Class.query.get(class_name)
            if not class_obj:
                class_obj = Class(class_name=class_name, class_id=class_name, wali_kelas_id=teacher_id if teacher_name else None)
                db.session.add(class_obj)
            else:
                if teacher_name:
                    class_obj.wali_kelas_id = teacher_id
            
            db.session.flush() # Ensure foreign keys exist
            results['classes_processed'] = 1
            
            # Find Header Row for Students
            full_df = pd.read_excel(file_path, header=None)
            header_row_idx = None
            
            for idx, row in full_df.iterrows():
                row_values = [str(val).upper() for val in row.values if pd.notna(val)]
                if "NO. INDUK" in row_values or "NIS" in row_values:
                     # Check if NAMA is also there to be sure
                     if any("NAMA" in s for s in row_values):
                        header_row_idx = idx
                        break
            
            if header_row_idx is None:
                raise ValueError("Could not find student table header (NO. INDUK / NAMA) in file.")
            
            # Reload DataFrame with correct header
            df_students = pd.read_excel(file_path, header=header_row_idx)
            
            # Normalize columns
            df_students.columns = [str(c).upper().strip() for c in df_students.columns]
            
            # Find column names
            nis_col = next((c for c in df_students.columns if "NO. INDUK" in c or "NIS" in c), None)
            name_col = next((c for c in df_students.columns if "NAMA" in c), None)
            
            if not nis_col or not name_col:
                raise ValueError("Missing NIS or Name column in student table.")
            
            for _, student_row in df_students.iterrows():
                raw_nis = student_row[nis_col]
                student_name = student_row[name_col]
                
                if pd.isna(raw_nis) or pd.isna(student_name) or str(student_name).strip() == "":
                    continue
                
                # Clean NIS (remove .0 if float)
                if isinstance(raw_nis, float):
                     nis = str(int(raw_nis))
                else:
                     nis = str(raw_nis).replace(".0", "")
                
                # Upsert Student
                student = Student.query.get(nis)
                if not student:
                    student = Student(nis=nis, name=student_name, class_id=class_name)
                    db.session.add(student)
                    results['students_imported'] += 1
                else:
                    # Update class if moved
                    if student.class_id != class_name:
                        student.class_id = class_name
            
            db.session.commit()
            return results

        except Exception as e:
            db.session.rollback()
            raise e
