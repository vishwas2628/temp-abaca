from django.contrib.postgres.fields import JSONField
from django.db import models
from simple_history.models import HistoricalRecords

from matching.managers.response_manager import ResponseManager
from matching.tests.schemas.response_value_schema import response_value
from shared.models import SanitizedModel, TimestampedModel
from shared.validators import JSONSchemaValidator


class Response(SanitizedModel, TimestampedModel):
    """
    Holds all the responses given by Entrepreneurs.

    Notes:
    - As of now, everytime a user submits a response that he has already given before,
    it will always be saved as a brand new one instead of updating the existing one.
    """
    value = JSONField(
        blank=True, null=True, validators=[JSONSchemaValidator(limit_value=response_value)],
        help_text='JSON object specifying the value: { "text": "" } or { "value": 1 } or { "min": 5, "max": 9 }')

    question = models.ForeignKey(
        'Question',
        on_delete=models.CASCADE,
        help_text='Question ID',
        related_name='responses'
    )
    user_profile = models.ForeignKey(
        'viral.UserProfile',
        on_delete=models.CASCADE,
        help_text='User Profile ID'
    )
    answers = models.ManyToManyField(
        'Answer', blank=True, help_text='Chosen Answers IDs')
    team_member = models.ForeignKey(
        'viral.TeamMember',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    # Keep a history of all updates done (except for the answers):
    # As of now, django-simple-history does not allow tracking m2m fields:
    # https://github.com/jazzband/django-simple-history/issues/399
    history = HistoricalRecords(
        excluded_fields=['user_profile', 'created_at', 'updated_at'],
        cascade_delete_history=True)

    objects = ResponseManager()

    def __str__(self):
        return self.question.entrepreneur_question + ' ' + (
            str(self.value) if self.value else ' - '.join(map(lambda answer: answer.value, self.answers.all())))
