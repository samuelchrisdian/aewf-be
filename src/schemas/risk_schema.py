"""
Risk validation schemas using Marshmallow.
"""
from marshmallow import Schema, fields, validate, validates, ValidationError
from datetime import date


# Valid alert types
VALID_ALERT_TYPES = ["high_risk", "medium_risk", "consecutive_absence"]

# Valid alert statuses
VALID_ALERT_STATUSES = ["pending", "acknowledged", "resolved"]

# Valid risk levels
VALID_RISK_LEVELS = ["high", "medium", "low"]

# Valid actions
VALID_ACTIONS = ["contacted_parent", "scheduled_meeting", "home_visit", "counseling", "other"]


class RiskAlertSchema(Schema):
    """Base schema for risk alert response serialization."""
    id = fields.Integer(dump_only=True)
    student_nis = fields.String()
    alert_type = fields.String()
    message = fields.String()
    status = fields.String()
    assigned_to = fields.String(allow_none=True)
    action_taken = fields.String(allow_none=True)
    action_notes = fields.String(allow_none=True)
    follow_up_date = fields.Date(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    resolved_at = fields.DateTime(dump_only=True, allow_none=True)


class RiskAlertDetailSchema(Schema):
    """Risk alert with student info for list responses."""
    id = fields.Integer(dump_only=True)
    student_nis = fields.String()
    student_name = fields.String(dump_only=True)
    class_id = fields.String(dump_only=True)
    class_name = fields.String(dump_only=True)
    alert_type = fields.String()
    message = fields.String()
    status = fields.String()
    assigned_to = fields.String(allow_none=True)
    assignee_name = fields.String(dump_only=True, allow_none=True)
    action_taken = fields.String(allow_none=True)
    action_notes = fields.String(allow_none=True)
    follow_up_date = fields.Date(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    resolved_at = fields.DateTime(dump_only=True, allow_none=True)


class RiskAlertActionSchema(Schema):
    """Schema for taking action on an alert."""
    action = fields.String(
        required=True,
        validate=validate.OneOf(VALID_ACTIONS)
    )
    notes = fields.String(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    follow_up_date = fields.Date(allow_none=True)
    status = fields.String(
        validate=validate.OneOf(["acknowledged", "resolved"]),
        load_default="acknowledged"
    )

    @validates('follow_up_date')
    def validate_follow_up_date(self, value, **kwargs):
        """Validate follow_up_date is not in the past."""
        if value and value < date.today():
            raise ValidationError('Follow-up date cannot be in the past')


class RiskHistorySchema(Schema):
    """Schema for risk history response."""
    id = fields.Integer(dump_only=True)
    student_nis = fields.String()
    risk_level = fields.String()
    risk_score = fields.Integer()
    factors = fields.Dict(allow_none=True)
    calculated_at = fields.DateTime(dump_only=True)


class RiskFactorsSchema(Schema):
    """Schema for risk factors."""
    attendance_rate = fields.Float()
    consecutive_absences = fields.Integer()
    late_frequency = fields.Integer()
    trend = fields.String()


class StudentRiskSchema(Schema):
    """Schema for student risk detail response."""
    student_nis = fields.String()
    student_name = fields.String()
    class_id = fields.String()
    class_name = fields.String()
    risk_level = fields.String()
    risk_score = fields.Integer()  # 0-100
    factors = fields.Nested(RiskFactorsSchema)
    last_updated = fields.DateTime()
    alert_generated = fields.Boolean()


class StudentRiskListSchema(Schema):
    """Schema for at-risk students list."""
    student_nis = fields.String()
    student_name = fields.String()
    class_id = fields.String()
    risk_level = fields.String()
    risk_score = fields.Integer()
    factors = fields.Nested(RiskFactorsSchema)
    last_updated = fields.DateTime()
    alert_generated = fields.Boolean()


class RiskRecalculateSchema(Schema):
    """Schema for recalculate request."""
    class_id = fields.String(allow_none=True)  # Optional: only recalculate for specific class
    student_nis = fields.String(allow_none=True)  # Optional: only recalculate for specific student


# Schema instances for reuse
risk_alert_schema = RiskAlertSchema()
risk_alert_detail_schema = RiskAlertDetailSchema()
risk_alert_list_schema = RiskAlertDetailSchema(many=True)
risk_alert_action_schema = RiskAlertActionSchema()
risk_history_schema = RiskHistorySchema()
risk_history_list_schema = RiskHistorySchema(many=True)
student_risk_schema = StudentRiskSchema()
student_risk_list_schema = StudentRiskListSchema(many=True)
risk_recalculate_schema = RiskRecalculateSchema()
