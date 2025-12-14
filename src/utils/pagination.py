"""
Pagination utility for SQLAlchemy queries.
Provides standardized pagination format across all API endpoints.
"""
import math


def paginate(query, page: int = 1, per_page: int = 20, max_per_page: int = 100):
    """
    Paginates a SQLAlchemy query and returns standardized format.
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        per_page: Items per page (default: 20)
        max_per_page: Maximum allowed items per page (default: 100)
    
    Returns:
        dict: {
            "items": [...],
            "pagination": {
                "page": 1,
                "per_page": 20,
                "total": 100,
                "pages": 5
            }
        }
    """
    # Validate and constrain parameters
    page = max(1, page)
    per_page = min(max(1, per_page), max_per_page)
    
    # Get total count
    total = query.count()
    
    # Calculate total pages
    pages = math.ceil(total / per_page) if total > 0 else 1
    
    # Ensure page doesn't exceed total pages
    page = min(page, pages)
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Get paginated items
    items = query.offset(offset).limit(per_page).all()
    
    return {
        "items": items,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages
        }
    }


def get_pagination_params(request_args: dict) -> tuple:
    """
    Extract pagination parameters from request arguments.
    
    Args:
        request_args: Flask request.args dict
    
    Returns:
        tuple: (page, per_page)
    """
    try:
        page = int(request_args.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    
    try:
        per_page = int(request_args.get('per_page', 20))
    except (ValueError, TypeError):
        per_page = 20
    
    return page, per_page


def paginate_query(query, page: int = 1, per_page: int = 20, max_per_page: int = 100):
    """
    Paginates a SQLAlchemy query and returns format with 'data' key.
    Alias for paginate() that returns 'data' instead of 'items' for service layer.
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        per_page: Items per page (default: 20)
        max_per_page: Maximum allowed items per page (default: 100)
    
    Returns:
        dict: {"data": [...], "pagination": {...}}
    """
    result = paginate(query, page, per_page, max_per_page)
    return {
        "data": result["items"],
        "pagination": result["pagination"]
    }

