from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from matching.models import Response
from milestone_planner.models import Milestone
from milestone_planner.serializers.milestone_evidence_serializer import MilestoneEvidenceSerializer
from shared.mixins import ConditionalRequiredPerFieldMixin


class UpdateMilestoneSerializer(ConditionalRequiredPerFieldMixin, serializers.ModelSerializer):
    target_date = serializers.DateField(required=False, allow_null=True)
    date_of_completion = serializers.DateField(required=False, allow_null=True)
    evidence = MilestoneEvidenceSerializer(many=True, required=False)

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
        return bool(evidence_published) is True and bool(self.instance.date_of_completion) is False

    def validate(self, attrs):
        attrs = super().validate(attrs)

        # 1a) Ensure that a plan publication includes every field.
        plan_fields = ['target_date', 'strategy', 'outcomes', 'resources', 'finances_needed']
        is_publishing_plan = attrs.get('plan_published', False)
        is_missing_plan_fields = any(bool(attrs.get(field) or type(attrs.get(field)) == int) is False
                                     for field in plan_fields)
        has_already_plan_fields = not any(bool(getattr(self.instance, field) or type(attrs.get(field)) == int)
                                          is False for field in plan_fields)

        if is_publishing_plan and is_missing_plan_fields and not has_already_plan_fields:
            self.fail(self.ERROR_MISSING_PLAN_FIELDS)

        # 1b) Ensure that a evidence publication includes at least date of completion.
        is_missing_date_of_completion = bool(attrs.get('date_of_completion')) is False
        is_publishing_evidence = attrs.get('evidence_published', False)
        has_already_evidence_fields = bool(self.instance.date_of_completion) and self.instance.evidence.exists()

        if is_publishing_evidence and is_missing_date_of_completion and not has_already_evidence_fields:
            self.fail(self.ERROR_MISSING_EVIDENCE_FIELDS)

        # 2) Otherwise, ensure that at least is updating into a valid milestone state:
        evidence_fields = ['date_of_completion', 'evidence']
        upcoming_updates = {
            # 2.1 Grab existing plan and evidence fields from instance
            **{field: getattr(self.instance, field) for field in plan_fields},
            **{field: getattr(self.instance, field) for field in evidence_fields},
            # 2.2 Grab submitted plan & evidence fields and override previous instance fields
            **{field: attrs.get(field) for field in plan_fields if field in attrs},
            **{field: attrs.get(field) for field in evidence_fields if field in attrs},
        }

        if all(bool(value or type(value) == int) is False for value in upcoming_updates.values()):
            self.fail(self.ERROR_INVALID_MILESTONE)

        return attrs

    def update(self, instance, validated_data):
        # Decouple evidence from remaining milestone data to create in bulk later:
        has_evidence = 'evidence' in validated_data
        evidence = validated_data.pop('evidence') if has_evidence else []

        # Update milestone from submitted data:
        updated_milestone = super().update(instance, validated_data)

        # Bulk create evidence (responses)
        if len(evidence):
            responses = Response.objects.bulk_create_with_answers(
                evidence, user_profile=instance.user_profile)
            updated_milestone.evidence.set([response.pk for response in responses])
        elif has_evidence:
            updated_milestone.evidence.clear()

        updated_milestone.update_state()
        return updated_milestone

    class Meta:
        model = Milestone
        read_only_fields = ('uid', 'state', 'user_profile', 'category_level', 'created_at', 'updated_at')
        exclude = ('id',)
