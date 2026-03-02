from shared.models import TimestampedModel
from django.db import models


class SupporterOfferingCategories(TimestampedModel):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = 'Supporter offering categories'

    def __str__(self):
        return self.name
