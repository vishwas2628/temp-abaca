from django.db import models

from .timestamped_model import TimestampedModel
from .unique_uid import UniqueUID

from allauth.utils import get_user_model


class PendingRegistration(TimestampedModel, UniqueUID):
    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
    )

    affiliate = models.ForeignKey(
        'viral.Affiliate',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='pending_registration'
    )

    # Used for ensuring that the registration has the bare minimum before being finished.
    is_complete = models.BooleanField(default=False)

    def __str__(self):
        return self.user.email
