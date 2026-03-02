from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from grid.models.category_level import CategoryLevel
from matching.models import Response
from milestone_planner.models import Milestone
from milestone_planner.serializers.milestone_evidence_serializer import MilestoneEvidenceSerializer
from milestone_planner.serializers.milestone_category_level_serializer import MilestoneCategoryLevelSerializer
from shared.utils import CurrentUserProfileDefault
from shared.mixins import ConditionalRequiredPerFieldMixin


class CreateMilestoneSerializer(ConditionalRequiredPerFieldMixin, serializers.ModelSerializer):
    user_profile = serializers.HiddenField(
        default=serializers.CreateOnlyDefault(CurrentUserProfileDefault())
    )
    evidence = MilestoneEvidenceSerializer(many=True, required=False)
    category_level = serializers.PrimaryKeyRelatedField(
        queryset=CategoryLevel.objects.filter(category__group=2))

    ERROR_INVALID_MILESTONE = 'invalid_milestone'
    ERROR_MISSING_PLAN_FIELDS = 'incomplete_plan'
    ERROR_MISSING_EVIDENCE_FIELDS = 'incomplete_evidence'

    default_error_messages = {
        ERROR_INVALID_MILESTONE: _("Invalid milestone."),
        ERROR_MISSING_PLAN_FIELDS: _("Missing required plan fields."),
        ERROR_MISSING_EVIDENCE_FIELDS: _("Missing required evidence fields."),
    }

    def is_target_date_required(self):
        plan_published = self.initial_data.get('plan_published', False)
        has_date_of_completion = 'date_of_completion' in self.initial_data
        has_evidence = 'evidence' in self.initial_data
        return bool(plan_published) is True and not has_date_of_completion and not has_evidence

    def is_date_of_completion_required(self):
        evidence_published = self.initial_data.get('evidence_published', False)
        return bool(evidence_published) is True

    def validate(self, attrs):
        attrs = super().validate(attrs)

        # 1a) Ensure that a plan publication includes every field.
        plan_fields = ['strategy', 'outcomes', 'resources', 'finances_needed']
        is_publishing_plan = attrs.get('plan_published', False)
        is_missing_plan_fields = any(bool(attrs.get(field) or type(attrs.get(field)) == int) is False
                                     for field in plan_fields)

        if is_publishing_plan and is_missing_plan_fields:
            self.fail(self.ERROR_MISSING_PLAN_FIELDS)

        # 1b) Ensure that a evidence publication includes at least date of completion.
        has_date_of_completion = attrs.get('date_of_completion', False)
        is_publishing_evidence = attrs.get('evidence_published', False)

        if is_publishing_evidence and not has_date_of_completion:
            self.fail(self.ERROR_MISSING_EVIDENCE_FIELDS)

        # 2) Otherwise, ensure that at least is submiting a valid draft:
        plan_fields = ['target_date', 'strategy', 'outcomes', 'resources', 'finances_needed']
        has_any_plan_field = any(bool(attrs.get(field) or type(attrs.get(field)) == int)
                                 is True for field in plan_fields)
        evidence = attrs.get('evidence', [])

        if not has_any_plan_field and bool(evidence) is False and not has_date_of_completion:
            self.fail(self.ERROR_INVALID_MILESTONE)

        return attrs

    def create(self, validated_data):
        # Decouple evidence from remaining milestone data to create in bulk later:
        evidence = validated_data.pop('evidence') if 'evidence' in validated_data else []

        # Create milestone from submitted data:
        milestone = Milestone.objects.create(**validated_data)

        # Bulk create evidence (responses)
        if len(evidence):
            responses = Response.objects.bulk_create_with_answers(
                evidence, user_profile=milestone.user_profile)

            milestone.evidence.set([response.pk for response in responses])

        milestone.update_state()
        return milestone

    class Meta:
        model = Milestone
        read_only_fields = ('state', 'created_at', 'updated_at')
        exclude = ('id',)
        validators = [
            UniqueTogetherValidator(
                queryset=Milestone.objects.all(),
                fields=['user_profile', 'category_level']
            )
        ]
