from django.db import models
from shared.models import UniqueUID
from shared.models import TimestampedModel


class SDGAffiliateProgramEntry(TimestampedModel, UniqueUID):
    affiliate = models.ForeignKey(
        'viral.Affiliate',
        on_delete=models.CASCADE,
        related_name='%(class)s_affiliate',
    )
    user_profile = models.ForeignKey(
        'viral.UserProfile',
        on_delete=models.CASCADE,
        related_name='%(class)s_user_profile',
    )
    responses = models.ManyToManyField(
        'sdg.Response',
        blank=True,
        related_name='%(class)s_responses',
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        verbose_name = 'Affiliate Program - Entrepreneur submission'
        verbose_name_plural = 'Affiliate Program - Entrepreneur submissions'
