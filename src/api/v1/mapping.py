"""
Mapping API endpoints.
Provides enhanced mapping management operations.
"""
from flask import Blueprint, request

from src.app.middleware import token_required
from src.services.mapping_service import mapping_service
from src.utils.response_helpers import (
    success_response,
    paginated_response,
    not_found_response,
    validation_error_response
)
from src.utils.pagination import get_pagination_params
from src.utils.validators import validate_boolean_param


mapping_bp = Blueprint('mapping', __name__, url_prefix='/api/v1/mapping')


@mapping_bp.route('/unmapped', methods=['GET'])
@token_required
def get_unmapped_users(current_user):
    """
    Get list of machine users without student mappings.
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - machine_id: Filter by machine ID
        - include_suggestions: Include suggested matches (default: true)
    
    Returns:
        Paginated list of unmapped users with suggested matches
    """
    # Get pagination params
    page, per_page = get_pagination_params(request.args)
    
    # Get filter params
    machine_id = request.args.get('machine_id', type=int)
    include_suggestions = validate_boolean_param(
        request.args.get('include_suggestions', 'true')
    )
    if include_suggestions is None:
        include_suggestions = True
    
    result = mapping_service.get_unmapped_users(
        page=page,
        per_page=per_page,
        machine_id=machine_id,
        include_suggestions=include_suggestions
    )
    
    return paginated_response(
        data=result["data"],
        pagination=result["pagination"],
        message="Unmapped users retrieved successfully"
    )


@mapping_bp.route('/bulk-verify', methods=['POST'])
@token_required
def bulk_verify_mappings(current_user):
    """
    Bulk verify or reject mappings.
    
    Request Body:
        {
            "mappings": [
                {"mapping_id": 1, "status": "verified"},
                {"mapping_id": 2, "status": "rejected", "reason": "Wrong person"}
            ]
        }
    
    Returns:
        Results with verified/rejected/failed counts
    """
    data = request.get_json()
    
    if not data:
        return validation_error_response(
            {"_schema": ["Request body is required"]},
            message="Invalid request"
        )
    
    result, errors = mapping_service.bulk_verify_mappings(data, current_user.id)
    
    if errors:
        return validation_error_response(errors)
    
    return success_response(
        data=result,
        message="Bulk verification completed"
    )


@mapping_bp.route('/stats', methods=['GET'])
@token_required
def get_mapping_stats(current_user):
    """
    Get mapping statistics.
    
    Returns:
        Mapping statistics including total, mapped, verified, suggested counts
    """
    stats = mapping_service.get_mapping_stats()
    
    return success_response(
        data=stats,
        message="Mapping statistics retrieved successfully"
    )


@mapping_bp.route('/<int:mapping_id>', methods=['DELETE'])
@token_required
def delete_mapping(current_user, mapping_id):
    """
    Delete a mapping.
    
    Path Parameters:
        - mapping_id: Mapping ID
    
    Returns:
        Success message
    """
    success, error = mapping_service.delete_mapping(mapping_id)
    
    if not success:
        return not_found_response("Mapping")
    
    return success_response(message="Mapping deleted successfully")


@mapping_bp.route('/<int:mapping_id>', methods=['GET'])
@token_required
def get_mapping(current_user, mapping_id):
    """
    Get a single mapping by ID.
    
    Path Parameters:
        - mapping_id: Mapping ID
    
    Returns:
        Mapping details
    """
    mapping_data, error = mapping_service.get_mapping(mapping_id)
    
    if error:
        return not_found_response("Mapping")
    
    return success_response(
        data=mapping_data,
        message="Mapping retrieved successfully"
    )
