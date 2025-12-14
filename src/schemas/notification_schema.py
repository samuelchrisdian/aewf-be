"""
Notification schemas for request validation and response serialization.
"""
from marshmallow import Schema, fields, validate, validates, ValidationError


class SendNotificationSchema(Schema):
    """Schema for sending a notification."""
    recipient_type = fields.String(
        required=True,
        validate=validate.OneOf(['teacher', 'parent']),
        metadata={'description': 'Type of recipient'}
    )
    recipient_id = fields.String(
        required=True,
        metadata={'description': 'Teacher ID or parent phone'}
    )
    type = fields.String(
        load_default='custom',
        validate=validate.OneOf(['risk_alert', 'attendance', 'custom']),
        metadata={'description': 'Type of notification'}
    )
    title = fields.String(
        required=True,
        validate=validate.Length(min=1, max=200),
        metadata={'description': 'Notification title'}
    )
    message = fields.String(
        required=True,
        validate=validate.Length(min=1, max=1000),
        metadata={'description': 'Notification body'}
    )
    priority = fields.String(
        load_default='normal',
        validate=validate.OneOf(['high', 'normal', 'low']),
        metadata={'description': 'Notification priority'}
    )
    channel = fields.String(
        load_default='in_app',
        validate=validate.OneOf(['in_app', 'email', 'sms']),
        metadata={'description': 'Delivery channel'}
    )
    action_url = fields.String(
        load_default=None,
        validate=validate.Length(max=500),
        metadata={'description': 'Optional action URL'}
    )


class NotificationSettingsUpdateSchema(Schema):
    """Schema for updating notification settings."""
    enable_risk_alerts = fields.Boolean(
        load_default=None,
        metadata={'description': 'Enable risk alert notifications'}
    )
    enable_attendance = fields.Boolean(
        load_default=None,
        metadata={'description': 'Enable attendance notifications'}
    )
    enable_email = fields.Boolean(
        load_default=None,
        metadata={'description': 'Enable email notifications'}
    )
    enable_sms = fields.Boolean(
        load_default=None,
        metadata={'description': 'Enable SMS notifications'}
    )
    daily_digest_time = fields.String(
        load_default=None,
        validate=validate.Regexp(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', error='Must be in HH:MM format'),
        metadata={'description': 'Time for daily digest (HH:MM)'}
    )


# Schema instances for use in routes
send_notification_schema = SendNotificationSchema()
notification_settings_update_schema = NotificationSettingsUpdateSchema()
