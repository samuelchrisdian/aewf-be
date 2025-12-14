"""
Authentication validation schemas using Marshmallow.
"""
from marshmallow import Schema, fields, validate, validates_schema, ValidationError


class LoginSchema(Schema):
    """Schema for user login request validation."""
    username = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    password = fields.Str(required=True, validate=validate.Length(min=1, max=100))


class ChangePasswordSchema(Schema):
    """Schema for password change request validation."""
    current_password = fields.Str(required=True, validate=validate.Length(min=1))
    new_password = fields.Str(required=True, validate=validate.Length(min=6, max=100))
    confirm_password = fields.Str(required=True)
    
    @validates_schema
    def validate_passwords_match(self, data, **kwargs):
        """Ensure new password and confirmation match."""
        if data.get('new_password') != data.get('confirm_password'):
            raise ValidationError('Passwords do not match', 'confirm_password')
        if data.get('current_password') == data.get('new_password'):
            raise ValidationError('New password must be different from current password', 'new_password')


class RefreshTokenSchema(Schema):
    """Schema for refresh token request validation."""
    refresh_token = fields.Str(required=True)


# Schema instances for use in routes
login_schema = LoginSchema()
change_password_schema = ChangePasswordSchema()
refresh_token_schema = RefreshTokenSchema()
