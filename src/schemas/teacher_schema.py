"""
Teacher validation schemas using Marshmallow.
"""
from marshmallow import Schema, fields, validate


class ClassBasicSchema(Schema):
    """Basic class info for nested serialization in teacher."""
    class_id = fields.String(dump_only=True)
    class_name = fields.String(dump_only=True)
    student_count = fields.Integer(dump_only=True)


class TeacherSchema(Schema):
    """Schema for teacher list response serialization."""
    teacher_id = fields.String(dump_only=True)
    name = fields.String()
    role = fields.String()
    phone = fields.String(allow_none=True)


class TeacherDetailSchema(Schema):
    """Schema for detailed teacher response with classes."""
    teacher_id = fields.String(dump_only=True)
    name = fields.String()
    role = fields.String()
    phone = fields.String(allow_none=True)
    classes = fields.List(fields.Nested(ClassBasicSchema), dump_only=True)


class TeacherCreateSchema(Schema):
    """Schema for creating a new teacher."""
    teacher_id = fields.String(
        required=True,
        validate=validate.Length(min=1, max=50)
    )
    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255)
    )
    role = fields.String(
        load_default="Teacher",
        validate=validate.OneOf(["Teacher", "Wali Kelas", "Guru Mapel", "Admin"])
    )
    phone = fields.String(
        allow_none=True,
        validate=validate.Length(max=20)
    )


class TeacherUpdateSchema(Schema):
    """Schema for updating a teacher."""
    name = fields.String(
        validate=validate.Length(min=1, max=255)
    )
    role = fields.String(
        validate=validate.OneOf(["Teacher", "Wali Kelas", "Guru Mapel", "Admin"])
    )
    phone = fields.String(
        allow_none=True,
        validate=validate.Length(max=20)
    )


# Schema instances for reuse
teacher_schema = TeacherSchema()
teacher_list_schema = TeacherSchema(many=True)
teacher_detail_schema = TeacherDetailSchema()
teacher_create_schema = TeacherCreateSchema()
teacher_update_schema = TeacherUpdateSchema()
