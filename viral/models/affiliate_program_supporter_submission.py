from django.db import models
from django.contrib.postgres.fields import IntegerRangeField, JSONField

from shared.models import TimestampedModel, UniqueUID
from matching.models.supporter import validate_level_range


class AffiliateProgramSupporterSubmission(TimestampedModel, UniqueUID):
    """
    Track Supporter submissions to Affiliate Programs
    """
    affiliate = models.ForeignKey(
        'Affiliate',
        on_delete=models.CASCADE
    )
    supporter = models.ForeignKey(
        'matching.Supporter',
        on_delete=models.CASCADE
    )

    investing_level_range = IntegerRangeField(null=True, validators=[validate_level_range])

    """
    Sectors & Locations are stored in JSON as they will only be used as static data.
    Keep in mind that any structural changes to the current sectors & locations entities or payloads
    will require creating a normalization script to update all JSON values' to match a new structure.
    """
    sectors_of_interest = JSONField(null=True, blank=True)
    locations_of_interest = JSONField(null=True, blank=True)

    criteria = models.ManyToManyField(
        'matching.Criteria',
        related_name='criteria',
        help_text='Responses given on a Question Bundle.',
        blank=True
    )

    additional_criteria = models.ManyToManyField(
        'matching.Criteria',
        related_name='additional_criteria',
        help_text='Optional responses outside of a Question Bundle.',
        blank=True
    )

    team_members = JSONField(null=True, blank=True)

    class Meta:
        verbose_name = 'Affiliate Program - Supporter submission'
        verbose_name_plural = 'Affiliate Program - Supporter submissions'
