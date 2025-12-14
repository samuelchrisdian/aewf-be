"""
Authentication service for login, logout, token management, and password operations.
"""
import jwt
import datetime
import secrets
from flask import current_app

from src.repositories.user_repo import user_repo


class AuthService:
    """Service for authentication operations."""
    
    @staticmethod
    def login(username, password, ip_address=None, user_agent=None):
        """
        Authenticate user and generate tokens.
        
        Args:
            username: User's username
            password: User's password
            ip_address: Client IP for logging
            user_agent: Client user agent for logging
            
        Returns:
            Tuple of (success: bool, result: dict or error message)
        """
        # Get user by username
        user = user_repo.get_by_username(username)
        
        if not user:
            return False, "Invalid username or password"
        
        if not user.is_active:
            return False, "Account is disabled"
        
        # Check password
        if not user.check_password(password):
            return False, "Invalid username or password"
        
        # Generate tokens
        access_token = AuthService._generate_access_token(user)
        refresh_token = AuthService._generate_refresh_token(user)
        
        # Update last login and store refresh token
        user_repo.update_last_login(user.id)
        user_repo.update_refresh_token(user.id, refresh_token)
        
        # Log activity
        user_repo.log_activity(
            user_id=user.id,
            action='login',
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return True, {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': 3600,  # 1 hour
            'user': AuthService._serialize_user(user)
        }
    
    @staticmethod
    def logout(user_id, ip_address=None, user_agent=None):
        """
        Logout user by invalidating refresh token.
        
        Args:
            user_id: User ID
            ip_address: Client IP for logging
            user_agent: Client user agent for logging
            
        Returns:
            True on success
        """
        user_repo.clear_refresh_token(user_id)
        
        # Log activity
        user_repo.log_activity(
            user_id=user_id,
            action='logout',
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return True
    
    @staticmethod
    def refresh_access_token(refresh_token):
        """
        Generate new access token using refresh token.
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            Tuple of (success: bool, result: dict or error message)
        """
        try:
            # Decode refresh token
            payload = jwt.decode(
                refresh_token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
            
            user_id = payload.get('user_id')
            token_type = payload.get('type')
            
            if token_type != 'refresh':
                return False, "Invalid token type"
            
            # Get user and verify refresh token matches
            user = user_repo.get_by_id(user_id)
            
            if not user:
                return False, "User not found"
            
            if not user.is_active:
                return False, "Account is disabled"
            
            if user.refresh_token != refresh_token:
                return False, "Invalid refresh token"
            
            # Generate new access token
            access_token = AuthService._generate_access_token(user)
            
            return True, {
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': 3600
            }
            
        except jwt.ExpiredSignatureError:
            return False, "Refresh token has expired"
        except jwt.InvalidTokenError:
            return False, "Invalid refresh token"
    
    @staticmethod
    def change_password(user_id, current_password, new_password, ip_address=None, user_agent=None):
        """
        Change user's password.
        
        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password
            ip_address: Client IP for logging
            user_agent: Client user agent for logging
            
        Returns:
            Tuple of (success: bool, error message or None)
        """
        user = user_repo.get_by_id(user_id)
        
        if not user:
            return False, "User not found"
        
        # Verify current password
        if not user.check_password(current_password):
            return False, "Current password is incorrect"
        
        # Update password
        user_repo.update(user_id, {'password': new_password})
        
        # Invalidate refresh token (force re-login)
        user_repo.clear_refresh_token(user_id)
        
        # Log activity
        user_repo.log_activity(
            user_id=user_id,
            action='password_change',
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return True, None
    
    @staticmethod
    def get_current_user(user_id):
        """
        Get current user details.
        
        Args:
            user_id: User ID
            
        Returns:
            User data dict or None
        """
        user = user_repo.get_by_id(user_id)
        
        if not user:
            return None
        
        return AuthService._serialize_user(user)
    
    @staticmethod
    def _generate_access_token(user):
        """Generate a JWT access token."""
        payload = {
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            'type': 'access',
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            'iat': datetime.datetime.utcnow()
        }
        return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')
    
    @staticmethod
    def _generate_refresh_token(user):
        """Generate a JWT refresh token."""
        payload = {
            'user_id': user.id,
            'type': 'refresh',
            'jti': secrets.token_hex(16),  # Unique token ID
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
            'iat': datetime.datetime.utcnow()
        }
        return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')
    
    @staticmethod
    def _serialize_user(user):
        """Serialize user for response."""
        # Define permissions based on role
        role_permissions = {
            'Admin': ['read', 'write', 'delete', 'manage_users'],
            'Teacher': ['read', 'write'],
            'Staff': ['read']
        }
        
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'is_active': user.is_active,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'permissions': role_permissions.get(user.role, ['read'])
        }


# Singleton instance
auth_service = AuthService()
