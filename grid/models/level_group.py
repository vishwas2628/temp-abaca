from django.db import models
from shared.models import TimestampedModel


class LevelGroup(TimestampedModel):
    slug = models.CharField(max_length=60)

    def __str__(self):
        return self.slug

    class Meta:
        verbose_name_plural = 'Level Groups'
