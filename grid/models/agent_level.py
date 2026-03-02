from django.db import models
from shared.models import TimestampedModel


class AgentLevel(TimestampedModel):
    value = models.IntegerField()
    description = models.TextField()
