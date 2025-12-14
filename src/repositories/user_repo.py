"""
User repository for database operations.
"""
import datetime
from sqlalchemy import desc
from src.app.extensions import db
from src.domain.models import User, ActivityLog


class UserRepository:
    """Repository for user database operations."""
    
    @staticmethod
    def get_all(page=1, per_page=20, is_active=None, role=None, search=None):
        """
        Get all users with optional filters and pagination.
        
        Args:
            page: Page number
            per_page: Items per page
            is_active: Filter by active status
            role: Filter by role
            search: Search by username or email
            
        Returns:
            Tuple of (users list, pagination dict)
        """
        query = User.query
        
        # Apply filters
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        if role:
            query = query.filter(User.role == role)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                db.or_(
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern)
                )
            )
        
        # Order by created_at descending
        query = query.order_by(desc(User.created_at))
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        users = query.offset((page - 1) * per_page).limit(per_page).all()
        
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page if per_page > 0 else 0
        }
        
        return users, pagination
    
    @staticmethod
    def get_by_id(user_id):
        """Get a user by ID."""
        return User.query.get(user_id)
    
    @staticmethod
    def get_by_username(username):
        """Get a user by username."""
        return User.query.filter_by(username=username).first()
    
    @staticmethod
    def create(data):
        """
        Create a new user.
        
        Args:
            data: Dictionary with user fields (username, password, email, role, is_active)
            
        Returns:
            Created user object
        """
        user = User(
            username=data['username'],
            email=data.get('email'),
            role=data.get('role', 'Staff'),
            is_active=data.get('is_active', True)
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        return user
    
    @staticmethod
    def update(user_id, data):
        """
        Update an existing user.
        
        Args:
            user_id: User ID
            data: Dictionary with fields to update
            
        Returns:
            Updated user object or None if not found
        """
        user = User.query.get(user_id)
        if not user:
            return None
        
        # Update only provided fields
        if data.get('username'):
            user.username = data['username']
        if data.get('email') is not None:
            user.email = data['email']
        if data.get('role'):
            user.role = data['role']
        if data.get('is_active') is not None:
            user.is_active = data['is_active']
        if data.get('password'):
            user.set_password(data['password'])
        
        db.session.commit()
        return user
    
    @staticmethod
    def delete(user_id, soft_delete=True):
        """
        Delete a user (soft delete by default).
        
        Args:
            user_id: User ID
            soft_delete: If True, set is_active=False. If False, actually delete.
            
        Returns:
            True if successful, False if not found
        """
        user = User.query.get(user_id)
        if not user:
            return False
        
        if soft_delete:
            user.is_active = False
            db.session.commit()
        else:
            db.session.delete(user)
            db.session.commit()
        
        return True
    
    @staticmethod
    def update_last_login(user_id):
        """Update user's last login timestamp."""
        user = User.query.get(user_id)
        if user:
            user.last_login = datetime.datetime.utcnow()
            db.session.commit()
    
    @staticmethod
    def update_refresh_token(user_id, refresh_token):
        """Update user's refresh token."""
        user = User.query.get(user_id)
        if user:
            user.refresh_token = refresh_token
            db.session.commit()
    
    @staticmethod
    def clear_refresh_token(user_id):
        """Clear user's refresh token (logout)."""
        user = User.query.get(user_id)
        if user:
            user.refresh_token = None
            db.session.commit()
    
    @staticmethod
    def check_username_exists(username, exclude_id=None):
        """
        Check if username already exists.
        
        Args:
            username: Username to check
            exclude_id: User ID to exclude from check (for updates)
            
        Returns:
            True if exists, False otherwise
        """
        query = User.query.filter_by(username=username)
        if exclude_id:
            query = query.filter(User.id != exclude_id)
        return query.first() is not None
    
    # --- Activity Log Operations ---
    
    @staticmethod
    def log_activity(user_id, action, resource_type=None, resource_id=None, 
                     details=None, ip_address=None, user_agent=None):
        """
        Log a user activity.
        
        Args:
            user_id: User ID
            action: Action type (login, logout, password_change, etc.)
            resource_type: Type of resource affected
            resource_id: ID of the affected resource
            details: Additional context as dict
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created ActivityLog object
        """
        log = ActivityLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(log)
        db.session.commit()
        return log
    
    @staticmethod
    def get_activity_log(user_id, page=1, per_page=20, action=None):
        """
        Get activity log for a user with pagination.
        
        Args:
            user_id: User ID
            page: Page number
            per_page: Items per page
            action: Optional filter by action type
            
        Returns:
            Tuple of (logs list, pagination dict)
        """
        query = ActivityLog.query.filter(ActivityLog.user_id == user_id)
        
        if action:
            query = query.filter(ActivityLog.action == action)
        
        # Order by created_at descending (newest first)
        query = query.order_by(desc(ActivityLog.created_at))
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        logs = query.offset((page - 1) * per_page).limit(per_page).all()
        
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page if per_page > 0 else 0
        }
        
        return logs, pagination


# Singleton instance
user_repo = UserRepository()
