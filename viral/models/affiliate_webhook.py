from django.db import models

from shared.models import TimestampedModel


class AffiliateWebhook(TimestampedModel):
    ENTREPRENEUR_PROGRAM = 'program'
    SUPPORTER_PROGRAM = 'supporter-program'

    WEBHOOK_SCHEMAS = (
        (ENTREPRENEUR_PROGRAM, 'Entrepreneur Program (Question Bundles)'),
        (SUPPORTER_PROGRAM, 'Supporter Program (Question Bundles)')
    )

    name = models.CharField(max_length=128)
    url = models.URLField()
    schema = models.CharField(
        choices=WEBHOOK_SCHEMAS,
        default=ENTREPRENEUR_PROGRAM,
        max_length=128
    )

    def __str__(self):
        return self.name
