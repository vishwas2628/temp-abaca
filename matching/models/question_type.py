from django.db import models
from shared.models import TimestampedModel
from django.contrib.postgres.fields import JSONField
from enum import Enum


class QuestionType(TimestampedModel):
    NUMERIC = "numeric"
    SINGLE_SELECT = "single-select"
    MULTI_SELECT = "multi-select"
    RANGE = "range"
    FREE_RESPONSE = "free-response"
    DATE = "date"
    TYPE_CHOICES = (
        (NUMERIC, "Numeric"),
        (SINGLE_SELECT, "Single Select"),
        (MULTI_SELECT, "Multi Select"),
        (RANGE, "Range"),
        (FREE_RESPONSE, "Free Response"),
        (DATE, "Date"),
    )

    name = models.CharField(max_length=100)
    type = models.CharField(
        choices=TYPE_CHOICES,
        default=SINGLE_SELECT,
        max_length=50
    )
    meta = JSONField(default=dict, blank=True)
    description = models.TextField()

    def __str__(self):
        return self.name
