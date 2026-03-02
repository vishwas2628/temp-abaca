from rest_framework import serializers

from grid.models import CategoryLevel
from grid.serializers import CategorySerializer
from shared.mixins import TranslationsSerializerMixin


class MilestoneCategoryLevelSerializer(TranslationsSerializerMixin, serializers.ModelSerializer):
    """
    Serializer for a Milestone's category level.
    """
    level = serializers.SlugRelatedField(
        read_only=True,
        slug_field='value'
    )
    category = CategorySerializer()

    class Meta:
        model = CategoryLevel
        fields = '__all__'

    class Translations:
        exclude = ['achievements', 'description', 'requirements', 'next_milestones_title',
                   'next_milestones_description', 'achieved_milestones_title',
                   'achieved_milestones_description']
