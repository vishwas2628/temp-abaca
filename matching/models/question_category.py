from django.db import models
from shared.models import TimestampedModel


class QuestionCategory(TimestampedModel):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "question categories"
