from flask import Blueprint, request, jsonify, current_app
from src.app.middleware import token_required
from src.services.master_data_service import MasterDataService
from src.services.machine_service import MachineService
from src.services.ingestion_service import IngestionService
from src.services.mapping_service import MappingService
from src.services.ml_service import MLService
import os
import uuid

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

def save_uploaded_file(file):
    filename = str(uuid.uuid4()) + "_" + file.filename
    filepath = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'tmp'), filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)
    return filepath, filename

# --- Import Endpoints ---

@api_v1.route('/import/master', methods=['POST'])
@token_required
def import_master(current_user):
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    
    try:
        filepath, _ = save_uploaded_file(file)
        result = MasterDataService.import_from_excel(filepath)
        os.remove(filepath) # Cleanup
        return jsonify({'success': True, 'data': result}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v1.route('/import/users-sync', methods=['POST'])
@token_required
def import_users_sync(current_user):
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
        
    machine_code = request.form.get('machine_code')
    if not machine_code:
        return jsonify({'message': 'machine_code is required'}), 400

    try:
        filepath, _ = save_uploaded_file(file)
        result = MachineService.sync_users_from_excel(filepath, machine_code)
        os.remove(filepath)
        return jsonify({'success': True, 'data': result}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v1.route('/import/attendance', methods=['POST'])
@token_required
def import_attendance(current_user):
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    
    machine_code = request.form.get('machine_code')
    if not machine_code:
        return jsonify({'message': 'machine_code is required'}), 400
        
    try:
        filepath, filename = save_uploaded_file(file)
        result = IngestionService.import_logs_from_excel(filepath, filename, machine_code)
        os.remove(filepath)
        return jsonify({'success': True, 'data': result}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# --- Batch Management Endpoints ---
from src.services.batch_service import batch_service
from src.app.middleware import role_required


@api_v1.route('/import/batches', methods=['GET'])
@token_required
def list_batches(current_user):
    """List all import batches with pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    file_type = request.args.get('file_type')
    status = request.args.get('status')
    
    batches, pagination = batch_service.list_batches(
        page=page,
        per_page=per_page,
        file_type=file_type,
        status=status
    )
    
    return jsonify({
        'success': True,
        'message': 'Batches retrieved successfully',
        'data': batches,
        'pagination': pagination
    }), 200


@api_v1.route('/import/batches/<int:batch_id>', methods=['GET'])
@token_required
def get_batch(current_user, batch_id):
    """Get details of a specific import batch."""
    batch, error = batch_service.get_batch(batch_id)
    
    if error:
        return jsonify({
            'success': False,
            'error': {'code': 'NOT_FOUND', 'message': error}
        }), 404
    
    return jsonify({
        'success': True,
        'message': 'Batch retrieved successfully',
        'data': batch
    }), 200


@api_v1.route('/import/batches/<int:batch_id>', methods=['DELETE'])
@token_required
@role_required(['Admin'])
def delete_batch(current_user, batch_id):
    """Delete an import batch and its raw logs. Admin only."""
    success, deleted_count, error = batch_service.delete_batch(batch_id)
    
    if not success:
        return jsonify({
            'success': False,
            'error': {'code': 'DELETE_FAILED', 'message': error}
        }), 404 if error == "Batch not found" else 500
    
    return jsonify({
        'success': True,
        'message': 'Batch deleted successfully',
        'data': {'deleted_raw_logs': deleted_count}
    }), 200


@api_v1.route('/import/batches/<int:batch_id>/rollback', methods=['POST'])
@token_required
@role_required(['Admin'])
def rollback_batch(current_user, batch_id):
    """Rollback an import batch - delete raw logs and mark as rolled back. Admin only."""
    success, deleted_count, error = batch_service.rollback_batch(batch_id)
    
    if not success:
        status_code = 404 if error == "Batch not found" else 400
        return jsonify({
            'success': False,
            'error': {'code': 'ROLLBACK_FAILED', 'message': error}
        }), status_code
    
    return jsonify({
        'success': True,
        'message': 'Batch rolled back successfully',
        'data': {'deleted_raw_logs': deleted_count}
    }), 200

# --- Mapping Endpoints ---

@api_v1.route('/mapping/process', methods=['POST'])
@token_required
def run_mapping_process(current_user):
    try:
        threshold = int(request.json.get('threshold', 90))
        result = MappingService.run_auto_mapping(threshold)
        return jsonify({'success': True, 'data': result}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v1.route('/mapping/suggestions', methods=['GET'])
@token_required
def get_mapping_suggestions(current_user):
    try:
        suggestions = MappingService.get_mapping_suggestions()
        return jsonify({'success': True, 'data': suggestions}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v1.route('/mapping/verify', methods=['POST'])
@token_required
def verify_mapping(current_user):
    try:
        mapping_id = request.json.get('mapping_id')
        status = request.json.get('status', 'verified') # verified or rejected
        
        if not mapping_id:
             return jsonify({'message': 'mapping_id is required'}), 400
             
        success = MappingService.verify_mapping(mapping_id, current_user.id, status)
        if success:
             return jsonify({'success': True}), 200
        else:
             return jsonify({'success': False, 'message': 'Mapping not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# --- ML Endpoints ---

@api_v1.route('/models/train', methods=['POST'])
@token_required
def train_models(current_user):
    try:
        result = MLService.train_models()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v1.route('/risk/<nis>', methods=['GET'])
@token_required
def get_risk_score(current_user, nis):
    try:
        result = MLService.predict_risk(nis)
        return jsonify({'success': True, 'data': result}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
