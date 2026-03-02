from django.db import models

from .timestamped_model import TimestampedModel


class Logs(TimestampedModel):
    slug = models.CharField(
        max_length=128,
        choices=[
            ('webapp', 'WebApp'),
            ('api', 'API'),
            ('mail', 'Mailjet'),
        ],
        blank=True
    )
    level = models.CharField(
        max_length=128,
        choices=[
            ('debug', 'Debug'),
            ('info', 'Info'),
            ('warn', 'Warn'),
            ('error', 'Error'),
            ('fatal', 'Fatal'),
        ],
        blank=True
    )
    log = models.TextField()

    def __str__(self):
        return self.slug
