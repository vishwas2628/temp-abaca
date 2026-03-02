from django.db import models
from django.contrib.postgres.fields import JSONField
from shared.models import SanitizedModel, TimestampedModel
from shared.validators import JSONSchemaValidator
from matching.models.response import Response
from matching.tests.schemas.criteria_desired_schema import criteria_desired


class Criteria(SanitizedModel, TimestampedModel):
    name = models.CharField(max_length=100)
    description = models.TextField()
    desired = JSONField(
        blank=True, null=True, validators=[JSONSchemaValidator(limit_value=criteria_desired)],
        help_text="""JSON object specifying the desired value:
        { "text": "" } or { "value": 1 } or { "min": 5, "max": 9 }""")

    criteria_weight = models.ForeignKey(
        'CriteriaWeight',
        on_delete=models.CASCADE,
        help_text='Criteria weight ID'
    )
    supporter = models.ForeignKey(
        'Supporter',
        on_delete=models.CASCADE,
        help_text='Supporter ID'
    )
    question = models.ForeignKey(
        'Question',
        on_delete=models.CASCADE,
        help_text='Question ID'
    )
    answers = models.ManyToManyField(
        'Answer', blank=True, help_text='Chosen Answers IDs')

    is_active = models.BooleanField(default=True, help_text='To filter outdated Criteria of a Supporter')

    def __str__(self):
        return self.name

    def get_responses(self):
        return Response.objects.filter(user_profile=self.supporter.user_profile, question=self.question).first()
