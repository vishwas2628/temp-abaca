from uuid import uuid4
from django.contrib.postgres.fields import JSONField
from django.db import models
from tinymce import HTMLField
from shared.models.sanitized_model import SanitizedModel
from shared.models.timestamped_model import TimestampedModel
from shared.models.unique_uid import UniqueUID
from shared.validators import JSONSchemaValidator
from matching.tests.schemas.response_value_schema import response_value
from matching.tests.schemas.criteria_desired_schema import criteria_desired
from capital_explorer.schema import submission_schema
from sortedm2m.fields import SortedManyToManyField


class CompanyStage(TimestampedModel):
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0, db_index=True)

    def __str__(self):
        return self.name


class FundingType(TimestampedModel):
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0, db_index=True)

    def __str__(self):
        return self.name


class FundingStage(TimestampedModel):
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0, db_index=True)

    def __str__(self):
        return self.name


class FundingSource(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    funding_types = SortedManyToManyField('FundingType')
    funding_stages = SortedManyToManyField('FundingStage')
    company_stages = SortedManyToManyField('CompanyStage')
    about = HTMLField()
    key_characteristics = HTMLField()
    key_implications = HTMLField()
    related_links = HTMLField(null=True, blank=True)

    def __str__(self):
        return self.name


class FundingCriteria(SanitizedModel, TimestampedModel):
    funding_source = models.ForeignKey('FundingSource', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    desired = JSONField(
        blank=True,
        null=True,
        validators=[JSONSchemaValidator(limit_value=criteria_desired)],
        help_text="""JSON object specifying the desired value:
        { "text": "" } or { "value": 1 } or { "min": 5, "max": 9 }""",
    )

    criteria_weight = models.ForeignKey('CriteriaWeight', on_delete=models.CASCADE)
    question = models.ForeignKey('matching.Question', on_delete=models.CASCADE)
    answers = models.ManyToManyField('matching.Answer', blank=True)

    def __str__(self):
        return f'[{self.funding_source.name}] {self.name}'

    class Meta:
        verbose_name_plural = 'Funding criteria'


class CriteriaWeight(TimestampedModel):
    name = models.CharField(max_length=100)
    value_matched = models.IntegerField()
    value_unmatched = models.IntegerField()
    value_unanswered = models.IntegerField()

    def __str__(self):
        return self.name


class Submission(TimestampedModel, UniqueUID):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    company = models.OneToOneField(
        'viral.Company', on_delete=models.CASCADE, related_name='capital_explorer_submissions'
    )
    responses = JSONField(
        blank=True,
        null=True,
        validators=[JSONSchemaValidator(limit_value=submission_schema)],
    )
    passcode = models.CharField(max_length=20, null=True, blank=True)
    previous_passcode = models.CharField(max_length=20, null=True, blank=True)
    invited_users = models.ManyToManyField('viral.UserProfile', blank=True)
    invited_guests = models.ManyToManyField('viral.UserGuest', blank=True)

    __original_passcode = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_passcode = self.passcode

    def save(self, *args, **kwargs):
        # Automatically update previous passcode:
        if self.passcode != self.__original_passcode:
            self.previous_passcode = self.__original_passcode

        super().save(*args, **kwargs)
        self.__original_passcode = self.passcode
