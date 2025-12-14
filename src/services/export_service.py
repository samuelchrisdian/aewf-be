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
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Students')
        
        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })
        
        # Write headers
        headers = ['NIS', 'Name', 'Class ID', 'Class Name', 'Parent Phone', 'Active']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write data
        for row, student in enumerate(students, start=1):
            worksheet.write(row, 0, student.nis)
            worksheet.write(row, 1, student.name)
            worksheet.write(row, 2, student.class_id)
            worksheet.write(row, 3, student.class_obj.class_name if student.class_obj else '')
            worksheet.write(row, 4, student.parent_phone or '')
            worksheet.write(row, 5, 'Yes' if student.is_active else 'No')
        
        # Auto-fit columns
        worksheet.set_column('A:A', 12)  # NIS
        worksheet.set_column('B:B', 25)  # Name
        worksheet.set_column('C:C', 12)  # Class ID
        worksheet.set_column('D:D', 20)  # Class Name
        worksheet.set_column('E:E', 15)  # Phone
        worksheet.set_column('F:F', 10)  # Active
        
        workbook.close()
        output.seek(0)
        
        return output
    
    def export_attendance_excel(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        class_id: Optional[str] = None
    ) -> BytesIO:
        """
        Export attendance records to Excel file.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            class_id: Optional filter by class
            
        Returns:
            BytesIO: Excel file buffer
        """
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
        
        # Get attendance records
        query = attendance_repository.get_daily(
            start_date=start_dt,
            end_date=end_dt,
            class_id=class_id
        )
        records = query.all()
        
        # Create Excel file in memory
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Attendance')
        
        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })
        
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        time_format = workbook.add_format({'num_format': 'hh:mm:ss'})
        
        # Write headers
        headers = [
            'Date', 'NIS', 'Student Name', 'Class', 
            'Status', 'Check In', 'Check Out', 'Notes'
        ]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write data
        for row, record in enumerate(records, start=1):
            worksheet.write(row, 0, record.attendance_date, date_format)
            worksheet.write(row, 1, record.student_nis)
            worksheet.write(row, 2, record.student.name if record.student else '')
            worksheet.write(row, 3, record.student.class_id if record.student else '')
            worksheet.write(row, 4, record.status)
            
            # Check in/out times
            if record.check_in:
                worksheet.write(row, 5, record.check_in, time_format)
            else:
                worksheet.write(row, 5, '')
                
            if record.check_out:
                worksheet.write(row, 6, record.check_out, time_format)
            else:
                worksheet.write(row, 6, '')
            
            worksheet.write(row, 7, record.notes or '')
        
        # Auto-fit columns
        worksheet.set_column('A:A', 12)  # Date
        worksheet.set_column('B:B', 12)  # NIS
        worksheet.set_column('C:C', 25)  # Name
        worksheet.set_column('D:D', 12)  # Class
        worksheet.set_column('E:E', 12)  # Status
        worksheet.set_column('F:F', 12)  # Check In
        worksheet.set_column('G:G', 12)  # Check Out
        worksheet.set_column('H:H', 30)  # Notes
        
        workbook.close()
        output.seek(0)
        
        return output
    
    def generate_master_template(self) -> BytesIO:
        """
        Generate master data import template Excel file.
        
        Returns:
            BytesIO: Excel file buffer
        """
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })
        
        example_format = workbook.add_format({
            'italic': True,
            'font_color': '#7F7F7F'
        })
        
        # Students sheet
        students_sheet = workbook.add_worksheet('Students')
        student_headers = ['nis', 'name', 'class_id', 'parent_phone']
        for col, header in enumerate(student_headers):
            students_sheet.write(0, col, header, header_format)
        
        # Add example row
        students_sheet.write(1, 0, '2024001', example_format)
        students_sheet.write(1, 1, 'John Doe', example_format)
        students_sheet.write(1, 2, 'X-IPA-1', example_format)
        students_sheet.write(1, 3, '081234567890', example_format)
        
        students_sheet.set_column('A:A', 12)
        students_sheet.set_column('B:B', 25)
        students_sheet.set_column('C:C', 12)
        students_sheet.set_column('D:D', 15)
        
        # Classes sheet
        classes_sheet = workbook.add_worksheet('Classes')
        class_headers = ['class_id', 'class_name', 'wali_kelas_id']
        for col, header in enumerate(class_headers):
            classes_sheet.write(0, col, header, header_format)
        
        # Add example row
        classes_sheet.write(1, 0, 'X-IPA-1', example_format)
        classes_sheet.write(1, 1, 'X IPA 1', example_format)
        classes_sheet.write(1, 2, 'T001', example_format)
        
        classes_sheet.set_column('A:A', 12)
        classes_sheet.set_column('B:B', 20)
        classes_sheet.set_column('C:C', 15)
        
        # Teachers sheet
        teachers_sheet = workbook.add_worksheet('Teachers')
        teacher_headers = ['teacher_id', 'name', 'phone', 'role']
        for col, header in enumerate(teacher_headers):
            teachers_sheet.write(0, col, header, header_format)
        
        # Add example row
        teachers_sheet.write(1, 0, 'T001', example_format)
        teachers_sheet.write(1, 1, 'Mrs. Sarah', example_format)
        teachers_sheet.write(1, 2, '081234567890', example_format)
        teachers_sheet.write(1, 3, 'Wali Kelas', example_format)
        
        teachers_sheet.set_column('A:A', 12)
        teachers_sheet.set_column('B:B', 25)
        teachers_sheet.set_column('C:C', 15)
        teachers_sheet.set_column('D:D', 15)
        
        workbook.close()
        output.seek(0)
        
        return output


# Singleton instance
export_service = ExportService()
