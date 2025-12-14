"""
Configuration validation schemas using Marshmallow.
"""
from marshmallow import Schema, fields, validate, validates, ValidationError
from datetime import datetime


class AttendanceRulesSchema(Schema):
    """Schema for attendance rules settings."""
    late_threshold_minutes = fields.Int(validate=validate.Range(min=1, max=120))
    grace_period_minutes = fields.Int(validate=validate.Range(min=0, max=60))
    auto_absent_after_hours = fields.Int(validate=validate.Range(min=1, max=12))
    school_start_time = fields.Str(validate=validate.Regexp(r'^\d{2}:\d{2}$'))
    school_end_time = fields.Str(validate=validate.Regexp(r'^\d{2}:\d{2}$'))


class RiskThresholdsSchema(Schema):
    """Schema for risk threshold settings."""
    high_risk_score = fields.Int(validate=validate.Range(min=1, max=100))
    medium_risk_score = fields.Int(validate=validate.Range(min=1, max=100))
    consecutive_absence_alert = fields.Int(validate=validate.Range(min=1, max=30))


class NotificationSettingsSchema(Schema):
    """Schema for notification settings."""
    enable_sms = fields.Bool()
    enable_email = fields.Bool()
    daily_digest_time = fields.Str(validate=validate.Regexp(r'^\d{2}:\d{2}$'))


class SettingsUpdateSchema(Schema):
    """Schema for updating system settings."""
    attendance_rules = fields.Nested(AttendanceRulesSchema, required=False)
    risk_thresholds = fields.Nested(RiskThresholdsSchema, required=False)
    notification_settings = fields.Nested(NotificationSettingsSchema, required=False)


class HolidayCreateSchema(Schema):
    """Schema for creating a school holiday."""
    date = fields.Date(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    type = fields.Str(
        required=False,
        validate=validate.OneOf(['holiday', 'break', 'event']),
        load_default='holiday'
    )


class HolidayResponseSchema(Schema):
    """Schema for serializing holiday data."""
    id = fields.Int(dump_only=True)
    date = fields.Date()
    name = fields.Str()
    type = fields.Str()
    created_at = fields.DateTime()


# Schema instances for use in routes
settings_update_schema = SettingsUpdateSchema()
holiday_create_schema = HolidayCreateSchema()
holiday_response_schema = HolidayResponseSchema()
holiday_response_list_schema = HolidayResponseSchema(many=True)
