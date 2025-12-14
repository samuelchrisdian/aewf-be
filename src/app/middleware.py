from functools import wraps
from flask import request, jsonify, current_app
import jwt
from src.domain.models import User

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['user_id']).first()
            if not current_user:
                 return jsonify({'message': 'User not found!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401
        except Exception as e:
            return jsonify({'message': f'Token error: {str(e)}'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


def role_required(allowed_roles):
    """
    Decorator to restrict access based on user role.
    Must be used AFTER @token_required decorator.
    
    Args:
        allowed_roles: List of allowed role names (e.g., ['Admin', 'Teacher'])
    
    Usage:
        @route('/admin-only')
        @token_required
        @role_required(['Admin'])
        def admin_only(current_user):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if current_user.role not in allowed_roles:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'ACCESS_DENIED',
                        'message': f'Access denied. Required role: {", ".join(allowed_roles)}'
                    }
                }), 403
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator
