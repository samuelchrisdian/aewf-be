"""
Notification service for business logic.
"""
from src.repositories.notification_repo import notification_repo


class NotificationService:
    """Service for notification business logic."""
    
    @staticmethod
    def get_notifications(recipient_type, recipient_id, is_read=None, page=1, per_page=20):
        """
        Get notifications for a recipient with unread count.
        
        Args:
            recipient_type: 'teacher' or 'parent'
            recipient_id: Teacher ID or parent phone
            is_read: Optional filter for read status
            page: Page number
            per_page: Items per page
            
        Returns:
            Tuple of (data dict with notifications and unread_count, pagination dict)
        """
        notifications, pagination = notification_repo.get_notifications(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            is_read=is_read,
            page=page,
            per_page=per_page
        )
        
        unread_count = notification_repo.get_unread_count(recipient_type, recipient_id)
        
        # Format notifications for response
        notifications_list = []
        for n in notifications:
            notifications_list.append({
                'id': n.id,
                'type': n.type,
                'title': n.title,
                'message': n.message,
                'priority': n.priority,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat() if n.created_at else None,
                'action_url': n.action_url
            })
        
        data = {
            'unread_count': unread_count,
            'notifications': notifications_list
        }
        
        return data, pagination
    
    @staticmethod
    def send_notification(data):
        """
        Send a notification (create in database).
        
        Args:
            data: Dictionary with notification fields
            
        Returns:
            Created notification data
        """
        notification = notification_repo.create(data)
        
        return {
            'id': notification.id,
            'recipient_type': notification.recipient_type,
            'recipient_id': notification.recipient_id,
            'type': notification.type,
            'title': notification.title,
            'message': notification.message,
            'priority': notification.priority,
            'channel': notification.channel,
            'created_at': notification.created_at.isoformat() if notification.created_at else None
        }
    
    @staticmethod
    def mark_as_read(notification_id, recipient_type, recipient_id):
        """
        Mark a notification as read.
        
        Args:
            notification_id: ID of the notification
            recipient_type: Type of recipient (for ownership check)
            recipient_id: ID of recipient (for ownership check)
            
        Returns:
            Tuple of (success boolean, error message or None)
        """
        notification = notification_repo.get_by_id(notification_id)
        
        if not notification:
            return False, "Notification not found"
        
        # Check ownership
        if notification.recipient_type != recipient_type or notification.recipient_id != recipient_id:
            return False, "Notification not found"
        
        notification_repo.mark_as_read(notification_id)
        return True, None
    
    @staticmethod
    def delete_notification(notification_id, recipient_type, recipient_id):
        """
        Delete a notification.
        
        Args:
            notification_id: ID of the notification
            recipient_type: Type of recipient (for ownership check)
            recipient_id: ID of recipient (for ownership check)
            
        Returns:
            Tuple of (success boolean, error message or None)
        """
        notification = notification_repo.get_by_id(notification_id)
        
        if not notification:
            return False, "Notification not found"
        
        # Check ownership
        if notification.recipient_type != recipient_type or notification.recipient_id != recipient_id:
            return False, "Notification not found"
        
        notification_repo.delete(notification_id)
        return True, None
    
    @staticmethod
    def get_settings(user_id):
        """
        Get notification settings for a teacher.
        
        Args:
            user_id: Teacher ID
            
        Returns:
            Settings dictionary
        """
        settings = notification_repo.get_settings(user_id)
        
        return {
            'user_id': settings.user_id,
            'enable_risk_alerts': settings.enable_risk_alerts,
            'enable_attendance': settings.enable_attendance,
            'enable_email': settings.enable_email,
            'enable_sms': settings.enable_sms,
            'daily_digest_time': settings.daily_digest_time
        }
    
    @staticmethod
    def update_settings(user_id, data):
        """
        Update notification settings for a teacher.
        
        Args:
            user_id: Teacher ID
            data: Dictionary with settings to update
            
        Returns:
            Updated settings dictionary
        """
        settings = notification_repo.update_settings(user_id, data)
        
        return {
            'user_id': settings.user_id,
            'enable_risk_alerts': settings.enable_risk_alerts,
            'enable_attendance': settings.enable_attendance,
            'enable_email': settings.enable_email,
            'enable_sms': settings.enable_sms,
            'daily_digest_time': settings.daily_digest_time
        }


# Singleton instance
notification_service = NotificationService()
