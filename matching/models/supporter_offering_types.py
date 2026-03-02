from shared.models import TimestampedModel
from django.db import models


class SupporterOfferingTypes(TimestampedModel):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        'SupporterOfferingCategories', on_delete=models.DO_NOTHING)

    class Meta:
        verbose_name_plural = 'Supporter offering types'

    def __str__(self):
        return self.name
