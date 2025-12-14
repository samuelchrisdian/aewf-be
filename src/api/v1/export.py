"""
Export API endpoints.
Provides data export operations.
"""
from flask import Blueprint, request, send_file

from src.app.middleware import token_required
from src.services.export_service import export_service
from src.utils.response_helpers import validation_error_response


export_bp = Blueprint('export', __name__, url_prefix='/api/v1/export')


@export_bp.route('/students', methods=['GET'])
@token_required
def export_students(current_user):
    """
    Export students to Excel file.
    
    Query Parameters:
        - class_id: Filter by class (optional)
    
    Returns:
        Excel file download
    """
    # Get query params
    class_id = request.args.get('class_id')
    
    try:
        # Generate Excel file
        excel_file = export_service.export_students_excel(class_id=class_id)
        
        # Determine filename
        filename = f'students_{class_id}.xlsx' if class_id else 'students.xlsx'
        
        # Return file
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        return validation_error_response(
            {'error': [str(e)]},
            message='Error exporting students'
        )


@export_bp.route('/attendance', methods=['GET'])
@token_required
def export_attendance(current_user):
    """
    Export attendance records to Excel file.
    
    Query Parameters:
        - start_date: Start date (YYYY-MM-DD)
        - end_date: End date (YYYY-MM-DD)
        - class_id: Filter by class (optional)
    
    Returns:
        Excel file download
    """
    # Get query params
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    class_id = request.args.get('class_id')
    
    # Validate date parameters
    if not start_date or not end_date:
        return validation_error_response(
            {'date': ['start_date and end_date are required']},
            message='Missing required parameters'
        )
    
    try:
        # Generate Excel file
        excel_file = export_service.export_attendance_excel(
            start_date=start_date,
            end_date=end_date,
            class_id=class_id
        )
        
        # Determine filename
        filename = f'attendance_{start_date}_{end_date}.xlsx'
        
        # Return file
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    except ValueError as e:
        return validation_error_response(
            {'date': [str(e)]},
            message='Invalid date format'
        )
    except Exception as e:
        return validation_error_response(
            {'error': [str(e)]},
            message='Error exporting attendance'
        )


@export_bp.route('/template/master', methods=['GET'])
@token_required
def download_master_template(current_user):
    """
    Download master data import template Excel file.
    
    Returns:
        Excel file download with template structure
    """
    try:
        # Generate template file
        template_file = export_service.generate_master_template()
        
        # Return file
        return send_file(
            template_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='master_data_template.xlsx'
        )
    
    except Exception as e:
        return validation_error_response(
            {'error': [str(e)]},
            message='Error generating template'
        )
