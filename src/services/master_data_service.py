import pandas as pd
import re
from src.app.extensions import db
from src.domain.models import Teacher, Class, Student


class MasterDataService:
    """
    Service untuk import master data siswa dari file CSV per kelas.

    Format file CSV yang diharapkan:
    - Row 5: Kls / Smt,,: 7 ( Tujuh ) - A /,,,,  (untuk ekstrak nama kelas)
    - Row 6: Wali Kelas,,": Femi Nastiti, S. Pd",,,, (untuk ekstrak nama wali kelas)
    - Row 8: NO,NO. INDUK,BULAN : AGUSTUS,PADA TANGGAL... (header tabel)
    - Row 9+: Data siswa
    """

    @staticmethod
    def import_from_csv(file_path: str) -> dict:
        """
        Import master data dari file CSV per kelas.

        Args:
            file_path: Path ke file CSV

        Returns:
            dict: Hasil import dengan keys 'classes_processed', 'students_imported', 'errors'
        """
        results = {"classes_processed": 0, "students_imported": 0, "errors": []}

        try:
            # 1. Baca file tanpa header untuk parsing metadata (Row 0-7)
            df_meta = pd.read_csv(
                file_path, header=None, nrows=8, encoding="utf-8", on_bad_lines="skip"
            )

            # 2. Ekstrak Nama Kelas dari Row 5 (index 4)
            class_name = None
            teacher_name = None

            if len(df_meta) > 4:
                row_5 = " ".join(
                    [str(x) for x in df_meta.iloc[4].values if pd.notna(x)]
                )
                class_match = re.search(
                    r"(\d+)\s*\([^)]*\)\s*[-]?\s*([A-Z])", row_5, re.IGNORECASE
                )
                if class_match:
                    grade = class_match.group(1)
                    section = class_match.group(2).upper()
                    class_name = f"{grade}{section}"

            # 3. Ekstrak Nama Wali Kelas dari Row 6 (index 5)
            if len(df_meta) > 5:
                row_6 = " ".join(
                    [str(x) for x in df_meta.iloc[5].values if pd.notna(x)]
                )
                teacher_match = re.search(
                    r"Wali\s+Kelas\s*[:\"]?\s*([^\"]+)", row_6, re.IGNORECASE
                )
                if teacher_match:
                    teacher_name = teacher_match.group(1).strip().strip('"').strip()

            if not class_name:
                import os

                class_name = (
                    os.path.splitext(os.path.basename(file_path))[0]
                    .replace("Kls", "")
                    .strip()
                )
                results["errors"].append(
                    f"Warning: Could not extract class name from Row 5, using filename: {class_name}"
                )

            # 4. UPSERT Teacher
            teacher_id = None
            if teacher_name:
                simple_name = teacher_name.split(",")[0]
                teacher_id = "T_" + re.sub(r"[^A-Z]", "", simple_name.upper())[:10]

                teacher = Teacher.query.get(teacher_id)
                if not teacher:
                    teacher = Teacher(
                        teacher_id=teacher_id, name=teacher_name, role="Wali Kelas"
                    )
                    db.session.add(teacher)
                else:
                    if teacher.name != teacher_name:
                        teacher.name = teacher_name

            # 5. UPSERT Class
            class_obj = Class.query.get(class_name)
            if not class_obj:
                class_obj = Class(
                    class_name=class_name, class_id=class_name, wali_kelas_id=teacher_id
                )
                db.session.add(class_obj)
            else:
                if teacher_id:
                    class_obj.wali_kelas_id = teacher_id

            results["classes_processed"] += 1

            # 6. Reload dataframe dengan header=7
            df_students = pd.read_csv(
                file_path, header=7, dtype=str, encoding="utf-8", on_bad_lines="skip"
            )

            df_students.columns = [str(c).strip().upper() for c in df_students.columns]

            nis_col = None
            name_col = None

            for col in df_students.columns:
                if "NO. INDUK" in col or "NO INDUK" in col or col == "NIS":
                    nis_col = col
                elif col == "NAMA" or "NAMA" in col:
                    name_col = col

            if not nis_col and len(df_students.columns) > 1:
                nis_col = df_students.columns[1]

            if not name_col and len(df_students.columns) > 2:
                name_col = df_students.columns[2]

            if not nis_col or not name_col:
                raise ValueError(
                    f"Required columns not found. Available: {df_students.columns.tolist()}"
                )

            for _, row in df_students.iterrows():
                raw_nis = row.get(nis_col)
                raw_name = row.get(name_col)

                if pd.isna(raw_nis) or pd.isna(raw_name):
                    continue

                nis = str(raw_nis).strip().replace(".0", "")
                name = str(raw_name).strip()

                if not nis or not nis.replace(" ", "").isdigit():
                    continue

                student = Student.query.get(nis)
                if not student:
                    student = Student(nis=nis, name=name, class_id=class_name)
                    db.session.add(student)
                    results["students_imported"] += 1
                else:
                    if student.class_id != class_name:
                        student.class_id = class_name
                    if student.name != name:
                        student.name = name

            db.session.commit()
            return results

        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def import_from_excel(file_path: str) -> dict:
        """
        Import master data dari file Excel (xls/xlsx) dengan multiple sheets.
        Setiap sheet dapat berisi multiple classes.
        """
        results = {"classes_processed": 0, "students_imported": 0, "errors": []}

        try:
            xls = pd.ExcelFile(file_path)

            for sheet_name in xls.sheet_names:
                try:
                    MasterDataService._process_excel_sheet(xls, sheet_name, results)
                except Exception as sheet_err:
                    results["errors"].append(f"Sheet {sheet_name}: {str(sheet_err)}")

            db.session.commit()
            return results

        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def _process_excel_sheet(excel_file, sheet_name, results):
        """
        Process a single Excel sheet that may contain MULTIPLE classes.

        Each class section starts with:
        - "Kls / Smt" row containing class info
        - "Wali Kelas" row containing teacher info
        - Header row with "NO. INDUK"
        - Student data rows
        """
        # Baca seluruh sheet tanpa header
        full_df = pd.read_excel(
            excel_file, sheet_name=sheet_name, header=None, dtype=str
        )

        # 1. CARI SEMUA POSISI "Kls / Smt" (penanda awal setiap kelas)
        class_start_rows = []
        for idx, row in full_df.iterrows():
            row_str = " ".join([str(x) for x in row.values if pd.notna(x)])
            if re.search(r"Kls\s*/?\s*Smt|Kelas\s*/?\s*Smt", row_str, re.IGNORECASE):
                class_start_rows.append(idx)

        if not class_start_rows:
            # Fallback: proses seluruh sheet sebagai satu kelas
            class_start_rows = [0]

        # 2. PROSES SETIAP KELAS
        for i, start_row in enumerate(class_start_rows):
            # Tentukan batas akhir (sampai kelas berikutnya atau akhir file)
            end_row = (
                class_start_rows[i + 1]
                if i + 1 < len(class_start_rows)
                else len(full_df)
            )

            # Subset dataframe untuk kelas ini
            class_df = full_df.iloc[start_row:end_row].reset_index(drop=True)

            try:
                MasterDataService._process_single_class(class_df, results)
            except Exception as e:
                results["errors"].append(
                    f"Sheet {sheet_name} Row {start_row}: {str(e)}"
                )

    @staticmethod
    def _process_single_class(class_df, results):
        """
        Process a single class section from the dataframe.

        Args:
            class_df: Subset of dataframe containing one class
            results: Results dictionary to update
        """
        class_name = None
        teacher_name = None
        header_idx = None

        # A. EKSTRAK METADATA dari baris pertama (Kls/Smt dan Wali Kelas)
        for idx in range(min(10, len(class_df))):  # Scan first 10 rows
            row = class_df.iloc[idx]
            row_str = " ".join([str(x) for x in row.values if pd.notna(x)])

            # Cari Nama Kelas: "7 ( Tujuh ) - A" -> "7A"
            if not class_name:
                match = re.search(
                    r"(\d+)\s*\([^)]*\)\s*[-]?\s*([A-Z])", row_str, re.IGNORECASE
                )
                if match:
                    grade = match.group(1)
                    section = match.group(2).upper()
                    class_name = f"{grade}{section}"

            # Cari Nama Guru
            if not teacher_name:
                match = re.search(r"Wali\s+Kelas\s*:?\s*(.+)", row_str, re.IGNORECASE)
                if match:
                    teacher_name = match.group(1).strip().strip('"').strip(":").strip()

            # Cari Header Tabel (NO. INDUK)
            if header_idx is None:
                row_vals = [str(x).upper() for x in row.values]
                if any("NO. INDUK" in s or "NO INDUK" in s for s in row_vals):
                    header_idx = idx

        if not class_name:
            raise ValueError("Nama kelas tidak ditemukan (format: '7 ( Tujuh ) - A')")

        if header_idx is None:
            raise ValueError("Header tabel (NO. INDUK) tidak ditemukan")

        # B. UPSERT Teacher
        teacher_id = None
        if teacher_name:
            simple_name = teacher_name.split(",")[0]
            teacher_id = "T_" + re.sub(r"[^A-Z]", "", simple_name.upper())[:10]

            teacher = Teacher.query.get(teacher_id)
            if not teacher:
                teacher = Teacher(
                    teacher_id=teacher_id, name=teacher_name, role="Wali Kelas"
                )
                db.session.add(teacher)

        # C. UPSERT Class
        class_obj = Class.query.get(class_name)
        if not class_obj:
            class_obj = Class(
                class_name=class_name, class_id=class_name, wali_kelas_id=teacher_id
            )
            db.session.add(class_obj)
        else:
            if teacher_id:
                class_obj.wali_kelas_id = teacher_id

        results["classes_processed"] += 1

        # D. BACA DATA SISWA (setelah header)
        # Ambil baris setelah header sampai akhir class_df
        student_rows = class_df.iloc[header_idx + 1 :]

        for _, row in student_rows.iterrows():
            # Kolom 1 = NO. INDUK (NIS), Kolom 2 = NAMA (berdasarkan posisi)
            if len(row) < 3:
                continue

            raw_nis = row.iloc[1]
            raw_name = row.iloc[2]

            if pd.isna(raw_nis) or pd.isna(raw_name):
                continue

            nis = str(raw_nis).replace(".0", "").strip()
            name = str(raw_name).strip()

            # Skip jika NIS bukan angka atau kosong
            if not nis or not nis.isdigit():
                continue

            # Upsert Student
            student = Student.query.get(nis)
            if not student:
                student = Student(nis=nis, name=name, class_id=class_name)
                db.session.add(student)
                results["students_imported"] += 1
            else:
                if student.class_id != class_name:
                    student.class_id = class_name


# Singleton instance
master_data_service = MasterDataService()
