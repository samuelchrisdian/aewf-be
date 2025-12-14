"""
User management service for CRUD operations.
"""
from src.repositories.user_repo import user_repo
from src.schemas.user_schema import user_response_schema, user_response_list_schema, activity_log_schema


class UserService:
    """Service for user management operations."""
    
    @staticmethod
    def list_users(page=1, per_page=20, is_active=None, role=None, search=None):
        """
        Get paginated list of users.
        
        Args:
            page: Page number
            per_page: Items per page
            is_active: Filter by active status
            role: Filter by role
            search: Search by username or email
            
        Returns:
            Tuple of (users list, pagination dict)
        """
        users, pagination = user_repo.get_all(
            page=page,
            per_page=per_page,
            is_active=is_active,
            role=role,
            search=search
        )
        
        # Serialize users with permissions
        data = []
        for user in users:
            user_data = UserService._serialize_user(user)
            data.append(user_data)
        
        return data, pagination
    
    @staticmethod
    def get_user(user_id):
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (user data, error message)
        """
        user = user_repo.get_by_id(user_id)
        
        if not user:
            return None, "User not found"
        
        return UserService._serialize_user(user), None
    
    @staticmethod
    def create_user(data, created_by_user_id=None, ip_address=None, user_agent=None):
        """
        Create a new user.
        
        Args:
            data: User data dict
            created_by_user_id: ID of user creating this record
            ip_address: Client IP for logging
            user_agent: Client user agent for logging
            
        Returns:
            Tuple of (user data, error message)
        """
        # Check if username already exists
        if user_repo.check_username_exists(data['username']):
            return None, "Username already exists"
        
        # Create user
        user = user_repo.create(data)
        
        # Log activity if created by another user
        if created_by_user_id:
            user_repo.log_activity(
                user_id=created_by_user_id,
                action='create_user',
                resource_type='user',
                resource_id=str(user.id),
                details={'username': user.username, 'role': user.role},
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        return UserService._serialize_user(user), None
    
    @staticmethod
    def update_user(user_id, data, updated_by_user_id=None, ip_address=None, user_agent=None):
        """
        Update an existing user.
        
        Args:
            user_id: User ID to update
            data: Update data dict
            updated_by_user_id: ID of user making the update
            ip_address: Client IP for logging
            user_agent: Client user agent for logging
            
        Returns:
            Tuple of (user data, error message)
        """
        # Check if user exists
        existing = user_repo.get_by_id(user_id)
        if not existing:
            return None, "User not found"
        
        # Check username uniqueness if changing
        if data.get('username') and data['username'] != existing.username:
            if user_repo.check_username_exists(data['username'], exclude_id=user_id):
                return None, "Username already exists"
        
        # Update user
        user = user_repo.update(user_id, data)
        
        # Log activity
        if updated_by_user_id:
            user_repo.log_activity(
                user_id=updated_by_user_id,
                action='update_user',
                resource_type='user',
                resource_id=str(user_id),
                details={'updated_fields': list(data.keys())},
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        return UserService._serialize_user(user), None
    
    @staticmethod
    def delete_user(user_id, deleted_by_user_id=None, ip_address=None, user_agent=None):
        """
        Delete a user (soft delete).
        
        Args:
            user_id: User ID to delete
            deleted_by_user_id: ID of user performing delete
            ip_address: Client IP for logging
            user_agent: Client user agent for logging
            
        Returns:
            Tuple of (success: bool, error message)
        """
        # Prevent self-deletion
        if user_id == deleted_by_user_id:
            return False, "Cannot delete your own account"
        
        user = user_repo.get_by_id(user_id)
        if not user:
            return False, "User not found"
        
        # Soft delete
        success = user_repo.delete(user_id, soft_delete=True)
        
        if success and deleted_by_user_id:
            user_repo.log_activity(
                user_id=deleted_by_user_id,
                action='delete_user',
                resource_type='user',
                resource_id=str(user_id),
                details={'username': user.username},
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        return success, None if success else "Failed to delete user"
    
    @staticmethod
    def get_activity_log(user_id, page=1, per_page=20, action=None):
        """
        Get activity log for a user.
        
        Args:
            user_id: User ID
            page: Page number
            per_page: Items per page
            action: Optional filter by action type
            
        Returns:
            Tuple of (activity logs, pagination dict)
        """
        # Check if user exists
        user = user_repo.get_by_id(user_id)
        if not user:
            return None, None, "User not found"
        
        logs, pagination = user_repo.get_activity_log(
            user_id=user_id,
            page=page,
            per_page=per_page,
            action=action
        )
        
        # Serialize logs
        data = []
        for log in logs:
            data.append({
                'id': log.id,
                'action': log.action,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'details': log.details,
                'ip_address': log.ip_address,
                'created_at': log.created_at.isoformat() if log.created_at else None
            })
        
        return data, pagination, None
    
    @staticmethod
    def _serialize_user(user):
        """Serialize user with permissions based on role."""
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
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None,
            'permissions': role_permissions.get(user.role, ['read'])
        }


# Singleton instance
user_service = UserService()
