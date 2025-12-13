"""
Student validation schemas using Marshmallow.
"""
from marshmallow import Schema, fields, validate, validates, ValidationError


class AttendanceSummarySchema(Schema):
    """Schema for student attendance summary."""
    total_days = fields.Integer(dump_only=True)
    present = fields.Integer(dump_only=True)
    late = fields.Integer(dump_only=True)
    absent = fields.Integer(dump_only=True)
    sick = fields.Integer(dump_only=True)
    permission = fields.Integer(dump_only=True)
    attendance_rate = fields.Float(dump_only=True)


class StudentSchema(Schema):
    """Schema for student response serialization."""
    nis = fields.String(dump_only=True)
    name = fields.String()
    class_id = fields.String()
    class_name = fields.String(dump_only=True)
    parent_phone = fields.String(allow_none=True)
    is_active = fields.Boolean()
    attendance_summary = fields.Nested(AttendanceSummarySchema, dump_only=True)


class StudentListSchema(Schema):
    """Schema for student list item (lighter version)."""
    nis = fields.String(dump_only=True)
    name = fields.String()
    class_id = fields.String()
    class_name = fields.String(dump_only=True)
    parent_phone = fields.String(allow_none=True)
    is_active = fields.Boolean()


class StudentCreateSchema(Schema):
    """Schema for creating a new student."""
    nis = fields.String(
        required=True,
        validate=validate.Length(min=1, max=20)
    )
    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255)
    )
    class_id = fields.String(
        required=True,
        validate=validate.Length(min=1, max=50)
    )
    parent_phone = fields.String(
        allow_none=True,
        validate=validate.Length(max=20)
    )
    is_active = fields.Boolean(load_default=True)

    @validates('nis')
    def validate_nis(self, value, **kwargs):
        """Validate NIS format - alphanumeric only."""
        if not value.replace('-', '').replace('_', '').isalnum():
            raise ValidationError('NIS must be alphanumeric')


class StudentUpdateSchema(Schema):
    """Schema for updating a student."""
    name = fields.String(
        validate=validate.Length(min=1, max=255)
    )
    class_id = fields.String(
        validate=validate.Length(min=1, max=50)
    )
    parent_phone = fields.String(
        allow_none=True,
        validate=validate.Length(max=20)
    )
    is_active = fields.Boolean()


# Schema instances for reuse
student_schema = StudentSchema()
student_list_schema = StudentListSchema(many=True)
student_create_schema = StudentCreateSchema()
student_update_schema = StudentUpdateSchema()
