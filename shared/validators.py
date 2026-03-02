import jsonschema

from django.core.exceptions import ValidationError
from django.core.validators import BaseValidator
from django.utils.translation import ugettext as _

from rest_framework.serializers import ValidationError as SerializerValidationError


class AbacaPasswordValidator:
    """
    A custom serializer validator for passwords on Abaca.
    """
    SPECIAL_CHARS = "[~`!@#$%^&*()_-+={}\\|/.:;\"\'<,>?]"

    def __init__(self, min_letters=1, min_numbers=1, min_specialchars=1):
        self.min_letters = min_letters
        self.min_numbers = min_numbers
        self.min_specialchars = min_specialchars

    def __call__(self, password):
        if not any(char.isdigit() for char in password):
            raise SerializerValidationError(_('Password must contain at least %(min_numbers)d digit.') %
                                            {'min_numbers': self.min_numbers})
        if not any(char.isalpha() for char in password):
            raise SerializerValidationError(_('Password must contain at least %(min_letters)d letter.') %
                                            {'min_letters': self.min_letters})
        if not any(char in self.SPECIAL_CHARS for char in password):
            raise SerializerValidationError(
                _('Password must contain at least %(min_specialchars)d special character.') %
                {'min_specialchars': self.min_specialchars})


class JSONSchemaValidator(BaseValidator):
    """
    A JSONField schema model validator:

    Example:
    * json_field = JSONField(validators=[JSONSchemaValidator(limit_value=JSON_SCHEMA)])
    """

    def compare(self, input, schema):
        try:
            jsonschema.validate(input, schema)
        except jsonschema.exceptions.ValidationError:
            raise ValidationError('%(value)s failed JSON schema check', params={'value': input})


class JSONSchemaSerializerValidator:
    """
    A jsonschema serializer validator.
    This is particularly useful when there's bulk actions like
    bulk_create or bulk_update where the model save method
    isn't triggered as well as the model fields' validation
    which requires us to validate on the serializer field.

    Example:
    * json_field = serializers.JSONField(validators=[JSONSchemaSerializerValidator(schema=JSON_SCHEMA)])
    """

    def __init__(self, schema):
        self.schema = schema

    def __call__(self, value):
        try:
            jsonschema.validate(value, self.schema)
        except jsonschema.exceptions.ValidationError:
            raise SerializerValidationError('%s failed JSON schema check' % value)
