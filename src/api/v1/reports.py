"""
Reports API endpoints.
Provides report generation operations.
"""
from flask import Blueprint, request, send_file
from io import BytesIO

from src.app.middleware import token_required
from src.services.report_service import report_service
from src.utils.response_helpers import (
    success_response,
    validation_error_response
)


reports_bp = Blueprint('reports', __name__, url_prefix='/api/v1/reports')


@reports_bp.route('/attendance', methods=['GET'])
@token_required
def get_attendance_report(current_user):
    """
    Generate attendance report with statistics.
    
    Query Parameters:
        - format: 'json' (default) or 'excel'
        - start_date: Start date (YYYY-MM-DD)
        - end_date: End date (YYYY-MM-DD)
        - class_id: Filter by class (optional)
        - student_nis: Filter by student (optional)
    
    Returns:
        JSON report or Excel file download
    """
    # Get query params
    format_type = request.args.get('format', 'json')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    class_id = request.args.get('class_id')
    student_nis = request.args.get('student_nis')
    
    # Validate date parameters
    if not start_date or not end_date:
        return validation_error_response(
            {'date': ['start_date and end_date are required']},
            message='Missing required parameters'
        )
    
    try:
        # Generate report
        result = report_service.get_attendance_report(
            start_date=start_date,
            end_date=end_date,
            class_id=class_id,
            student_nis=student_nis,
            format=format_type
        )
        
        # If Excel format, return file
        if format_type == 'excel':
            return send_file(
                result,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'attendance_report_{start_date}_{end_date}.xlsx'
            )
        
        # Return JSON
        return success_response(
            data=result,
            message='Attendance report generated successfully'
        )
    
    except ValueError as e:
        return validation_error_response(
            {'date': [str(e)]},
            message='Invalid date format'
        )
    except Exception as e:
        return validation_error_response(
            {'error': [str(e)]},
            message='Error generating report'
        )


@reports_bp.route('/risk', methods=['GET'])
@token_required
def get_risk_report(current_user):
    """
    Generate risk report with at-risk students and interventions.
    
    Query Parameters:
        - format: 'json' (default) or 'excel'
        - class_id: Filter by class (optional)
    
    Returns:
        JSON report or Excel file download
    """
    # Get query params
    format_type = request.args.get('format', 'json')
    class_id = request.args.get('class_id')
    
    try:
        # Generate report
        result = report_service.get_risk_report(
            class_id=class_id,
            format=format_type
        )
        
        # If Excel format, return file
        if format_type == 'excel':
            return send_file(
                result,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'risk_report.xlsx'
            )
        
        # Return JSON
        return success_response(
            data=result,
            message='Risk report generated successfully'
        )
    
    except Exception as e:
        return validation_error_response(
            {'error': [str(e)]},
            message='Error generating report'
        )


@reports_bp.route('/class-summary', methods=['GET'])
@token_required
def get_class_summary_report(current_user):
    """
    Generate class summary report with statistics.
    
    Query Parameters:
        - format: 'json' (default) or 'excel'
        - start_date: Start date (YYYY-MM-DD)
        - end_date: End date (YYYY-MM-DD)
    
    Returns:
        JSON report or Excel file download
    """
    # Get query params
    format_type = request.args.get('format', 'json')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Validate date parameters
    if not start_date or not end_date:
        return validation_error_response(
            {'date': ['start_date and end_date are required']},
            message='Missing required parameters'
        )
    
    try:
        # Generate report
        result = report_service.get_class_summary_report(
            start_date=start_date,
            end_date=end_date,
            format=format_type
        )
        
        # If Excel format, return file
        if format_type == 'excel':
            return send_file(
                result,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'class_summary_{start_date}_{end_date}.xlsx'
            )
        
        # Return JSON
        return success_response(
            data=result,
            message='Class summary report generated successfully'
        )
    
    except ValueError as e:
        return validation_error_response(
            {'date': [str(e)]},
            message='Invalid date format'
        )
    except Exception as e:
        return validation_error_response(
            {'error': [str(e)]},
            message='Error generating report'
        )
