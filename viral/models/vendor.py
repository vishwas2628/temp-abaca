from django.db import models
from django.core import signing
from django_better_admin_arrayfield.models.fields import ArrayField

from shared.models import TimestampedModel


class Vendor(TimestampedModel):
    NO_AUTH = 0
    BASIC_AUTH = 1

    AUTH_TYPES = (
        (NO_AUTH, "No Auth"),
        (BASIC_AUTH, "Basic Auth"),
    )

    # Loose schemas proposed by stakeholders:
    LOOSE_SCHEMA = 'loose'
    LOOSE_LIST_SCHEMA = 'loose_list'

    # TODO: Migrate loose schemas into a normalized schema with consistent structure and name casing;
    CALLBACK_SCHEMAS = (
        (LOOSE_SCHEMA, 'Loose Schema'),
        (LOOSE_LIST_SCHEMA, 'Loose List Schema'),
    )

    name = models.CharField(max_length=200)
    callback_schema = models.CharField(max_length=128, choices=CALLBACK_SCHEMAS, default=LOOSE_LIST_SCHEMA)
    endpoint = models.URLField(blank=True, null=True, default=None,
                               help_text='Callback URL to send back data to a Vendor.')
    uuid = models.IntegerField(unique=True)
    cors_origins = ArrayField(models.CharField(max_length=255), blank=True, null=True,
                              help_text='Domains that are allowed to perform requests to Abaca\'s API.')

    auth_type = models.SmallIntegerField(
        choices=AUTH_TYPES, default=NO_AUTH)
    auth_user = models.CharField(max_length=60, blank=True, null=True)
    auth_password = models.CharField(max_length=128, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.auth_password = signing.dumps(self.auth_password)
        super(Vendor, self).save(*args, **kwargs)

    def __str__(self):
        return self.name
