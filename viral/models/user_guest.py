from django.db import models

from shared.models import TimestampedModel, UniqueUID


class UserGuest(TimestampedModel, UniqueUID):
    name = models.CharField(max_length=128)
    email = models.EmailField(unique=True)

    def __str__(self) -> str:
        return self.name
