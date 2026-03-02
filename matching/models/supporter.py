from django.db import models
from django.contrib.postgres.fields import IntegerRangeField
from django.core.exceptions import ValidationError
from shared.models import SanitizedModel, TimestampedModel
from psycopg2.extras import NumericRange

from matching.models.supporter_offering import SupporterOffering
from matching.models.criteria import Criteria


def validate_level_range(value):
    if not isinstance(value, NumericRange):
        raise ValidationError("invalid range")
    elif (value.lower == value.upper):
        raise ValidationError(
            "to select a single range level, clear one of the input's value")
    elif (value.lower is not None and value.lower < 1) or (value.upper is not None and value.upper > 10):
        raise ValidationError("range must be from 1 to 9")


class ActiveSupporterManager(models.Manager):
    """
    As of now, what constitutes an active Supporter is:
    * Having a user_profile
    * Having the active flag as True
    """
    use_for_related_fields = True

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True).exclude(user_profile=None)


class Supporter(SanitizedModel, TimestampedModel):
    # Override supporter query list default to exclude inactive users
    objects = ActiveSupporterManager()
    # Custom attribute to list active & inactive users
    all_supporters = models.Manager()

    # Control wether or not a Supporter should be excluded from the App.
    is_active = models.BooleanField(default=True)

    name = models.CharField(max_length=100)
    about = models.TextField(blank=True)
    email = models.EmailField()
    types = models.ManyToManyField('SupporterType', blank=True)

    user_profile = models.ForeignKey(
        'viral.UserProfile',
        on_delete=models.CASCADE,
        related_name='supporter',
        blank=True, null=True
    )

    locations = models.ManyToManyField(
        'viral.Location', through='SupporterInterestLocation', blank=True)
    locations_weight = models.ForeignKey(
        'CriteriaWeight', on_delete=models.CASCADE, related_name='+', null=True)
    sectors = models.ManyToManyField(
        'viral.Sector', through='SupporterInterestSector', blank=True)
    sectors_weight = models.ForeignKey(
        'CriteriaWeight', on_delete=models.CASCADE, related_name='+', null=True)
    investing_level_range = IntegerRangeField(validators=[validate_level_range])
    level_weight = models.ForeignKey(
        'CriteriaWeight', on_delete=models.CASCADE, related_name='+', null=True)

    class Meta:
        verbose_name_plural = "supporters"

    @property
    def formatted_level_range(self):
        # Dash separated range (e.g. 1 - 2)
        level_range = str(self.investing_level_range.lower)
        level_range += ' - {}'.format(
            self.investing_level_range.upper) if self.investing_level_range.upper else ''
        return level_range

    def __str__(self):
        return self.name

    def get_offers(self):
        """
        Get list of offers associated with this supporter.
        """
        return SupporterOffering.objects.filter(supporter=self)

    def get_offers_with_prefetch(self):
        return SupporterOffering.objects.select_related('category').prefetch_related('types').filter(supporter=self)

    def get_criteria(self):
        """
        Get list of criteria associated with this supporter.
        """
        return Criteria.objects.filter(supporter=self, is_active=True)

    def get_criteria_with_prefetch(self):
        return Criteria.objects.select_related('question').prefetch_related(
            'question__question_type', 'question__question_category').prefetch_related('answers').filter(
            supporter=self, is_active=True)


class SupporterWizard(Supporter):
    """
    Proxy model for creating an all-purpose supporter wizard form
    """
    class Meta():
        proxy = True
        verbose_name = 'Complete Supporter'
        verbose_name_plural = 'Supporters Wizard'
