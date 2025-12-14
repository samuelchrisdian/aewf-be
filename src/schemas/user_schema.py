"""
User management validation schemas using Marshmallow.
"""
from marshmallow import Schema, fields, validate, validates, ValidationError


class UserCreateSchema(Schema):
    """Schema for user creation request validation."""
    username = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=50)
    )
    password = fields.Str(
        required=True,
        validate=validate.Length(min=6, max=100)
    )
    email = fields.Email(required=False, allow_none=True)
    role = fields.Str(
        required=False,
        validate=validate.OneOf(['Admin', 'Teacher', 'Staff']),
        load_default='Staff'
    )
    is_active = fields.Bool(required=False, load_default=True)


class UserUpdateSchema(Schema):
    """Schema for user update request validation."""
    username = fields.Str(
        required=False,
        validate=validate.Length(min=3, max=50)
    )
    email = fields.Email(required=False, allow_none=True)
    role = fields.Str(
        required=False,
        validate=validate.OneOf(['Admin', 'Teacher', 'Staff'])
    )
    is_active = fields.Bool(required=False)
    password = fields.Str(
        required=False,
        validate=validate.Length(min=6, max=100),
        load_only=True
    )


class UserResponseSchema(Schema):
    """Schema for serializing user data in responses."""
    id = fields.Int(dump_only=True)
    username = fields.Str()
    email = fields.Email(allow_none=True)
    role = fields.Str()
    is_active = fields.Bool()
    last_login = fields.DateTime(allow_none=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime(allow_none=True)
    permissions = fields.List(fields.Str(), dump_only=True)


class ActivityLogSchema(Schema):
    """Schema for serializing activity log entries."""
    id = fields.Int(dump_only=True)
    user_id = fields.Int()
    action = fields.Str()
    resource_type = fields.Str(allow_none=True)
    resource_id = fields.Str(allow_none=True)
    details = fields.Dict(allow_none=True)
    ip_address = fields.Str(allow_none=True)
    created_at = fields.DateTime()


# Schema instances for use in routes
user_create_schema = UserCreateSchema()
user_update_schema = UserUpdateSchema()
user_response_schema = UserResponseSchema()
user_response_list_schema = UserResponseSchema(many=True)
activity_log_schema = ActivityLogSchema(many=True)
