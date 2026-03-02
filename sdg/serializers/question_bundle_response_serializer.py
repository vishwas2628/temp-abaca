from rest_framework import serializers
from matching.models import Question
from sdg.models.sdg_response import Response


class QuestionBundleResponseSerializer(serializers.ModelSerializer):
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())  # pyright: ignore[reportAttributeAccessIssue]

    class Meta:
        model = Response
        exclude = ('user_profile',)
