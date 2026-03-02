from django.db import models
from shared.models import TimestampedModel


class LevelFilter(TimestampedModel):
    sector = models.IntegerField()
    location = models.IntegerField()
    category_level = models.ForeignKey(
        'CategoryLevel',
        on_delete=models.CASCADE
    )
