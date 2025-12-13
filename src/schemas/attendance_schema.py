"""
Attendance validation schemas using Marshmallow.
"""
from marshmallow import Schema, fields, validate, validates, ValidationError
from datetime import date


# Valid attendance status values
VALID_STATUSES = ["Present", "Absent", "Late", "Sick", "Permission"]


class AttendanceSchema(Schema):
    """Base schema for attendance response serialization."""
    id = fields.Integer(dump_only=True)
    student_nis = fields.String()
    attendance_date = fields.Date()
    check_in = fields.DateTime(allow_none=True)
    check_out = fields.DateTime(allow_none=True)
    status = fields.String()
    notes = fields.String(allow_none=True)
    recorded_by = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True, allow_none=True)


class AttendanceDetailSchema(Schema):
    """Attendance with student info for list responses."""
    id = fields.Integer(dump_only=True)
    student_nis = fields.String()
    student_name = fields.String(dump_only=True)
    class_id = fields.String(dump_only=True)
    class_name = fields.String(dump_only=True)
    attendance_date = fields.Date()
    check_in = fields.DateTime(allow_none=True)
    check_out = fields.DateTime(allow_none=True)
    status = fields.String()
    notes = fields.String(allow_none=True)
    recorded_by = fields.String(allow_none=True)
    recorder_name = fields.String(dump_only=True, allow_none=True)


class AttendanceCreateSchema(Schema):
    """Schema for creating manual attendance entry."""
    student_nis = fields.String(
        required=True,
        validate=validate.Length(min=1, max=20)
    )
    attendance_date = fields.Date(required=True)
    status = fields.String(
        required=True,
        validate=validate.OneOf(VALID_STATUSES)
    )
    check_in = fields.DateTime(allow_none=True, load_default=None)
    check_out = fields.DateTime(allow_none=True, load_default=None)
    notes = fields.String(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    recorded_by = fields.String(
        allow_none=True,
        validate=validate.Length(max=50)
    )

    @validates('attendance_date')
    def validate_attendance_date(self, value, **kwargs):
        """Validate attendance date is not in the future."""
        if value > date.today():
            raise ValidationError('Attendance date cannot be in the future')


class AttendanceUpdateSchema(Schema):
    """Schema for updating attendance record."""
    status = fields.String(
        validate=validate.OneOf(VALID_STATUSES)
    )
    check_in = fields.DateTime(allow_none=True)
    check_out = fields.DateTime(allow_none=True)
    notes = fields.String(
        allow_none=True,
        validate=validate.Length(max=500)
    )


class StudentAttendanceRecordSchema(Schema):
    """Schema for individual attendance record in student history."""
    id = fields.Integer(dump_only=True)
    attendance_date = fields.Date()
    check_in = fields.DateTime(allow_none=True)
    check_out = fields.DateTime(allow_none=True)
    status = fields.String()
    notes = fields.String(allow_none=True)


class ConsecutiveAbsenceSchema(Schema):
    """Schema for consecutive absence pattern."""
    start_date = fields.Date()
    end_date = fields.Date()
    count = fields.Integer()


class AttendancePatternsSchema(Schema):
    """Schema for attendance patterns."""
    consecutive_absences = fields.List(
        fields.Nested(ConsecutiveAbsenceSchema),
        dump_only=True
    )


class StudentAttendanceSummarySchema(Schema):
    """Schema for student attendance summary in history."""
    total_days = fields.Integer()
    present = fields.Integer()
    late = fields.Integer()
    absent = fields.Integer()
    sick = fields.Integer()
    permission = fields.Integer()
    attendance_rate = fields.Float()


class DailyBreakdownSchema(Schema):
    """Schema for daily attendance breakdown."""
    date = fields.Date()
    present = fields.Integer()
    late = fields.Integer()
    absent = fields.Integer()
    sick = fields.Integer()
    permission = fields.Integer()


class AttendanceSummaryStatsSchema(Schema):
    """Schema for attendance summary statistics."""
    total_school_days = fields.Integer()
    average_attendance_rate = fields.Float()
    present_count = fields.Integer()
    late_count = fields.Integer()
    absent_count = fields.Integer()
    sick_count = fields.Integer()
    permission_count = fields.Integer()


class AttendanceSummaryResponseSchema(Schema):
    """Schema for GET /attendance/summary response."""
    period = fields.String(allow_none=True)
    class_id = fields.String(allow_none=True)
    stats = fields.Nested(AttendanceSummaryStatsSchema)
    daily_breakdown = fields.List(fields.Nested(DailyBreakdownSchema))


# Schema instances for reuse
attendance_schema = AttendanceSchema()
attendance_detail_schema = AttendanceDetailSchema()
attendance_list_schema = AttendanceDetailSchema(many=True)
attendance_create_schema = AttendanceCreateSchema()
attendance_update_schema = AttendanceUpdateSchema()
