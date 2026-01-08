"""
Mapping API endpoints.
Provides enhanced mapping management operations.
"""

from flask import Blueprint, request

from src.app.middleware import token_required
from src.services.mapping_service import mapping_service
from src.schemas.mapping_schema import (
    manual_mapping_create_schema,
    bulk_mapping_create_schema,
)
from src.utils.response_helpers import (
    success_response,
    created_response,
    paginated_response,
    not_found_response,
    validation_error_response,
    error_response,
)
from src.utils.pagination import get_pagination_params
from src.utils.validators import validate_boolean_param


mapping_bp = Blueprint("mapping", __name__, url_prefix="/api/v1/mapping")


@mapping_bp.route("/unmapped", methods=["GET"])
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
    page, per_page, _ = get_pagination_params(request.args)

    # Get filter params
    machine_id = request.args.get("machine_id", type=int)
    include_suggestions = validate_boolean_param(
        request.args.get("include_suggestions", "true")
    )
    if include_suggestions is None:
        include_suggestions = True

    result = mapping_service.get_unmapped_users(
        page=page,
        per_page=per_page,
        machine_id=machine_id,
        include_suggestions=include_suggestions,
    )

    return paginated_response(
        data=result["data"],
        pagination=result["pagination"],
        message="Unmapped users retrieved successfully",
    )


@mapping_bp.route("/unmapped-students", methods=["GET"])
@token_required
def get_unmapped_students(current_user):
    """
    Get list of students without mappings to any machine user.

    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - class_id: Filter by class ID
        - search: Search by name/NIS
        - is_active: Filter by active status (default: true)

    Returns:
        Paginated list of unmapped students
    """
    # Get pagination params
    page, per_page, _ = get_pagination_params(request.args)

    # Filters
    class_id = request.args.get("class_id")
    search = request.args.get("search")
    is_active = validate_boolean_param(request.args.get("is_active", "true"))
    if is_active is None:
        is_active = True

    result = mapping_service.get_unmapped_students(
        page=page,
        per_page=per_page,
        class_id=class_id,
        is_active=is_active,
        search=search,
    )

    return paginated_response(
        data=result["data"],
        pagination=result["pagination"],
        message="Unmapped students retrieved successfully",
    )


@mapping_bp.route("/bulk-verify", methods=["POST"])
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
            {"_schema": ["Request body is required"]}, message="Invalid request"
        )

    result, errors = mapping_service.bulk_verify_mappings(data, current_user.id)

    if errors:
        return validation_error_response(errors)

    return success_response(data=result, message="Bulk verification completed")


@mapping_bp.route("/stats", methods=["GET"])
@token_required
def get_mapping_stats(current_user):
    """
    Get mapping statistics.

    Returns:
        Mapping statistics including total, mapped, verified, suggested counts
    """
    stats = mapping_service.get_mapping_stats()

    return success_response(
        data=stats, message="Mapping statistics retrieved successfully"
    )


@mapping_bp.route("/<int:mapping_id>", methods=["DELETE"])
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


@mapping_bp.route("/<int:mapping_id>", methods=["GET"])
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

    return success_response(data=mapping_data, message="Mapping retrieved successfully")


@mapping_bp.route("/list", methods=["GET"])
@token_required
def get_mappings_list(current_user):
    """
    Get paginated list of all mappings.

    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - status: Filter by status (verified, suggested, rejected)
        - machine_id: Filter by machine ID
        - class_id: Filter by student class ID
        - search: Search by student or machine user name

    Returns:
        Paginated list of mappings with machine user and student details
    """
    # Get pagination params
    page, per_page, _ = get_pagination_params(request.args)

    # Get filter params
    status = request.args.get("status")
    machine_id = request.args.get("machine_id", type=int)
    class_id = request.args.get("class_id")
    search = request.args.get("search")

    result = mapping_service.get_mappings_list(
        page=page,
        per_page=per_page,
        status=status,
        machine_id=machine_id,
        class_id=class_id,
        search=search,
    )

    return paginated_response(
        data=result["data"],
        pagination=result["pagination"],
        message="Mappings retrieved successfully",
    )


@mapping_bp.route("/student/<string:student_nis>", methods=["DELETE"])
@token_required
def unmap_student(current_user, student_nis):
    """
    Remove mapping for a specific student (unmap student).

    Path Parameters:
        - student_nis: Student NIS

    Returns:
        Success message
    """
    success, error = mapping_service.unmap_student(student_nis)

    if not success:
        return not_found_response("Student mapping")

    return success_response(message="Student unmapped successfully")


@mapping_bp.route("/manual", methods=["POST"])
@token_required
def create_manual_mapping(current_user):
    """
    Create a single manual mapping between a machine user and a student.

    Request Body:
        {
            "machine_user_id": 123,
            "student_nis": "2024001",
            "status": "verified"  // optional, default: "verified"
        }

    Returns:
        Created mapping data
    """
    data = request.get_json()

    if not data:
        return validation_error_response(
            {"_schema": ["Request body is required"]}, message="Invalid request"
        )

    # Validate input
    errors = manual_mapping_create_schema.validate(data)
    if errors:
        return validation_error_response(errors)

    validated_data = manual_mapping_create_schema.load(data)

    # Create mapping
    mapping_data, create_errors = mapping_service.create_manual_mapping(
        machine_user_id=validated_data["machine_user_id"],
        student_nis=validated_data["student_nis"],
        admin_user_id=current_user.id,
        status=validated_data.get("status", "verified"),
    )

    if create_errors:
        return validation_error_response(create_errors)

    return created_response(data=mapping_data, message="Mapping created successfully")


@mapping_bp.route("/bulk-create", methods=["POST"])
@token_required
def bulk_create_mappings(current_user):
    """
    Create multiple manual mappings at once.

    Request Body:
        {
            "mappings": [
                {"machine_user_id": 123, "student_nis": "2024001"},
                {"machine_user_id": 124, "student_nis": "2024002"}
            ]
        }

    Returns:
        Results with created/failed counts and created mappings
    """
    data = request.get_json()

    if not data:
        return validation_error_response(
            {"_schema": ["Request body is required"]}, message="Invalid request"
        )

    # Validate input
    errors = bulk_mapping_create_schema.validate(data)
    if errors:
        return validation_error_response(errors)

    validated_data = bulk_mapping_create_schema.load(data)

    # Create mappings
    results, create_errors = mapping_service.bulk_create_mappings(
        mappings_data=validated_data["mappings"],
        admin_user_id=current_user.id,
    )

    if create_errors:
        return validation_error_response(create_errors)

    return success_response(data=results, message="Bulk mapping creation completed")
