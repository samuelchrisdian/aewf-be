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
        format: str = 'json'
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
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
        
        # Get attendance statistics
        stats = attendance_repository.get_summary_stats(
            class_id=class_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        # Get daily breakdown
        daily_breakdown = attendance_repository.get_daily_breakdown(
            class_id=class_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        # Build report data
        report_data = {
            'report_type': 'attendance',
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'filters': {
                'class_id': class_id,
                'student_nis': student_nis
            },
            'statistics': stats,
            'daily_breakdown': daily_breakdown,
            'generated_at': datetime.now().isoformat()
        }
        
        # If student-specific, add student details
        if student_nis:
            student = student_repository.get_by_nis(student_nis)
            if student:
                student_stats = attendance_repository.count_by_status(
                    nis=student_nis,
                    start_date=start_dt,
                    end_date=end_dt
                )
                report_data['student'] = {
                    'nis': student.nis,
                    'name': student.name,
                    'class_id': student.class_id,
                    'statistics': student_stats
                }
        
        if format == 'excel':
            return self._generate_attendance_excel(report_data)
        
        return report_data
    
    def get_risk_report(
        self,
        class_id: Optional[str] = None,
        format: str = 'json'
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
            'report_type': 'risk',
            'filters': {
                'class_id': class_id
            },
            'summary': {
                'total_at_risk': len(risk_students),
                'high_risk': sum(1 for s in risk_students if s.risk_level == 'high'),
                'medium_risk': sum(1 for s in risk_students if s.risk_level == 'medium'),
                'low_risk': sum(1 for s in risk_students if s.risk_level == 'low')
            },
            'students': [],
            'generated_at': datetime.now().isoformat()
        }
        
        # Add student details with interventions
        for risk_student in risk_students:
            student_data = {
                'nis': risk_student.student_nis,
                'name': risk_student.student.name if risk_student.student else '',
                'class_id': risk_student.student.class_id if risk_student.student else '',
                'risk_level': risk_student.risk_level,
                'risk_score': float(risk_student.risk_score) if risk_student.risk_score else 0,
                'factors': risk_student.factors or {},
                'last_updated': risk_student.last_updated.isoformat() if risk_student.last_updated else None
            }
            
            # Get intervention history if available
            if hasattr(risk_student, 'interventions'):
                student_data['interventions'] = [
                    {
                        'action': intervention.action,
                        'notes': intervention.notes,
                        'date': intervention.created_at.isoformat()
                    }
                    for intervention in risk_student.interventions
                ]
            
            report_data['students'].append(student_data)
        
        if format == 'excel':
            return self._generate_risk_excel(report_data)
        
        return report_data
    
    def get_class_summary_report(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        format: str = 'json'
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
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
        
        # Get all classes
        classes = class_repository.get_all().all()
        
        # Build report data
        report_data = {
            'report_type': 'class_summary',
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'classes': [],
            'generated_at': datetime.now().isoformat()
        }
        
        # Get statistics for each class
        for class_obj in classes:
            # Get attendance stats for this class
            stats = attendance_repository.get_summary_stats(
                class_id=class_obj.class_id,
                start_date=start_dt,
                end_date=end_dt
            )
            
            # Get risk count for this class
            risk_count = risk_repository.count_by_class(class_obj.class_id)
            
            class_data = {
                'class_id': class_obj.class_id,
                'class_name': class_obj.class_name,
                'wali_kelas': {
                    'teacher_id': class_obj.wali_kelas_id,
                    'name': class_obj.wali_kelas.name if class_obj.wali_kelas else ''
                } if class_obj.wali_kelas_id else None,
                'student_count': len(class_obj.students) if hasattr(class_obj, 'students') else 0,
                'attendance_statistics': stats,
                'at_risk_students': risk_count
            }
            
            report_data['classes'].append(class_data)
        
        if format == 'excel':
            return self._generate_class_summary_excel(report_data)
        
        return report_data
    
    def _generate_attendance_excel(self, report_data: Dict[str, Any]) -> BytesIO:
        """Generate Excel file for attendance report."""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Attendance Report')
        
        # Add formats
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'bg_color': '#4472C4',
            'font_color': 'white'
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9E1F2',
            'border': 1
        })
        
        # Write title
        worksheet.write('A1', 'Attendance Report', title_format)
        
        # Write period
        row = 2
        worksheet.write(row, 0, 'Period:', header_format)
        worksheet.write(row, 1, f"{report_data['period']['start_date']} to {report_data['period']['end_date']}")
        
        # Write statistics
        row += 2
        worksheet.write(row, 0, 'Statistics', title_format)
        row += 1
        
        stats = report_data['statistics']
        for key, value in stats.items():
            worksheet.write(row, 0, key.replace('_', ' ').title())
            worksheet.write(row, 1, value)
            row += 1
        
        workbook.close()
        output.seek(0)
        return output
    
    def _generate_risk_excel(self, report_data: Dict[str, Any]) -> BytesIO:
        """Generate Excel file for risk report."""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Risk Report')
        
        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })
        
        # Write headers
        headers = ['NIS', 'Name', 'Class', 'Risk Level', 'Risk Score']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write student data
        for row, student in enumerate(report_data['students'], start=1):
            worksheet.write(row, 0, student['nis'])
            worksheet.write(row, 1, student['name'])
            worksheet.write(row, 2, student['class_id'])
            worksheet.write(row, 3, student['risk_level'])
            worksheet.write(row, 4, student['risk_score'])
        
        # Auto-fit columns
        worksheet.set_column('A:A', 12)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 12)
        worksheet.set_column('D:D', 12)
        worksheet.set_column('E:E', 12)
        
        workbook.close()
        output.seek(0)
        return output
    
    def _generate_class_summary_excel(self, report_data: Dict[str, Any]) -> BytesIO:
        """Generate Excel file for class summary report."""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Class Summary')
        
        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })
        
        # Write headers
        headers = ['Class ID', 'Class Name', 'Wali Kelas', 'Students', 'Attendance Rate', 'At Risk']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write class data
        for row, class_data in enumerate(report_data['classes'], start=1):
            worksheet.write(row, 0, class_data['class_id'])
            worksheet.write(row, 1, class_data['class_name'])
            worksheet.write(row, 2, class_data['wali_kelas']['name'] if class_data.get('wali_kelas') else '')
            worksheet.write(row, 3, class_data['student_count'])
            
            # Get attendance rate from stats
            stats = class_data.get('attendance_statistics', {})
            rate = stats.get('average_attendance_rate', 0)
            worksheet.write(row, 4, f"{rate}%")
            
            worksheet.write(row, 5, class_data['at_risk_students'])
        
        # Auto-fit columns
        worksheet.set_column('A:A', 12)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 25)
        worksheet.set_column('D:D', 10)
        worksheet.set_column('E:E', 15)
        worksheet.set_column('F:F', 10)
        
        workbook.close()
        output.seek(0)
        return output


# Singleton instance
report_service = ReportService()
