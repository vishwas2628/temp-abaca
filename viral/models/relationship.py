from django.db import models


from shared.models import TimestampedModel


class Relationship(TimestampedModel):
    match = models.BooleanField()
    investor = models.OneToOneField(
        'UserProfile',
        related_name='user_investor',
        on_delete=models.CASCADE,
    )
    entrepreneur = models.OneToOneField(
        'UserProfile',
        related_name='user_entrepreneur',
        on_delete=models.CASCADE,
    )
    creator = models.OneToOneField(
        'UserProfile',
        related_name='user_creator',
        on_delete=models.CASCADE
    )
