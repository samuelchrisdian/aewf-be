"""
Mapping validation schemas using Marshmallow.
"""
from marshmallow import Schema, fields, validate, validates, ValidationError


class StudentInfoSchema(Schema):
    """Schema for student information in mapping context."""
    nis = fields.String(dump_only=True)
    name = fields.String(dump_only=True)
    class_id = fields.String(dump_only=True)


class MachineUserInfoSchema(Schema):
    """Schema for machine user information in mapping context."""
    id = fields.Integer(dump_only=True)
    machine_user_id = fields.String(dump_only=True)
    machine_user_name = fields.String(dump_only=True)
    machine_code = fields.String(dump_only=True)


class SuggestedMatchSchema(Schema):
    """Schema for suggested student match."""
    student = fields.Nested(StudentInfoSchema, dump_only=True)
    confidence_score = fields.Integer(dump_only=True)


class MappingSchema(Schema):
    """Schema for mapping response serialization."""
    id = fields.Integer(dump_only=True)
    machine_user = fields.Nested(MachineUserInfoSchema, dump_only=True)
    student = fields.Nested(StudentInfoSchema, dump_only=True, allow_none=True)
    status = fields.String(dump_only=True)
    confidence_score = fields.Integer(dump_only=True)
    verified_at = fields.DateTime(dump_only=True, allow_none=True)
    verified_by = fields.String(dump_only=True, allow_none=True)


class UnmappedUserSchema(Schema):
    """Schema for unmapped user with suggested matches."""
    machine_user = fields.Nested(MachineUserInfoSchema, dump_only=True)
    suggested_matches = fields.Nested(SuggestedMatchSchema, many=True, dump_only=True)


class MappingStatsSchema(Schema):
    """Schema for mapping statistics response."""
    total_machine_users = fields.Integer(dump_only=True)
    mapped_count = fields.Integer(dump_only=True)
    verified_count = fields.Integer(dump_only=True)
    suggested_count = fields.Integer(dump_only=True)
    unmapped_count = fields.Integer(dump_only=True)
    mapping_rate = fields.Float(dump_only=True)


class BulkVerifyItemSchema(Schema):
    """Schema for single bulk verify item."""
    mapping_id = fields.Integer(
        required=True
    )
    status = fields.String(
        required=True,
        validate=validate.OneOf(['verified', 'rejected'])
    )
    reason = fields.String(
        allow_none=True,
        validate=validate.Length(max=500)
    )


class BulkVerifyRequestSchema(Schema):
    """Schema for bulk verify request."""
    mappings = fields.Nested(
        BulkVerifyItemSchema,
        many=True,
        required=True,
        validate=validate.Length(min=1, max=100)
    )


# Schema instances for reuse
mapping_schema = MappingSchema()
mapping_list_schema = MappingSchema(many=True)
unmapped_user_schema = UnmappedUserSchema()
unmapped_user_list_schema = UnmappedUserSchema(many=True)
mapping_stats_schema = MappingStatsSchema()
bulk_verify_request_schema = BulkVerifyRequestSchema()
