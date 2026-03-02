from django.db import models
from django.contrib.postgres.fields import JSONField

from grid.managers import AssessmentManager
from shared.models import TimestampedModel


class Assessment(TimestampedModel):
    """
    Holds all the self-assessements done by Entrepreneurs.

    Notes:
    - As of now, everytime a user submits a self-assessment it will always be saved
    as a brand new one instead even if it doesn't change his overall level.
    """
    BEGAN_STATE = 0
    FINISHED_STATE = 1
    REGISTERED_USER_STATE = 2
    ASSESSMENT_STATES = (
        (BEGAN_STATE, 'Began Assessment'),
        (FINISHED_STATE, 'Finished Assessment'),
        (REGISTERED_USER_STATE, 'User Registered'),
    )

    level = models.ForeignKey('Level', on_delete=models.CASCADE)
    data = JSONField()
    user = models.IntegerField()
    evaluated = models.IntegerField(help_text='Company ID')
    hash_token = models.CharField(unique=True, max_length=40)
    state = models.IntegerField(
        choices=ASSESSMENT_STATES, blank=True, default=REGISTERED_USER_STATE)

    from_milestone_planner = models.BooleanField(
        default=False, help_text='Signals assessments that were generated from completing or uncompleting a milestone')

    # Add custom method to sync the assessment data with each milestone
    objects = AssessmentManager()
