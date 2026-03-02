from django.db import models

from shared.models import TimestampedModel


class Sector(TimestampedModel):
    name = models.CharField(max_length=50)
    uuid = models.UUIDField(unique=True)
    groups = models.ManyToManyField('Group', related_name='sectors')

    def __str__(self):
        return self.name
