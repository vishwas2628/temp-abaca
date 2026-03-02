from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from shared.models import TimestampedModel


def validate_source(value):
    valid_reference = isinstance(
        value, str) and '.' in value and len(value.split('.'))

    if not valid_reference:
        raise ValidationError(
            _('%(value)s is not a valid source'),
            params={'value': value},
        )
    else:
        source = value.split('.')
        app_label, model_name, field_name = source

        try:
            # Check if App and Model exist
            model_instance = apps.get_model(
                app_label=app_label, model_name=model_name)
            # Check if Field exists
            model_instance._meta.get_field(field_name)
        except:
            raise ValidationError(
                _('%(value)s either app, model or field do not exist'),
                params={'value': value},
            )


class ProfileIDField(TimestampedModel):
    """
    A profile field that identifies a user (e.g. name)
    """
    SELECTABLE_APP_MODELS = [
        {
            'source': 'viral.Company',
            'user_profile_relation': 'company_profile'
        }
    ]

    name = models.CharField(max_length=100)

    # Loose reference to another model field name following this structure: app.Model.field
    source = models.CharField(max_length=200, validators=[validate_source])

    # Specifies how the Model in the source relates to a UserProfile
    user_profile_relation = models.CharField(
        max_length=100, blank=True, editable=False)

    @property
    def app_label(self):
        return self.source.split('.')[0] or None

    @property
    def model_name(self):
        return self.source.split('.')[1] or None

    @property
    def field_name(self):
        return self.source.split('.')[2] or None

    def save(self, *args, **kwargs):
        # Before saving, set the user_profile_relation associated to a source
        for app_model in self.SELECTABLE_APP_MODELS:
            if app_model['source'] in self.source:
                self.user_profile_relation = app_model['user_profile_relation']
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
