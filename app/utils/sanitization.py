"""This file contains the sanitization utilities for the application."""

import html
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)


def sanitize_string(value: str) -> str:
    """Sanitize a string to prevent XSS and other injection attacks.

    Args:
        value: The string to sanitize

    Returns:
        str: The sanitized string
    """
    # Convert to string if not already
    if not isinstance(value, str):
        value = str(value)

    # HTML escape to prevent XSS
    value = html.escape(value)

    # Remove any script tags that might have been escaped
    value = re.sub(r"&lt;script.*?&gt;.*?&lt;/script&gt;", "", value, flags=re.DOTALL)

    # Remove null bytes
    value = value.replace("\0", "")

    return value


def sanitize_email(email: str) -> str:
    """Sanitize an email address.

    Args:
        email: The email address to sanitize

    Returns:
        str: The sanitized email address
    """
    # Basic sanitization
    email = sanitize_string(email)

    # Ensure email format (simple check)
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        raise ValueError("Invalid email format")

    return email.lower()


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively sanitize all string values in a dictionary.

    Args:
        data: The dictionary to sanitize

    Returns:
        Dict[str, Any]: The sanitized dictionary
    """
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = sanitize_list(value)
        else:
            sanitized[key] = value
    return sanitized


def sanitize_list(data: List[Any]) -> List[Any]:
    """Recursively sanitize all string values in a list.

    Args:
        data: The list to sanitize

    Returns:
        List[Any]: The sanitized list
    """
    sanitized = []
    for item in data:
        if isinstance(item, str):
            sanitized.append(sanitize_string(item))
        elif isinstance(item, dict):
            sanitized.append(sanitize_dict(item))
        elif isinstance(item, list):
            sanitized.append(sanitize_list(item))
        else:
            sanitized.append(item)
    return sanitized


def validate_password_strength(password: str) -> bool:
    """Validate password strength.

    Args:
        password: The password to validate

    Returns:
        bool: Whether the password is strong enough

    Raises:
        ValueError: If the password is not strong enough with reason
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")

    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")

    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one number")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError("Password must contain at least one special character")

    return True


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal and other attacks.

    Args:
        filename: The filename to sanitize

    Returns:
        str: The sanitized filename
    """
    # Remove path separators and dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Remove path traversal attempts
    filename = re.sub(r'\.\./', '', filename)
    filename = re.sub(r'\.\.\\', '', filename)
    
    # Remove null bytes
    filename = filename.replace('\0', '')
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    return filename


def sanitize_sql_like_pattern(pattern: str) -> str:
    """Sanitize a SQL LIKE pattern to prevent injection.

    Args:
        pattern: The pattern to sanitize

    Returns:
        str: The sanitized pattern
    """
    # Escape SQL LIKE special characters
    pattern = pattern.replace('\\', '\\\\')
    pattern = pattern.replace('%', '\\%')
    pattern = pattern.replace('_', '\\_')
    pattern = pattern.replace('[', '\\[')
    
    return pattern


def validate_uuid_string(uuid_str: str) -> str:
    """Validate that a string is a valid UUID format.

    Args:
        uuid_str: The UUID string to validate

    Returns:
        str: The validated UUID string

    Raises:
        ValueError: If the UUID format is invalid
    """
    import uuid
    try:
        uuid.UUID(uuid_str)
        return uuid_str
    except ValueError:
        raise ValueError("Invalid UUID format")


def sanitize_json_data(data: Any, max_depth: int = 10, current_depth: int = 0) -> Any:
    """Recursively sanitize JSON data with depth protection.

    Args:
        data: The data to sanitize
        max_depth: Maximum recursion depth
        current_depth: Current recursion depth

    Returns:
        Any: The sanitized data

    Raises:
        ValueError: If maximum depth is exceeded
    """
    if current_depth > max_depth:
        raise ValueError("JSON data exceeds maximum depth")

    if isinstance(data, str):
        return sanitize_string(data)
    elif isinstance(data, dict):
        if len(data) > 1000:  # Limit dictionary size
            raise ValueError("Dictionary too large")
        return {
            sanitize_string(str(k)): sanitize_json_data(v, max_depth, current_depth + 1)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        if len(data) > 1000:  # Limit list size
            raise ValueError("List too large")
        return [sanitize_json_data(item, max_depth, current_depth + 1) for item in data]
    else:
        return data


def validate_ip_address(ip: str) -> str:
    """Validate an IP address format.

    Args:
        ip: The IP address to validate

    Returns:
        str: The validated IP address

    Raises:
        ValueError: If the IP address format is invalid
    """
    import ipaddress
    try:
        ipaddress.ip_address(ip)
        return ip
    except ValueError:
        raise ValueError("Invalid IP address format")


def sanitize_url(url: str) -> str:
    """Sanitize a URL to prevent various attacks.

    Args:
        url: The URL to sanitize

    Returns:
        str: The sanitized URL

    Raises:
        ValueError: If the URL is malformed or dangerous
    """
    from urllib.parse import urlparse, urlunparse

    # Basic sanitization
    url = sanitize_string(url)
    
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        raise ValueError("Invalid URL format")
    
    # Validate scheme
    allowed_schemes = ['http', 'https', 'ftp', 'ftps']
    if parsed.scheme not in allowed_schemes:
        raise ValueError(f"URL scheme must be one of: {', '.join(allowed_schemes)}")
    
    # Check for dangerous patterns
    dangerous_patterns = [
        'javascript:', 'data:', 'vbscript:', 'file:', 'about:'
    ]
    
    url_lower = url.lower()
    for pattern in dangerous_patterns:
        if pattern in url_lower:
            raise ValueError("URL contains dangerous protocol")
    
    return url


def validate_content_type(content_type: str) -> str:
    """Validate HTTP content type.

    Args:
        content_type: The content type to validate

    Returns:
        str: The validated content type

    Raises:
        ValueError: If the content type is invalid
    """
    allowed_types = [
        'application/json',
        'application/x-www-form-urlencoded',
        'multipart/form-data',
        'text/plain',
        'text/html',
        'text/csv',
        'application/pdf',
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp'
    ]
    
    # Extract main content type (ignore parameters)
    main_type = content_type.split(';')[0].strip().lower()
    
    if main_type not in allowed_types:
        raise ValueError(f"Content type not allowed: {main_type}")
    
    return content_type


def sanitize_header_value(value: str) -> str:
    """Sanitize HTTP header value.

    Args:
        value: The header value to sanitize

    Returns:
        str: The sanitized header value
    """
    # Remove newlines to prevent header injection
    value = re.sub(r'[\r\n]', '', value)
    
    # Remove null bytes
    value = value.replace('\0', '')
    
    # Limit length
    if len(value) > 8192:  # HTTP header limit
        value = value[:8192]
    
    return value
