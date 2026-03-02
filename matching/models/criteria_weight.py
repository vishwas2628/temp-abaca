from django.db import models
from shared.models import TimestampedModel


class CriteriaWeight(TimestampedModel):
    name = models.CharField(max_length=100)
    value = models.IntegerField()

    def __str__(self):
        return self.name + ' (' + str(self.value) + ')'
