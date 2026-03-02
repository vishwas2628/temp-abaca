from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.db import models
from simple_history.models import HistoricalRecords

from milestone_planner.managers import MilestoneManager
from shared.models import TimestampedModel, UniqueUID


class Milestone(TimestampedModel, UniqueUID):
    TO_BE_PLANNED_STATE = 'to-be-planned'
    PLANNED_STATE = 'planned'
    IN_PROGRESS_STATE = 'in-progress'
    COMPLETED_STATE = 'completed'

    MILESTONE_STATES = (
        (TO_BE_PLANNED_STATE, 'To Be Planned'),
        (PLANNED_STATE, 'Planned'),
        (IN_PROGRESS_STATE, 'In Progress'),
        (COMPLETED_STATE, 'Completed'),
    )

    user_profile = models.ForeignKey(
        'viral.UserProfile',
        on_delete=models.CASCADE,
        related_name='milestones'
    )
    category_level = models.ForeignKey(
        'grid.CategoryLevel',
        on_delete=models.CASCADE,
        related_name='milestones',
    )
    critical = models.BooleanField(default=False)

    # Plan:
    strategy = models.TextField(blank=True)
    outcomes = models.TextField(blank=True)
    resources = models.TextField(blank=True)
    finances_needed = models.PositiveIntegerField(blank=True, null=True)
    target_date = models.DateField(blank=True, null=True)
    plan_published = models.BooleanField(default=False)

    # Evidence:
    evidence = models.ManyToManyField(
        'matching.Response',
        related_name='milestones',
        help_text='Responses given as evidence of a Milestone completed.',
        blank=True
    )
    evidence_published = models.BooleanField(default=False)
    date_of_completion = models.DateField(blank=True, null=True)

    # Keep a history of all updates done:
    history = HistoricalRecords(
        excluded_fields=['uid', 'category_level', 'user_profile', 'created_at', 'updated_at'],
        cascade_delete_history=True)

    # Add custom method to sync the assessment data with each milestone
    objects = MilestoneManager()

    # Holds the latest milestone state which will be useful to
    # track its progress in time through the model's history
    state = models.CharField(
        choices=MILESTONE_STATES,
        default=COMPLETED_STATE,
        max_length=128
    )

    @property
    def has_any_plan_field(self):
        plan_fields = ['target_date', 'strategy', 'outcomes', 'resources', 'finances_needed']
        return any(bool(getattr(self, field) or type(getattr(self, field)) == int) is True for field in plan_fields)

    @property
    def has_any_evidence_field(self):
        return bool(self.date_of_completion) or self.evidence.exists()

    @property
    def has_milestones_completed_above(self):
        """Returns whether if the current milestone has others completed above in its category."""
        return Milestone.objects.filter(
            user_profile=self.user_profile, category_level__level__value__gt=self.category_level.level.value,
            category_level__category=self.category_level.category, state=self.COMPLETED_STATE).exists()

    @property
    def current_state(self):
        """Returns the milestone's current state."""
        if self.evidence_published is False and (self.evidence.exists() or self.date_of_completion):
            return self.IN_PROGRESS_STATE
        elif self.date_of_completion and self.evidence_published:
            return self.COMPLETED_STATE
        if self.plan_published:
            return self.PLANNED_STATE
        elif self.has_any_plan_field:
            return self.TO_BE_PLANNED_STATE

    @property
    def state_formatted(self):
        return ' '.join(map(lambda word: word.capitalize(), self.current_state.split("-")))

    def update_state(self):
        # Ensure proper published states:
        if not self.has_any_plan_field:
            self.plan_published = False
        if not self.has_any_evidence_field:
            self.evidence_published = False

        # Helper method to update the milestone's state upon, for example, adding new evidence.
        self.state = self.current_state
        self.save()

    def clean(self):
        # Ensure that publishing a plan includes every field:
        plan_fields = ['strategy', 'outcomes', 'resources', 'finances_needed']
        has_missing_plan_fields = any(bool(getattr(self, field)) is False for field in plan_fields)
        if self.plan_published and has_missing_plan_fields:
            raise ValidationError(_('Cannot publish plan without filling all its required fields.'))

        # Ensure that publishing evidence includes every field:
        evidence_fields = ['date_of_completion', 'evidence']
        has_missing_evidence_fields = any(bool(getattr(self, field)) is False for field in evidence_fields)
        if self.evidence_published and has_missing_evidence_fields:
            raise ValidationError(_('Cannot publish evidence without filling all its required fields.'))

        # Ensure that new changes to a milestone reflect a valid state:
        if not self.current_state:
            raise ValidationError(_('Invalid milestone state. Please add at least a target or completion date.'))

    def save(self, *args, **kwargs):
        # Update the state field upon each new change:
        if self.pk:
            self.state = self.current_state
        super().save(*args, **kwargs)

    def __str__(self):
        # Check if instance has references before printing referenced values:
        if hasattr(self, 'user_profile'):
            return f'{self.user_profile.company.name} : ' + \
                f'{self.category_level.category.name} {self.category_level.level.value}'

        # Otherwise, it's an historic instance without references, and we can just print a generic name:
        # https://github.com/jazzband/django-simple-history/issues/521
        return _('Milestone')

    class Meta:
        # Only allow having a single milestone of a CategoryLevel per UserProfile
        unique_together = ('user_profile', 'category_level',)
