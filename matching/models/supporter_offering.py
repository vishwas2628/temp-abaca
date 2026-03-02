from django.db import models
from shared.models import SanitizedModel, TimestampedModel


class SupporterOffering(SanitizedModel, TimestampedModel):
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        'SupporterOfferingCategories', on_delete=models.DO_NOTHING)
    types = models.ManyToManyField(
        'SupporterOfferingTypes', blank=True)
    supporter = models.ForeignKey(
        'Supporter', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.supporter.name + ' - ' + self.category.name
