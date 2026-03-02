from django.db import models

from shared.models import TimestampedModel


class LocationGroup(TimestampedModel):
    """
    Custom location groups (multi-national regions e.g. european union)
    """
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
