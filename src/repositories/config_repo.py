"""
Configuration repository for database operations.
"""
import datetime
from sqlalchemy import desc
from src.app.extensions import db
from src.domain.models import SystemConfig, SchoolHoliday


# Default system settings
DEFAULT_SETTINGS = {
    'attendance_rules': {
        'late_threshold_minutes': 15,
        'grace_period_minutes': 5,
        'auto_absent_after_hours': 4,
        'school_start_time': '07:00',
        'school_end_time': '15:00'
    },
    'risk_thresholds': {
        'high_risk_score': 70,
        'medium_risk_score': 40,
        'consecutive_absence_alert': 3
    },
    'notification_settings': {
        'enable_sms': False,
        'enable_email': True,
        'daily_digest_time': '07:00'
    }
}


class ConfigRepository:
    """Repository for system configuration database operations."""
    
    @staticmethod
    def get_all_settings():
        """
        Get all system settings grouped by category.
        Returns default values for missing settings.
        
        Returns:
            dict: Settings organized by category
        """
        settings = {}
        
        # Get stored settings from DB
        stored = SystemConfig.query.all()
        
        for config in stored:
            if config.category not in settings:
                settings[config.category] = {}
            settings[config.category][config.key] = config.value
        
        # Merge with defaults for any missing settings
        for category, defaults in DEFAULT_SETTINGS.items():
            if category not in settings:
                settings[category] = defaults.copy()
            else:
                for key, value in defaults.items():
                    if key not in settings[category]:
                        settings[category][key] = value
        
        return settings
    
    @staticmethod
    def get_setting(category, key):
        """
        Get a specific setting value.
        
        Args:
            category: Setting category
            key: Setting key
            
        Returns:
            Setting value or default
        """
        config = SystemConfig.query.filter_by(key=key, category=category).first()
        if config:
            return config.value
        
        # Return default if available
        if category in DEFAULT_SETTINGS:
            return DEFAULT_SETTINGS[category].get(key)
        
        return None
    
    @staticmethod
    def update_settings(category, updates, user_id=None):
        """
        Update settings for a category.
        
        Args:
            category: Setting category (attendance_rules, risk_thresholds, etc.)
            updates: Dict of key-value pairs to update
            user_id: ID of user making the update
            
        Returns:
            dict: Updated settings for the category
        """
        for key, value in updates.items():
            config = SystemConfig.query.filter_by(key=key, category=category).first()
            
            if config:
                config.value = value
                config.updated_by = user_id
            else:
                config = SystemConfig(
                    key=key,
                    value=value,
                    category=category,
                    updated_by=user_id
                )
                db.session.add(config)
        
        db.session.commit()
        
        # Return updated settings for this category
        return ConfigRepository.get_all_settings().get(category, {})
    
    @staticmethod
    def seed_defaults():
        """
        Seed default settings if not already present.
        Called during app initialization.
        """
        for category, defaults in DEFAULT_SETTINGS.items():
            for key, value in defaults.items():
                existing = SystemConfig.query.filter_by(key=key, category=category).first()
                if not existing:
                    config = SystemConfig(
                        key=key,
                        value=value,
                        category=category,
                        description=f"Default {category} setting"
                    )
                    db.session.add(config)
        
        db.session.commit()
    
    # --- Holiday Operations ---
    
    @staticmethod
    def get_holidays(start_date=None, end_date=None, year=None):
        """
        Get school holidays with optional date filtering.
        
        Args:
            start_date: Filter holidays from this date
            end_date: Filter holidays until this date
            year: Filter holidays for a specific year
            
        Returns:
            List of SchoolHoliday objects
        """
        query = SchoolHoliday.query
        
        if year:
            query = query.filter(
                db.extract('year', SchoolHoliday.date) == year
            )
        
        if start_date:
            query = query.filter(SchoolHoliday.date >= start_date)
        
        if end_date:
            query = query.filter(SchoolHoliday.date <= end_date)
        
        return query.order_by(SchoolHoliday.date).all()
    
    @staticmethod
    def get_holiday_by_id(holiday_id):
        """Get a holiday by ID."""
        return SchoolHoliday.query.get(holiday_id)
    
    @staticmethod
    def get_holiday_by_date(date):
        """Get a holiday by date."""
        return SchoolHoliday.query.filter_by(date=date).first()
    
    @staticmethod
    def add_holiday(date, name, type='holiday', user_id=None):
        """
        Add a new school holiday.
        
        Args:
            date: Holiday date
            name: Holiday name
            type: Holiday type (holiday, break, event)
            user_id: ID of user creating the holiday
            
        Returns:
            Created SchoolHoliday object or None if already exists
        """
        # Check if holiday already exists for this date
        existing = SchoolHoliday.query.filter_by(date=date).first()
        if existing:
            return None
        
        holiday = SchoolHoliday(
            date=date,
            name=name,
            type=type,
            created_by=user_id
        )
        db.session.add(holiday)
        db.session.commit()
        return holiday
    
    @staticmethod
    def delete_holiday(holiday_id):
        """
        Delete a school holiday.
        
        Args:
            holiday_id: Holiday ID
            
        Returns:
            True if deleted, False if not found
        """
        holiday = SchoolHoliday.query.get(holiday_id)
        if holiday:
            db.session.delete(holiday)
            db.session.commit()
            return True
        return False


# Singleton instance
config_repo = ConfigRepository()
