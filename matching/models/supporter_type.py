from django.db import models
from shared.models import TimestampedModel


class SupporterType(TimestampedModel):
    name = models.CharField(max_length=100)
    description = models.TextField()
    public = models.BooleanField(default=False)
    label = models.TextField(blank=True)

    def __str__(self):
        return self.name
