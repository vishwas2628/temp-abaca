from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from matching.models import Response, Question, QuestionType
from milestone_planner.schemas.milestone_evidence_value_schema import MILESTONE_EVIDENCE_VALUE_SCHEMA
from shared.validators import JSONSchemaSerializerValidator


class MilestoneEvidenceSerializer(serializers.ModelSerializer):
    """
    Serializer for a Milestone's evidence.
    """
    value = serializers.JSONField(required=False, validators=[JSONSchemaSerializerValidator(schema=MILESTONE_EVIDENCE_VALUE_SCHEMA)])
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())

    def validate(self, attrs):
        """
        1 - Require a value since, for now, we are only accepting free responses
        2 - Check for all questions with answers, that every answer belongs in fact to that question.
        """
        question = attrs.get('question', None)
        value = attrs.get('value', None)
        is_select_question = question.question_type.type in [
            QuestionType.SINGLE_SELECT, QuestionType.MULTI_SELECT] if question else False

        if not is_select_question and not value:
            raise serializers.ValidationError({'value': _('This field is required.')}, code='required')
        
        return attrs

    class Meta:
        model = Response
        fields = ('value', 'question')
