from django.db import models

from shared.models import TimestampedModel, UniqueUID

from allauth.utils import get_user_model


class UserProfile(TimestampedModel, UniqueUID):
    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
    )
    company = models.OneToOneField(
        'Company',
        on_delete=models.CASCADE,
        related_name='company_profile'
    )
    # Source field represents the Affiliate flow used when a user got registered
    source = models.ForeignKey(
        'Affiliate',
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True
    )

    @property
    def is_offline(self):
        return self.user.last_login == None

    @property
    def source_type(self):
        # Get user origin from flow or None if registered directly
        return self.source.flow_type if self.source else None

    def __str__(self):
        return self.user.email
