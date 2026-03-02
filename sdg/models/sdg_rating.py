from django.db import models
from shared.models.timestamped_model import TimestampedModel


class SdgRating(TimestampedModel):
    company_list = models.ForeignKey(
        'company_lists.CompanyList',
        related_name="+",
        on_delete=models.DO_NOTHING,
        null=False,
        blank=False,
    )
    company = models.ForeignKey(
        'viral.Company',
        on_delete=models.DO_NOTHING,
        null=False,
        blank=False,
    )
    impact_rating = models.CharField(max_length=255)
    impact_score = models.IntegerField()
    impact_negative = models.IntegerField()
    impact_positive = models.IntegerField()
