"""
Notification repository for database operations.
"""
import datetime
from sqlalchemy import desc
from src.app.extensions import db
from src.domain.models import Notification, NotificationSettings


class NotificationRepository:
    """Repository for notification database operations."""
    
    @staticmethod
    def get_notifications(recipient_type, recipient_id, is_read=None, page=1, per_page=20):
        """
        Get notifications for a recipient with optional filters.
        
        Args:
            recipient_type: 'teacher' or 'parent'
            recipient_id: Teacher ID or parent phone
            is_read: Optional filter for read status
            page: Page number
            per_page: Items per page
            
        Returns:
            Tuple of (notifications list, pagination dict)
        """
        query = Notification.query.filter(
            Notification.recipient_type == recipient_type,
            Notification.recipient_id == recipient_id
        )
        
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)
        
        # Order by created_at descending (newest first)
        query = query.order_by(desc(Notification.created_at))
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        notifications = query.offset((page - 1) * per_page).limit(per_page).all()
        
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page if per_page > 0 else 0
        }
        
        return notifications, pagination
    
    @staticmethod
    def get_unread_count(recipient_type, recipient_id):
        """Get count of unread notifications for a recipient."""
        return Notification.query.filter(
            Notification.recipient_type == recipient_type,
            Notification.recipient_id == recipient_id,
            Notification.is_read == False
        ).count()
    
    @staticmethod
    def get_by_id(notification_id):
        """Get a notification by ID."""
        return Notification.query.get(notification_id)
    
    @staticmethod
    def create(data):
        """
        Create a new notification.
        
        Args:
            data: Dictionary with notification fields
            
        Returns:
            Created notification object
        """
        notification = Notification(
            recipient_type=data['recipient_type'],
            recipient_id=data['recipient_id'],
            type=data.get('type', 'custom'),
            title=data['title'],
            message=data['message'],
            priority=data.get('priority', 'normal'),
            channel=data.get('channel', 'in_app'),
            action_url=data.get('action_url')
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @staticmethod
    def mark_as_read(notification_id):
        """
        Mark a notification as read.
        
        Args:
            notification_id: ID of the notification
            
        Returns:
            True if successful, False if not found
        """
        notification = Notification.query.get(notification_id)
        if notification:
            notification.is_read = True
            notification.read_at = datetime.datetime.utcnow()
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def delete(notification_id):
        """
        Delete a notification.
        
        Args:
            notification_id: ID of the notification
            
        Returns:
            True if deleted, False if not found
        """
        notification = Notification.query.get(notification_id)
        if notification:
            db.session.delete(notification)
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def get_settings(user_id):
        """
        Get notification settings for a teacher.
        Creates default settings if not exists.
        
        Args:
            user_id: Teacher ID
            
        Returns:
            NotificationSettings object
        """
        settings = NotificationSettings.query.filter_by(user_id=user_id).first()
        if not settings:
            # Create default settings
            settings = NotificationSettings(user_id=user_id)
            db.session.add(settings)
            db.session.commit()
        return settings
    
    @staticmethod
    def update_settings(user_id, data):
        """
        Update notification settings for a teacher.
        
        Args:
            user_id: Teacher ID
            data: Dictionary with settings to update
            
        Returns:
            Updated NotificationSettings object
        """
        settings = NotificationSettings.query.filter_by(user_id=user_id).first()
        if not settings:
            settings = NotificationSettings(user_id=user_id)
            db.session.add(settings)
        
        # Update only provided fields
        if data.get('enable_risk_alerts') is not None:
            settings.enable_risk_alerts = data['enable_risk_alerts']
        if data.get('enable_attendance') is not None:
            settings.enable_attendance = data['enable_attendance']
        if data.get('enable_email') is not None:
            settings.enable_email = data['enable_email']
        if data.get('enable_sms') is not None:
            settings.enable_sms = data['enable_sms']
        if data.get('daily_digest_time') is not None:
            settings.daily_digest_time = data['daily_digest_time']
        
        db.session.commit()
        return settings


# Singleton instance
notification_repo = NotificationRepository()
