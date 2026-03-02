from django.db import models

from shared.models import TimestampedModel


class Group(TimestampedModel):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
