from django.db import models
from shared.models import TimestampedModel
from enum import Enum


class InterestedCTA(TimestampedModel):
    supporter = models.ForeignKey(
        'viral.Company',
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name='supporter_company_id',
        help_text='Company ID of Supporter'
    )
    entrepreneur = models.ForeignKey(
        'viral.Company',
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name='entrepreneur_company_id',
        help_text='Company ID of Entrepreneur'
    )

    INITIAL_VALUE = 0
    INTERESTED = 1
    CONNECTED = 2
    INTEREST_PAST = 3
    INTEREST_CHOICES = (
        (INITIAL_VALUE, 'None'),
        (INTERESTED, 'Request Sent'),
        (CONNECTED, 'Connected'),
        (INTEREST_PAST, 'Past Connection'),
    )

    supporter_is_interested = models.IntegerField(
        choices=INTEREST_CHOICES,
        default=INITIAL_VALUE,
        help_text='0 (Initial) 1 (Interested)'
    )

    entrepreneur_is_interested = models.IntegerField(
        choices=INTEREST_CHOICES,
        default=INITIAL_VALUE,
        help_text='0 (Initial) 1 (Interested)'
    )

    state_of_interest = models.IntegerField(
        choices=INTEREST_CHOICES,
        default=INITIAL_VALUE,
        help_text='0 (No connection) 1 (Someone has interest) 2 (Connected) 3 (Disconnected)'
    )

    class Meta:
        # Make possible to only have one type of metadata
        # for each supporter - entrepreneur.
        unique_together = ('supporter', 'entrepreneur',)
        verbose_name = "Connection"
