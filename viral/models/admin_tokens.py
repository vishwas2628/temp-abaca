from django.db import models

from shared.models import TimestampedModel


class AdminTokens(TimestampedModel):
    key = models.CharField(max_length=40)
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
    )
    available = models.BooleanField(default=True)
