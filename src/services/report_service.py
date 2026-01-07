"""
Report service for generating reports.
Handles report generation for attendance, risk, and class summaries.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from io import BytesIO
import xlsxwriter

from src.repositories.attendance_repo import attendance_repository
from src.repositories.student_repo import student_repository
from src.repositories.class_repo import class_repository
from src.repositories.risk_repo import risk_repository


class ReportService:
    """Service class for report generation."""

    def get_attendance_report(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        class_id: Optional[str] = None,
        student_nis: Optional[str] = None,
        format: str = "json",
    ) -> Dict[str, Any]:
        """
        Generate attendance report with statistics.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            class_id: Filter by class
            student_nis: Filter by student
            format: 'json' or 'excel'

        Returns:
            Report data dict or BytesIO for excel
        """
        # Parse dates
        start_dt = (
            datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        )
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

        # Get attendance statistics
        stats = attendance_repository.get_summary_stats(
            class_id=class_id, start_date=start_dt, end_date=end_dt
        )

        # Get daily breakdown
        daily_breakdown = attendance_repository.get_daily_breakdown(
            class_id=class_id, start_date=start_dt, end_date=end_dt
        )

        # Build report data
        report_data = {
            "report_type": "attendance",
            "period": {"start_date": start_date, "end_date": end_date},
            "filters": {"class_id": class_id, "student_nis": student_nis},
            "statistics": stats,
            "daily_breakdown": daily_breakdown,
            "generated_at": datetime.now().isoformat(),
        }

        # If student-specific, add student details
        if student_nis:
            student = student_repository.get_by_nis(student_nis)
            if student:
                student_stats = attendance_repository.count_by_status(
                    nis=student_nis, start_date=start_dt, end_date=end_dt
                )
                report_data["student"] = {
                    "nis": student.nis,
                    "name": student.name,
                    "class_id": student.class_id,
                    "statistics": student_stats,
                }

        if format == "excel":
            return self._generate_attendance_excel(report_data)

        return report_data

    def get_risk_report(
        self, class_id: Optional[str] = None, format: str = "json"
    ) -> Dict[str, Any]:
        """
        Generate risk report with at-risk students and interventions.

        Args:
            class_id: Filter by class
            format: 'json' or 'excel'

        Returns:
            Report data dict or BytesIO for excel
        """
        # Get at-risk students
        risk_students = risk_repository.get_all_with_details(class_id=class_id)

        # Build report data
        report_data = {
            "report_type": "risk",
            "filters": {"class_id": class_id},
            "summary": {
                "total_at_risk": len(risk_students),
                "high_risk": sum(1 for s in risk_students if s.risk_level == "high"),
                "medium_risk": sum(
                    1 for s in risk_students if s.risk_level == "medium"
                ),
                "low_risk": sum(1 for s in risk_students if s.risk_level == "low"),
            },
            "students": [],
            "generated_at": datetime.now().isoformat(),
        }

        # Add student details with interventions
        for risk_student in risk_students:
            student_data = {
                "nis": risk_student.student_nis,
                "name": risk_student.student.name if risk_student.student else "",
                "class_id": (
                    risk_student.student.class_id if risk_student.student else ""
                ),
                "risk_level": risk_student.risk_level,
                "risk_score": (
                    float(risk_student.risk_score) if risk_student.risk_score else 0
                ),
                "factors": risk_student.factors or {},
                "last_updated": (
                    risk_student.calculated_at.isoformat()
                    if risk_student.calculated_at
                    else None
                ),
            }

            # Get intervention history if available
            if hasattr(risk_student, "interventions"):
                student_data["interventions"] = [
                    {
                        "action": intervention.action,
                        "notes": intervention.notes,
                        "date": intervention.created_at.isoformat(),
                    }
                    for intervention in risk_student.interventions
                ]

            report_data["students"].append(student_data)

        if format == "excel":
            return self._generate_risk_excel(report_data)

        return report_data

    def get_class_summary_report(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        format: str = "json",
    ) -> Dict[str, Any]:
        """
        Generate class summary report with statistics.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            format: 'json' or 'excel'

        Returns:
            Report data dict or BytesIO for excel
        """
        # Parse dates
        start_dt = (
            datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        )
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

        # Get all classes
        classes = class_repository.get_all().all()

        # Build report data
        report_data = {
            "report_type": "class_summary",
            "period": {"start_date": start_date, "end_date": end_date},
            "classes": [],
            "generated_at": datetime.now().isoformat(),
        }

        # Get statistics for each class
        for class_obj in classes:
            # Get attendance stats for this class
            stats = attendance_repository.get_summary_stats(
                class_id=class_obj.class_id, start_date=start_dt, end_date=end_dt
            )

            # Get risk count for this class
            risk_count = risk_repository.count_by_class(class_obj.class_id)

            class_data = {
                "class_id": class_obj.class_id,
                "class_name": class_obj.class_name,
                "wali_kelas": (
                    {
                        "teacher_id": class_obj.wali_kelas_id,
                        "name": (
                            class_obj.wali_kelas.name if class_obj.wali_kelas else ""
                        ),
                    }
                    if class_obj.wali_kelas_id
                    else None
                ),
                "student_count": (
                    len(class_obj.students) if hasattr(class_obj, "students") else 0
                ),
                "attendance_statistics": stats,
                "at_risk_students": risk_count,
            }

            report_data["classes"].append(class_data)

        if format == "excel":
            return self._generate_class_summary_excel(report_data)

        return report_data

    def _generate_attendance_excel(self, report_data: Dict[str, Any]) -> BytesIO:
        """Generate Excel file for attendance report in matrix format."""
        import calendar
        from datetime import datetime as dt

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Rekap Absensi")

        # Parse period dates
        start_date_str = report_data["period"].get("start_date")
        end_date_str = report_data["period"].get("end_date")

        if start_date_str:
            start_dt = dt.strptime(start_date_str, "%Y-%m-%d")
            year = start_dt.year
            month = start_dt.month
        else:
            year = dt.now().year
            month = dt.now().month

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

        # Get class info
        class_id = report_data["filters"].get("class_id")
        class_obj = None
        wali_kelas_name = ""
        class_display_name = ""

        if class_id:
            class_obj = class_repository.get_by_id(class_id)
            if class_obj:
                class_display_name = class_obj.class_name
                if class_obj.wali_kelas:
                    wali_kelas_name = class_obj.wali_kelas.name

        # Create formats
        title_format = workbook.add_format(
            {
                "bold": True,
                "font_size": 14,
                "font_color": "red",
                "align": "center",
                "valign": "vcenter",
            }
        )

        subtitle_format = workbook.add_format(
            {
                "bold": True,
                "font_size": 12,
                "font_color": "red",
                "align": "center",
                "valign": "vcenter",
            }
        )

        year_format = workbook.add_format(
            {"bold": True, "font_size": 11, "align": "center", "valign": "vcenter"}
        )

        class_info_format = workbook.add_format(
            {"bold": True, "font_size": 10, "bg_color": "yellow"}
        )

        header_format = workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "align": "center",
                "valign": "vcenter",
                "text_wrap": True,
            }
        )

        date_header_format = workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "align": "center",
                "valign": "vcenter",
                "font_size": 9,
            }
        )

        weekend_header_format = workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "align": "center",
                "valign": "vcenter",
                "font_size": 9,
                "bg_color": "red",
                "font_color": "white",
            }
        )

        cell_format = workbook.add_format(
            {"border": 1, "align": "center", "valign": "vcenter"}
        )

        cell_left_format = workbook.add_format(
            {"border": 1, "align": "left", "valign": "vcenter"}
        )

        weekend_cell_format = workbook.add_format(
            {"border": 1, "align": "center", "valign": "vcenter", "bg_color": "red"}
        )

        status_format = workbook.add_format(
            {"border": 1, "align": "center", "valign": "vcenter", "font_size": 9}
        )

        summary_header_format = workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "align": "center",
                "valign": "vcenter",
                "font_size": 8,
            }
        )

        signature_format = workbook.add_format({"align": "left", "valign": "vcenter"})

        underline_format = workbook.add_format({"underline": True, "bold": True})

        # Current row counter
        row = 0

        # Get academic year
        academic_year = f"{year}-{year + 1}" if month >= 7 else f"{year - 1}-{year}"

        # Title section
        title_col_end = 3 + days_in_month + 3  # NO, NO.INDUK, NAMA, days, S, I, A
        worksheet.merge_range(
            row, 0, row, title_col_end, "REKAP ABSENSI SISWA", title_format
        )
        row += 1

        worksheet.merge_range(
            row,
            0,
            row,
            title_col_end,
            "SEKOLAH MENENGAH PERTAMA KRISTEN PELITA KASIH",
            subtitle_format,
        )
        row += 1

        worksheet.merge_range(
            row, 0, row, title_col_end, f"TAHUN PELAJARAN {academic_year}", year_format
        )
        row += 2

        # Class info
        worksheet.write(row, 0, f"Kls / Smt", class_info_format)
        worksheet.write(row, 1, f": {class_display_name} /", class_info_format)
        row += 1

        worksheet.write(row, 0, "Wali Kelas", class_info_format)
        worksheet.write(row, 1, f": {wali_kelas_name}", class_info_format)
        row += 2

        # Table header row 1
        header_row = row
        worksheet.merge_range(header_row, 0, header_row + 1, 0, "NO.", header_format)
        worksheet.merge_range(
            header_row, 1, header_row + 1, 1, "NO.\nINDUK", header_format
        )

        # Month and NAMA header
        worksheet.write(header_row, 2, f"BULAN : {month_name}", header_format)
        worksheet.write(header_row + 1, 2, "NAMA", header_format)

        # PADA TANGGAL header
        worksheet.merge_range(
            header_row,
            3,
            header_row,
            3 + days_in_month - 1,
            "PADA TANGGAL",
            header_format,
        )

        # JUMLAH header
        jumlah_start_col = 3 + days_in_month
        worksheet.merge_range(
            header_row,
            jumlah_start_col,
            header_row,
            jumlah_start_col + 2,
            "JUMLAH",
            header_format,
        )

        # Date numbers (1-31) in second header row
        for day in range(1, days_in_month + 1):
            col = 2 + day
            # Check if weekend
            day_date = dt(year, month, day)
            is_weekend = day_date.weekday() >= 5  # Saturday=5, Sunday=6

            if is_weekend:
                worksheet.write(header_row + 1, col, day, weekend_header_format)
            else:
                worksheet.write(header_row + 1, col, day, date_header_format)

        # S, I, A headers
        worksheet.write(header_row + 1, jumlah_start_col, "S", summary_header_format)
        worksheet.write(
            header_row + 1, jumlah_start_col + 1, "I", summary_header_format
        )
        worksheet.write(
            header_row + 1, jumlah_start_col + 2, "A", summary_header_format
        )

        row = header_row + 2

        # Get students for this class
        students = []
        if class_id:
            students = student_repository.get_all(
                class_id=class_id, is_active=True
            ).all()

        # Prepare start and end date for querying
        period_start = dt(year, month, 1).date()
        period_end = dt(year, month, days_in_month).date()

        # Write student data
        for idx, student in enumerate(students, start=1):
            # Write NO
            worksheet.write(row, 0, idx, cell_format)

            # Write NO. INDUK
            worksheet.write(row, 1, student.nis, cell_format)

            # Write NAMA
            worksheet.write(row, 2, student.name, cell_left_format)

            # Get attendance records for this student
            attendance_records = attendance_repository.get_by_student(
                nis=student.nis, start_date=period_start, end_date=period_end
            )

            # Create a map of date -> status
            attendance_map = {}
            for record in attendance_records:
                attendance_map[record.attendance_date.day] = record.status

            # Counters for summary
            sick_count = 0
            permission_count = 0
            absent_count = 0

            # Write attendance for each day
            for day in range(1, days_in_month + 1):
                col = 2 + day
                day_date = dt(year, month, day)
                is_weekend = day_date.weekday() >= 5

                # Only process attendance data if not weekend
                status = attendance_map.get(day, "") if not is_weekend else ""
                display_text = ""

                # Map status to display text
                if status:
                    status_lower = status.lower()
                    if status_lower == "sick":
                        display_text = "s"
                        sick_count += 1
                    elif status_lower == "permission":
                        display_text = "i"
                        permission_count += 1
                    elif status_lower == "absent":
                        display_text = "a"
                        absent_count += 1
                    # Present and Late show nothing (as per screenshot)

                if is_weekend:
                    worksheet.write(row, col, display_text, weekend_cell_format)
                else:
                    worksheet.write(row, col, display_text, status_format)

            # Write summary columns
            worksheet.write(
                row, jumlah_start_col, sick_count if sick_count > 0 else "", cell_format
            )
            worksheet.write(
                row,
                jumlah_start_col + 1,
                permission_count if permission_count > 0 else "",
                cell_format,
            )
            worksheet.write(
                row,
                jumlah_start_col + 2,
                absent_count if absent_count > 0 else "",
                cell_format,
            )

            row += 1

        # Add some empty rows
        row += 3

        # Signature section
        # Left side - Kepala Sekolah
        worksheet.write(row, 0, "Mengetahui,", signature_format)
        row += 1
        worksheet.write(row, 0, "Kepala Sekolah", signature_format)

        # Right side - Guru
        city_name = "Lawang"  # Default city
        worksheet.write(
            row - 1, jumlah_start_col - 5, f"{city_name},", signature_format
        )
        worksheet.write(row, jumlah_start_col - 5, "Guru", signature_format)

        row += 4

        # Signature lines (underlined names)
        worksheet.write(row, 0, "Herawati Dewiani, S.Pd, M.M", underline_format)

        # Set column widths
        worksheet.set_column(0, 0, 4)  # NO
        worksheet.set_column(1, 1, 8)  # NO. INDUK
        worksheet.set_column(2, 2, 30)  # NAMA
        worksheet.set_column(3, 2 + days_in_month, 3)  # Date columns
        worksheet.set_column(
            jumlah_start_col, jumlah_start_col + 2, 3
        )  # S, I, A columns

        workbook.close()
        output.seek(0)
        return output

    def _generate_risk_excel(self, report_data: Dict[str, Any]) -> BytesIO:
        """Generate Excel file for risk report."""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Risk Report")

        # Add formats
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#4472C4", "font_color": "white", "border": 1}
        )

        # Write headers
        headers = ["NIS", "Name", "Class", "Risk Level", "Risk Score"]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Write student data
        for row, student in enumerate(report_data["students"], start=1):
            worksheet.write(row, 0, student["nis"])
            worksheet.write(row, 1, student["name"])
            worksheet.write(row, 2, student["class_id"])
            worksheet.write(row, 3, student["risk_level"])
            worksheet.write(row, 4, student["risk_score"])

        # Auto-fit columns
        worksheet.set_column("A:A", 12)
        worksheet.set_column("B:B", 25)
        worksheet.set_column("C:C", 12)
        worksheet.set_column("D:D", 12)
        worksheet.set_column("E:E", 12)

        workbook.close()
        output.seek(0)
        return output

    def _generate_class_summary_excel(self, report_data: Dict[str, Any]) -> BytesIO:
        """Generate Excel file for class summary report."""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Class Summary")

        # Add formats
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#4472C4", "font_color": "white", "border": 1}
        )

        # Write headers
        headers = [
            "Class ID",
            "Class Name",
            "Wali Kelas",
            "Students",
            "Attendance Rate",
            "At Risk",
        ]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Write class data
        for row, class_data in enumerate(report_data["classes"], start=1):
            worksheet.write(row, 0, class_data["class_id"])
            worksheet.write(row, 1, class_data["class_name"])
            worksheet.write(
                row,
                2,
                (
                    class_data["wali_kelas"]["name"]
                    if class_data.get("wali_kelas")
                    else ""
                ),
            )
            worksheet.write(row, 3, class_data["student_count"])

            # Get attendance rate from stats
            stats = class_data.get("attendance_statistics", {})
            rate = stats.get("average_attendance_rate", 0)
            worksheet.write(row, 4, f"{rate}%")

            worksheet.write(row, 5, class_data["at_risk_students"])

        # Auto-fit columns
        worksheet.set_column("A:A", 12)
        worksheet.set_column("B:B", 20)
        worksheet.set_column("C:C", 25)
        worksheet.set_column("D:D", 10)
        worksheet.set_column("E:E", 15)
        worksheet.set_column("F:F", 10)

        workbook.close()
        output.seek(0)
        return output


# Singleton instance
report_service = ReportService()
