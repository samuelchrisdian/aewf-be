"""
Class validation schemas using Marshmallow.
"""
from marshmallow import Schema, fields, validate


class TeacherBasicSchema(Schema):
    """Basic teacher info for nested serialization."""
    teacher_id = fields.String(dump_only=True)
    name = fields.String(dump_only=True)
    phone = fields.String(dump_only=True, allow_none=True)


class AttendanceStatsSchema(Schema):
    """Schema for class attendance statistics."""
    average_rate = fields.Float(dump_only=True)
    at_risk_students = fields.Integer(dump_only=True)


class ClassSchema(Schema):
    """Schema for class list response serialization."""
    class_id = fields.String(dump_only=True)
    class_name = fields.String()
    wali_kelas_id = fields.String(allow_none=True)
    wali_kelas_name = fields.String(dump_only=True, allow_none=True)
    student_count = fields.Integer(dump_only=True)


class ClassDetailSchema(Schema):
    """Schema for detailed class response with full info."""
    class_id = fields.String(dump_only=True)
    class_name = fields.String()
    wali_kelas = fields.Nested(TeacherBasicSchema, dump_only=True, allow_none=True)
    student_count = fields.Integer(dump_only=True)
    attendance_stats = fields.Nested(AttendanceStatsSchema, dump_only=True)


class ClassCreateSchema(Schema):
    """Schema for creating a new class."""
    class_id = fields.String(
        required=True,
        validate=validate.Length(min=1, max=50)
    )
    class_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=100)
    )
    wali_kelas_id = fields.String(
        allow_none=True,
        validate=validate.Length(max=50)
    )


class ClassUpdateSchema(Schema):
    """Schema for updating a class."""
    class_name = fields.String(
        validate=validate.Length(min=1, max=100)
    )
    wali_kelas_id = fields.String(
        allow_none=True,
        validate=validate.Length(max=50)
    )


# Schema instances for reuse
class_schema = ClassSchema()
class_list_schema = ClassSchema(many=True)
class_detail_schema = ClassDetailSchema()
class_create_schema = ClassCreateSchema()
class_update_schema = ClassUpdateSchema()
