"""
Export service for generating Excel files.
Handles data export operations for students, attendance, and templates.
"""

from typing import Optional
from datetime import datetime
from io import BytesIO
import xlsxwriter

from src.repositories.student_repo import student_repository
from src.repositories.attendance_repo import attendance_repository
from src.repositories.class_repo import class_repository


class ExportService:
    """Service class for Excel export operations."""

    def export_students_excel(self, class_id: Optional[str] = None) -> BytesIO:
        """
        Export students to Excel file.

        Args:
            class_id: Optional filter by class

        Returns:
            BytesIO: Excel file buffer
        """
        # Get students
        query = student_repository.get_all()
        if class_id:
            query = query.filter_by(class_id=class_id)
        students = query.all()

        # Create Excel file in memory
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Students")

        # Add formats
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#4472C4", "font_color": "white", "border": 1}
        )

        # Write headers
        headers = ["NIS", "Name", "Class ID", "Class Name", "Parent Phone", "Active"]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Write data
        for row, student in enumerate(students, start=1):
            worksheet.write(row, 0, student.nis)
            worksheet.write(row, 1, student.name)
            worksheet.write(row, 2, student.class_id)
            worksheet.write(
                row,
                3,
                student.student_class.class_name if student.student_class else "",
            )
            worksheet.write(row, 4, student.parent_phone or "")
            worksheet.write(row, 5, "Yes" if student.is_active else "No")

        # Auto-fit columns
        worksheet.set_column("A:A", 12)  # NIS
        worksheet.set_column("B:B", 25)  # Name
        worksheet.set_column("C:C", 12)  # Class ID
        worksheet.set_column("D:D", 20)  # Class Name
        worksheet.set_column("E:E", 15)  # Phone
        worksheet.set_column("F:F", 10)  # Active

        workbook.close()
        output.seek(0)

        return output

    def export_attendance_excel(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        class_id: Optional[str] = None,
    ) -> BytesIO:
        """
        Export attendance records to Excel file in matrix format.
        When class_id is provided, creates single sheet.
        When class_id is not provided, creates one sheet per class.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            class_id: Optional filter by class

        Returns:
            BytesIO: Excel file buffer
        """
        import calendar

        # Parse dates
        start_dt = (
            datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        )
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

        # Determine year and month from start_date
        if start_dt:
            year = start_dt.year
            month = start_dt.month
        else:
            year = datetime.now().year
            month = datetime.now().month

        # Indonesian month names
        month_names_id = {
            1: "JANUARI",
            2: "FEBRUARI",
            3: "MARET",
            4: "APRIL",
            5: "MEI",
            6: "JUNI",
            7: "JULI",
            8: "AGUSTUS",
            9: "SEPTEMBER",
            10: "OKTOBER",
            11: "NOVEMBER",
            12: "DESEMBER",
        }
        month_name = month_names_id.get(month, "")

        # Get days in month
        _, days_in_month = calendar.monthrange(year, month)

        # Get academic year
        academic_year = f"{year}-{year + 1}" if month >= 7 else f"{year - 1}-{year}"

        # Create Excel file in memory
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        # Create formats (defined at workbook level for reuse across sheets)
        formats = self._create_attendance_formats(workbook)

        # Prepare date range for querying
        period_start = datetime(year, month, 1).date()
        period_end = datetime(year, month, days_in_month).date()

        # Get list of classes to process
        if class_id:
            # Single class
            class_obj = class_repository.get_by_id(class_id)
            classes_to_process = [class_obj] if class_obj else []
        else:
            # All classes
            classes_to_process = class_repository.get_all().all()

        # Create one sheet per class
        for class_obj in classes_to_process:
            # Sheet name (max 31 characters for Excel)
            sheet_name = (
                class_obj.class_name[:31]
                if class_obj.class_name
                else class_obj.class_id[:31]
            )

            # Create worksheet for this class
            worksheet = workbook.add_worksheet(sheet_name)

            # Get class info
            wali_kelas_name = class_obj.wali_kelas.name if class_obj.wali_kelas else ""
            class_display_name = class_obj.class_name

            # Write sheet content
            self._write_attendance_sheet(
                worksheet=worksheet,
                formats=formats,
                class_obj=class_obj,
                class_display_name=class_display_name,
                wali_kelas_name=wali_kelas_name,
                year=year,
                month=month,
                month_name=month_name,
                days_in_month=days_in_month,
                academic_year=academic_year,
                period_start=period_start,
                period_end=period_end,
            )

        workbook.close()
        output.seek(0)

        return output

    def _create_attendance_formats(self, workbook):
        """Create and return all formats needed for attendance sheets."""
        return {
            "title": workbook.add_format(
                {
                    "bold": True,
                    "font_size": 14,
                    "font_color": "red",
                    "align": "center",
                    "valign": "vcenter",
                }
            ),
            "subtitle": workbook.add_format(
                {
                    "bold": True,
                    "font_size": 12,
                    "font_color": "red",
                    "align": "center",
                    "valign": "vcenter",
                }
            ),
            "year": workbook.add_format(
                {"bold": True, "font_size": 11, "align": "center", "valign": "vcenter"}
            ),
            "class_info": workbook.add_format(
                {"bold": True, "font_size": 10, "bg_color": "yellow"}
            ),
            "header": workbook.add_format(
                {
                    "bold": True,
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "text_wrap": True,
                }
            ),
            "date_header": workbook.add_format(
                {
                    "bold": True,
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "font_size": 9,
                }
            ),
            "weekend_header": workbook.add_format(
                {
                    "bold": True,
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "font_size": 9,
                    "bg_color": "red",
                    "font_color": "white",
                }
            ),
            "cell": workbook.add_format(
                {"border": 1, "align": "center", "valign": "vcenter"}
            ),
            "cell_left": workbook.add_format(
                {"border": 1, "align": "left", "valign": "vcenter"}
            ),
            "weekend_cell": workbook.add_format(
                {"border": 1, "align": "center", "valign": "vcenter", "bg_color": "red"}
            ),
            "status": workbook.add_format(
                {"border": 1, "align": "center", "valign": "vcenter", "font_size": 9}
            ),
            "present_cell": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "bg_color": "#92D050",
                }
            ),
            "late_cell": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "bg_color": "#FFFF00",
                }
            ),
            "summary_header": workbook.add_format(
                {
                    "bold": True,
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "font_size": 8,
                }
            ),
            "signature": workbook.add_format({"align": "left", "valign": "vcenter"}),
            "underline": workbook.add_format({"underline": True, "bold": True}),
        }

    def _write_attendance_sheet(
        self,
        worksheet,
        formats,
        class_obj,
        class_display_name,
        wali_kelas_name,
        year,
        month,
        month_name,
        days_in_month,
        academic_year,
        period_start,
        period_end,
    ):
        """Write attendance data to a single worksheet."""
        row = 0
        title_col_end = 3 + days_in_month + 4  # NO, NO.INDUK, NAMA, days, H, S, I, A

        # Title section
        worksheet.merge_range(
            row, 0, row, title_col_end, "REKAP ABSENSI SISWA", formats["title"]
        )
        row += 1

        worksheet.merge_range(
            row,
            0,
            row,
            title_col_end,
            "SEKOLAH MENENGAH PERTAMA KRISTEN PELITA KASIH",
            formats["subtitle"],
        )
        row += 1

        worksheet.merge_range(
            row,
            0,
            row,
            title_col_end,
            f"TAHUN PELAJARAN {academic_year}",
            formats["year"],
        )
        row += 2

        # Class info
        worksheet.write(row, 0, "Kls / Smt", formats["class_info"])
        worksheet.write(row, 1, f": {class_display_name} /", formats["class_info"])
        row += 1

        worksheet.write(row, 0, "Wali Kelas", formats["class_info"])
        worksheet.write(row, 1, f": {wali_kelas_name}", formats["class_info"])
        row += 2

        # Table header row 1
        header_row = row
        worksheet.merge_range(
            header_row, 0, header_row + 1, 0, "NO.", formats["header"]
        )
        worksheet.merge_range(
            header_row, 1, header_row + 1, 1, "NO.\nINDUK", formats["header"]
        )

        # Month and NAMA header
        worksheet.write(header_row, 2, f"BULAN : {month_name}", formats["header"])
        worksheet.write(header_row + 1, 2, "NAMA", formats["header"])

        # PADA TANGGAL header
        worksheet.merge_range(
            header_row,
            3,
            header_row,
            3 + days_in_month - 1,
            "PADA TANGGAL",
            formats["header"],
        )

        # JUMLAH header
        jumlah_start_col = 3 + days_in_month
        worksheet.merge_range(
            header_row,
            jumlah_start_col,
            header_row,
            jumlah_start_col + 3,
            "JUMLAH",
            formats["header"],
        )

        # Date numbers (1-31) in second header row
        for day in range(1, days_in_month + 1):
            col = 2 + day
            day_date = datetime(year, month, day)
            is_weekend = day_date.weekday() >= 5

            if is_weekend:
                worksheet.write(header_row + 1, col, day, formats["weekend_header"])
            else:
                worksheet.write(header_row + 1, col, day, formats["date_header"])

        # H, S, I, A headers
        worksheet.write(
            header_row + 1, jumlah_start_col, "H", formats["summary_header"]
        )
        worksheet.write(
            header_row + 1, jumlah_start_col + 1, "S", formats["summary_header"]
        )
        worksheet.write(
            header_row + 1, jumlah_start_col + 2, "I", formats["summary_header"]
        )
        worksheet.write(
            header_row + 1, jumlah_start_col + 3, "A", formats["summary_header"]
        )

        row = header_row + 2

        # Get students for this class
        students = student_repository.get_all(
            class_id=class_obj.class_id, is_active=True
        ).all()

        # Write student data
        for idx, student in enumerate(students, start=1):
            worksheet.write(row, 0, idx, formats["cell"])
            worksheet.write(row, 1, student.nis, formats["cell"])
            worksheet.write(row, 2, student.name, formats["cell_left"])

            # Get attendance records for this student
            attendance_records = attendance_repository.get_by_student(
                nis=student.nis, start_date=period_start, end_date=period_end
            )

            # Create a map of date -> status
            attendance_map = {
                record.attendance_date.day: record.status
                for record in attendance_records
            }

            # Counters for summary
            hadir_count = 0
            sick_count = 0
            permission_count = 0
            absent_count = 0

            # Write attendance for each day
            for day in range(1, days_in_month + 1):
                col = 2 + day
                day_date = datetime(year, month, day)
                is_weekend = day_date.weekday() >= 5

                # Only process attendance data if not weekend
                status = attendance_map.get(day, "") if not is_weekend else ""
                display_text = ""
                cell_style = formats["status"]

                if status:
                    status_lower = status.lower()
                    if status_lower == "present":
                        hadir_count += 1
                        cell_style = formats["present_cell"]
                    elif status_lower == "late":
                        hadir_count += 1
                        cell_style = formats["late_cell"]
                    elif status_lower == "sick":
                        display_text = "s"
                        sick_count += 1
                    elif status_lower == "permission":
                        display_text = "i"
                        permission_count += 1
                    elif status_lower == "absent":
                        display_text = "a"
                        absent_count += 1

                # Apply appropriate formatting
                if is_weekend:
                    worksheet.write(row, col, display_text, formats["weekend_cell"])
                else:
                    worksheet.write(row, col, display_text, cell_style)

            # Write summary columns (H, S, I, A)
            worksheet.write(
                row,
                jumlah_start_col,
                hadir_count if hadir_count > 0 else "",
                formats["cell"],
            )
            worksheet.write(
                row,
                jumlah_start_col + 1,
                sick_count if sick_count > 0 else "",
                formats["cell"],
            )
            worksheet.write(
                row,
                jumlah_start_col + 2,
                permission_count if permission_count > 0 else "",
                formats["cell"],
            )
            worksheet.write(
                row,
                jumlah_start_col + 3,
                absent_count if absent_count > 0 else "",
                formats["cell"],
            )

            row += 1

        # Signature section
        row += 3
        worksheet.write(row, 0, "Mengetahui,", formats["signature"])
        row += 1
        worksheet.write(row, 0, "Kepala Sekolah", formats["signature"])

        city_name = "Lawang"
        worksheet.write(
            row - 1, jumlah_start_col - 5, f"{city_name},", formats["signature"]
        )
        worksheet.write(row, jumlah_start_col - 5, "Guru", formats["signature"])

        row += 4
        worksheet.write(row, 0, "Herawati Dewiani, S.Pd, M.M", formats["underline"])

        # Set column widths
        worksheet.set_column(0, 0, 4)
        worksheet.set_column(1, 1, 8)
        worksheet.set_column(2, 2, 30)
        worksheet.set_column(3, 2 + days_in_month, 3)
        worksheet.set_column(jumlah_start_col, jumlah_start_col + 3, 3)

    def generate_master_template(self) -> BytesIO:
        """
        Generate master data import template Excel file.

        Returns:
            BytesIO: Excel file buffer
        """
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        # Add formats
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#4472C4", "font_color": "white", "border": 1}
        )

        example_format = workbook.add_format({"italic": True, "font_color": "#7F7F7F"})

        # Students sheet
        students_sheet = workbook.add_worksheet("Students")
        student_headers = ["nis", "name", "class_id", "parent_phone"]
        for col, header in enumerate(student_headers):
            students_sheet.write(0, col, header, header_format)

        # Add example row
        students_sheet.write(1, 0, "2024001", example_format)
        students_sheet.write(1, 1, "John Doe", example_format)
        students_sheet.write(1, 2, "X-IPA-1", example_format)
        students_sheet.write(1, 3, "081234567890", example_format)

        students_sheet.set_column("A:A", 12)
        students_sheet.set_column("B:B", 25)
        students_sheet.set_column("C:C", 12)
        students_sheet.set_column("D:D", 15)

        # Classes sheet
        classes_sheet = workbook.add_worksheet("Classes")
        class_headers = ["class_id", "class_name", "wali_kelas_id"]
        for col, header in enumerate(class_headers):
            classes_sheet.write(0, col, header, header_format)

        # Add example row
        classes_sheet.write(1, 0, "X-IPA-1", example_format)
        classes_sheet.write(1, 1, "X IPA 1", example_format)
        classes_sheet.write(1, 2, "T001", example_format)

        classes_sheet.set_column("A:A", 12)
        classes_sheet.set_column("B:B", 20)
        classes_sheet.set_column("C:C", 15)

        # Teachers sheet
        teachers_sheet = workbook.add_worksheet("Teachers")
        teacher_headers = ["teacher_id", "name", "phone", "role"]
        for col, header in enumerate(teacher_headers):
            teachers_sheet.write(0, col, header, header_format)

        # Add example row
        teachers_sheet.write(1, 0, "T001", example_format)
        teachers_sheet.write(1, 1, "Mrs. Sarah", example_format)
        teachers_sheet.write(1, 2, "081234567890", example_format)
        teachers_sheet.write(1, 3, "Wali Kelas", example_format)

        teachers_sheet.set_column("A:A", 12)
        teachers_sheet.set_column("B:B", 25)
        teachers_sheet.set_column("C:C", 15)
        teachers_sheet.set_column("D:D", 15)

        workbook.close()
        output.seek(0)

        return output


# Singleton instance
export_service = ExportService()
