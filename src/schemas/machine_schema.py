"""
Machine validation schemas using Marshmallow.
"""
from marshmallow import Schema, fields, validate, validates, ValidationError


class MachineUserSchema(Schema):
    """Schema for machine user response serialization."""
    id = fields.Integer(dump_only=True)
    machine_user_id = fields.String(dump_only=True)
    machine_user_name = fields.String(dump_only=True)
    department = fields.String(dump_only=True, allow_none=True)
    is_mapped = fields.Boolean(dump_only=True)


class MachineSchema(Schema):
    """Schema for machine response serialization."""
    id = fields.Integer(dump_only=True)
    machine_code = fields.String()
    location = fields.String(allow_none=True)
    status = fields.String(dump_only=True)
    user_count = fields.Integer(dump_only=True)
    last_sync = fields.DateTime(dump_only=True, allow_none=True)


class MachineDetailSchema(Schema):
    """Schema for detailed machine response with users."""
    id = fields.Integer(dump_only=True)
    machine_code = fields.String()
    location = fields.String(allow_none=True)
    status = fields.String(dump_only=True)
    user_count = fields.Integer(dump_only=True)
    last_sync = fields.DateTime(dump_only=True, allow_none=True)
    users = fields.Nested(MachineUserSchema, many=True, dump_only=True)


class MachineCreateSchema(Schema):
    """Schema for creating a new machine."""
    machine_code = fields.String(
        required=True,
        validate=validate.Length(min=1, max=50)
    )
    location = fields.String(
        allow_none=True,
        validate=validate.Length(max=255)
    )
    status = fields.String(
        load_default='active',
        validate=validate.OneOf(['active', 'inactive'])
    )

    @validates('machine_code')
    def validate_machine_code(self, value, **kwargs):
        """Validate machine_code format - alphanumeric with dashes."""
        clean = value.replace('-', '').replace('_', '')
        if not clean.isalnum():
            raise ValidationError('Machine code must be alphanumeric (dashes/underscores allowed)')


class MachineUpdateSchema(Schema):
    """Schema for updating a machine."""
    location = fields.String(
        allow_none=True,
        validate=validate.Length(max=255)
    )
    status = fields.String(
        validate=validate.OneOf(['active', 'inactive'])
    )


# Schema instances for reuse
machine_schema = MachineSchema()
machine_list_schema = MachineSchema(many=True)
machine_detail_schema = MachineDetailSchema()
machine_user_schema = MachineUserSchema()
machine_user_list_schema = MachineUserSchema(many=True)
machine_create_schema = MachineCreateSchema()
machine_update_schema = MachineUpdateSchema()
