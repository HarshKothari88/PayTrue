from typing import Dict, Tuple, Any
from functools import wraps
from flask import jsonify

class AuthenticationError(Exception):
    """Base exception for authentication errors."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code
        self.message = message

class CustomFileNotFoundError(FileNotFoundError):
    """Custom exception for file not found errors."""
    def __init__(self, message: str = "File not found.", status_code: int = 404):
        super().__init__(message)
        self.status_code = status_code
        self.message = message

class ContentTooLarge(Exception):
    """Custom exception for Content or Value too large"""
    def __init__(self, message: str = "Value too large", status_code: int = 413):
        super().__init__(message)
        self.status_code = status_code
        self.message = message

def handle_errors(f):
    """Decorator to handle errors in route handlers."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except AuthenticationError as e:
            return jsonify({
                'success': False,
                'error': e.message
            }), e.status_code
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f"An unexpected error occurred: {str(e)}"
            }), 500
    return decorated_function

def create_error_response(message: str, status_code: int = 400) -> Tuple[Dict[str, Any], int]:
    """Create a standardized error response."""
    return {
        'success': False,
        'error': message
    }, status_code

def create_success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a standardized success response."""
    return {
        'success': True,
        'data': data
    }