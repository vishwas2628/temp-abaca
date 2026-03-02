from uuid import uuid4
from django.db import models
from allauth.utils import get_user_model
from shared.models import TimestampedModel
from django.contrib.postgres.fields import JSONField

class AffiliateSubmissionDraft(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    affiliate = models.ForeignKey('Affiliate', on_delete=models.CASCADE)
    data = JSONField()