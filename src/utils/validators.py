"""
Common validation utilities for input data.
"""
import re
from typing import List, Tuple, Optional


def validate_phone_format(phone: str) -> bool:
    """
    Validate Indonesian phone number format.
    
    Accepts formats:
    - 08xxxxxxxxx (10-13 digits starting with 08)
    - +628xxxxxxxxx (with country code)
    - 628xxxxxxxxx (without plus)
    
    Args:
        phone: Phone number string
    
    Returns:
        bool: True if valid format
    """
    if not phone:
        return True  # Empty is valid (optional field)
    
    # Remove spaces and dashes
    cleaned = re.sub(r'[\s\-]', '', phone)
    
    # Pattern for Indonesian phone numbers
    patterns = [
        r'^08\d{8,11}$',        # 08xxxxxxxxx
        r'^\+628\d{8,11}$',     # +628xxxxxxxxx
        r'^628\d{8,11}$',       # 628xxxxxxxxx
    ]
    
    return any(re.match(pattern, cleaned) for pattern in patterns)


def validate_required_fields(data: dict, required: List[str]) -> List[str]:
    """
    Check if all required fields are present and non-empty.
    
    Args:
        data: Dictionary of field values
        required: List of required field names
    
    Returns:
        List[str]: List of missing or empty field names
    """
    missing = []
    for field in required:
        value = data.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ''):
            missing.append(field)
    return missing


def validate_sort_params(
    sort_by: Optional[str],
    order: Optional[str],
    allowed_fields: List[str]
) -> Tuple[Optional[str], str]:
    """
    Validate and normalize sorting parameters.
    
    Args:
        sort_by: Field to sort by
        order: Sort order ('asc' or 'desc')
        allowed_fields: List of allowed sort fields
    
    Returns:
        Tuple[Optional[str], str]: (validated_sort_by, validated_order)
    """
    # Validate sort_by
    if sort_by and sort_by not in allowed_fields:
        sort_by = None
    
    # Validate and normalize order
    if order:
        order = order.lower()
        if order not in ('asc', 'desc'):
            order = 'asc'
    else:
        order = 'asc'
    
    return sort_by, order


def validate_boolean_param(value: Optional[str]) -> Optional[bool]:
    """
    Parse boolean query parameter.
    
    Args:
        value: String value from query params
    
    Returns:
        Optional[bool]: Parsed boolean or None if invalid
    """
    if value is None:
        return None
    
    value_lower = value.lower()
    if value_lower in ('true', '1', 'yes'):
        return True
    elif value_lower in ('false', '0', 'no'):
        return False
    
    return None


def sanitize_string(value: Optional[str], max_length: int = 255) -> Optional[str]:
    """
    Sanitize and trim string input.
    
    Args:
        value: Input string
        max_length: Maximum allowed length
    
    Returns:
        Optional[str]: Sanitized string or None
    """
    if value is None:
        return None
    
    # Strip whitespace
    sanitized = value.strip()
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized if sanitized else None
