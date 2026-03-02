import json

from django.db import models
from django.db.models import CharField, TextField
from django.contrib.postgres.fields import JSONField


class SanitizedModel(models.Model):
    """
    An abstract model that ensures that all
    string fields get a custom sanitization.
    """

    def sanitize_fields(self):
        for field in self._meta.fields:
            field_value = getattr(self, field.name)

            if type(field) in [CharField, TextField] and isinstance(field_value, str):
                # Escape unsuported unicode sequence (null) in PostgresSQL:
                sanitized_value = field_value.replace('\x00', '')
                # Finally update field value with sanitized value:
                setattr(self, field.name, sanitized_value)
            elif type(field) == JSONField:
                field_value = getattr(self, field.name)
                # Escape unsuported unicode sequence (null) in PostgresSQL:
                sanitized_value = json.loads(json.dumps(field_value).replace('\\u0000', ''))
                # Finally update field value with sanitized value:
                setattr(self, field.name, sanitized_value)

    def save(self, *args, **kwargs):
        self.sanitize_fields()
        return super().save(*args, **kwargs)

    class Meta:
        abstract = True
