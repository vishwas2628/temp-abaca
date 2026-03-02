from django.db import models
from shared.models import SanitizedModel, TimestampedModel


class Answer(SanitizedModel, TimestampedModel):
    value = models.CharField(max_length=100)
    question = models.ForeignKey(
        'Question',
        on_delete=models.CASCADE,
        # related_name='answers'
    )
    order = models.PositiveIntegerField(default=0)  # pyright: ignore
    instructions = models.TextField(null=True, blank=True, max_length=300)

    def __str__(self):
        return self.question.entrepreneur_question + ' > ' + self.value  # pyright: ignore

    class Meta:  # pyright: ignore
        ordering = (
            'order',
            'id',
        )
