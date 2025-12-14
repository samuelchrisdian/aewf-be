"""
Configuration service for business logic.
"""
import datetime
from src.repositories.config_repo import config_repo


class ConfigService:
    """Service for system configuration business logic."""
    
    @staticmethod
    def get_settings():
        """
        Get all system settings formatted for API response.
        
        Returns:
            dict: All settings organized by category
        """
        return config_repo.get_all_settings()
    
    @staticmethod
    def update_settings(updates, user_id=None):
        """
        Update system settings.
        
        Args:
            updates: Dict with category keys and setting values
            user_id: ID of user making updates
            
        Returns:
            Tuple of (updated_settings, error_message)
        """
        result = {}
        
        # Update each category
        for category, values in updates.items():
            if isinstance(values, dict):
                result[category] = config_repo.update_settings(
                    category=category,
                    updates=values,
                    user_id=user_id
                )
        
        # Return all settings after update
        return config_repo.get_all_settings(), None
    
    @staticmethod
    def get_school_calendar(year=None, month=None):
        """
        Get school calendar with holidays.
        
        Args:
            year: Filter by year (default: current year)
            month: Filter by month (optional)
            
        Returns:
            dict: Calendar data with holidays and school days
        """
        if year is None:
            year = datetime.datetime.now().year
        
        # Get holidays for the year
        holidays = config_repo.get_holidays(year=year)
        
        # Format holidays
        holiday_list = []
        for h in holidays:
            holiday_list.append({
                'id': h.id,
                'date': h.date.isoformat() if h.date else None,
                'name': h.name,
                'type': h.type
            })
        
        # Get attendance settings for context
        settings = config_repo.get_all_settings()
        attendance_rules = settings.get('attendance_rules', {})
        
        return {
            'year': year,
            'month': month,
            'holidays': holiday_list,
            'total_holidays': len(holiday_list),
            'school_settings': {
                'start_time': attendance_rules.get('school_start_time', '07:00'),
                'end_time': attendance_rules.get('school_end_time', '15:00'),
                'late_threshold_minutes': attendance_rules.get('late_threshold_minutes', 15)
            }
        }
    
    @staticmethod
    def add_holiday(date, name, type='holiday', user_id=None):
        """
        Add a school holiday.
        
        Args:
            date: Holiday date
            name: Holiday name
            type: Holiday type
            user_id: ID of user creating holiday
            
        Returns:
            Tuple of (holiday_data, error_message)
        """
        holiday = config_repo.add_holiday(
            date=date,
            name=name,
            type=type,
            user_id=user_id
        )
        
        if not holiday:
            return None, "Holiday already exists for this date"
        
        return {
            'id': holiday.id,
            'date': holiday.date.isoformat() if holiday.date else None,
            'name': holiday.name,
            'type': holiday.type,
            'created_at': holiday.created_at.isoformat() if holiday.created_at else None
        }, None
    
    @staticmethod
    def remove_holiday(holiday_id):
        """
        Remove a school holiday.
        
        Args:
            holiday_id: Holiday ID
            
        Returns:
            Tuple of (success, error_message)
        """
        success = config_repo.delete_holiday(holiday_id)
        if not success:
            return False, "Holiday not found"
        return True, None


# Singleton instance
config_service = ConfigService()
