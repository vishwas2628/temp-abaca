from uuid import uuid4
from django.db import models
from rest_framework.authentication import get_user_model
from shared.models.timestamped_model import TimestampedModel


class Consent(TimestampedModel):
    CAPITAL_EXPLORER_TYPE = 'capital_explorer'
    SDG_REPORT_TYPE = 'sdg_report'
    CONSENT_TYPE_CHOICES = [
        (CAPITAL_EXPLORER_TYPE, "Capital Explorer"),
        (SDG_REPORT_TYPE, "SDG Report"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
    )
    consent_type = models.CharField(
        max_length=128,
        choices=CONSENT_TYPE_CHOICES,
    )

    def __str__(self):
        return f'[{self.get_consent_type_display()}] {self.user.get_username()}'

    # class Meta:
    #     constraints = [models.UniqueConstraint(fields=['user', 'consent_type'], name='unique_user_consent')]
