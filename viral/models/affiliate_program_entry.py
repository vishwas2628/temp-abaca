from django.db import models
from django.contrib.postgres.fields import JSONField

from shared.models import TimestampedModel, UniqueUID


class AffiliateProgramEntry(TimestampedModel, UniqueUID):
    """
    Track Entrepreneur submissions to Affiliate Programs

    TODO: Rename this model to a more meaningful name:
    AffiliateProgramEntrepreneurSubmission
    But considering these hurdles:
    * Renaming all references on the application without regressions;
    * Avoid loosing any data on the database;
    """
    affiliate = models.ForeignKey(
        'Affiliate',
        on_delete=models.CASCADE
    )
    user_profile = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE
    )
    assessment = models.ForeignKey(
        'grid.Assessment',
        on_delete=models.CASCADE
    )
    responses = models.ManyToManyField(
        'matching.Response',
        blank=True
    )

    team_members = JSONField(null=True, blank=True)

    class Meta:
        unique_together = ('affiliate', 'assessment',)
        verbose_name = 'Affiliate Program - Entrepreneur submission'
        verbose_name_plural = 'Affiliate Program - Entrepreneur submissions'
