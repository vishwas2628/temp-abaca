from uuid import uuid4
from django.db import models

from shared.models import TimestampedModel


class TeamMember(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    company = models.ForeignKey(
        'Company',
        on_delete=models.CASCADE,
    )
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField()
    position = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True, help_text='Inactive Team Members will not be visible for the users')

    def responses(self):
        return self.response_set.distinct('question_id').order_by('question_id', '-created_at')

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.position})'
