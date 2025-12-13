"""
Standardized API response helpers.
Ensures consistent response format across all endpoints.
"""
from flask import jsonify
from typing import Any, Optional


def success_response(data: Any = None, message: str = "Success", status_code: int = 200):
    """
    Create a standardized success response.
    
    Args:
        data: Response data (dict, list, or any serializable object)
        message: Success message
        status_code: HTTP status code (default: 200)
    
    Returns:
        tuple: (Flask Response, status_code)
    """
    response = {
        "success": True,
        "message": message
    }
    
    if data is not None:
        response["data"] = data
    
    return jsonify(response), status_code


def error_response(
    message: str,
    code: str = "ERROR",
    details: Optional[dict] = None,
    status_code: int = 400
):
    """
    Create a standardized error response.
    
    Args:
        message: Error message
        code: Error code (e.g., "VALIDATION_ERROR", "NOT_FOUND")
        details: Additional error details (e.g., field-level errors)
        status_code: HTTP status code (default: 400)
    
    Returns:
        tuple: (Flask Response, status_code)
    """
    response = {
        "success": False,
        "error": {
            "code": code,
            "message": message
        }
    }
    
    if details is not None:
        response["error"]["details"] = details
    
    return jsonify(response), status_code


def paginated_response(
    data: list,
    pagination: dict,
    message: str = "Success",
    status_code: int = 200
):
    """
    Create a standardized paginated response.
    
    Args:
        data: List of items
        pagination: Pagination metadata dict
        message: Success message
        status_code: HTTP status code (default: 200)
    
    Returns:
        tuple: (Flask Response, status_code)
    """
    response = {
        "success": True,
        "message": message,
        "data": data,
        "pagination": pagination
    }
    
    return jsonify(response), status_code


def created_response(data: Any = None, message: str = "Created successfully"):
    """
    Create a standardized 201 Created response.
    
    Args:
        data: Created resource data
        message: Success message
    
    Returns:
        tuple: (Flask Response, 201)
    """
    return success_response(data=data, message=message, status_code=201)


def not_found_response(resource: str = "Resource"):
    """
    Create a standardized 404 Not Found response.
    
    Args:
        resource: Name of the resource not found
    
    Returns:
        tuple: (Flask Response, 404)
    """
    return error_response(
        message=f"{resource} not found",
        code="NOT_FOUND",
        status_code=404
    )


def validation_error_response(details: dict, message: str = "Validation failed"):
    """
    Create a standardized validation error response.
    
    Args:
        details: Field-level validation errors
        message: Error message
    
    Returns:
        tuple: (Flask Response, 400)
    """
    return error_response(
        message=message,
        code="VALIDATION_ERROR",
        details=details,
        status_code=400
    )


def conflict_response(message: str):
    """
    Create a standardized 409 Conflict response.
    
    Args:
        message: Conflict description
    
    Returns:
        tuple: (Flask Response, 409)
    """
    return error_response(
        message=message,
        code="CONFLICT",
        status_code=409
    )
