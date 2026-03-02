from rest_framework import serializers

from milestone_planner.models import Milestone
from milestone_planner.serializers.milestone_category_level_serializer import MilestoneCategoryLevelSerializer
from milestone_planner.serializers.milestone_evidence_serializer import MilestoneEvidenceSerializer


class ListMilestonesSerializer(serializers.ModelSerializer):
    user_profile = serializers.SlugRelatedField(
        read_only=True,
        slug_field='uid'
    )
    category_level = MilestoneCategoryLevelSerializer()
    evidence = MilestoneEvidenceSerializer(many=True)

    # Custom flags
    planned = serializers.SerializerMethodField()
    in_progress = serializers.SerializerMethodField()
    completed = serializers.SerializerMethodField()
    evidence_provided = serializers.SerializerMethodField()

    def get_planned(self, instance):
        return instance.state == Milestone.PLANNED_STATE

    def get_in_progress(self, instance):
        return instance.state == Milestone.IN_PROGRESS_STATE

    def get_completed(self, instance):
        return instance.state == Milestone.COMPLETED_STATE

    def get_evidence_provided(self, instance):
        return instance.evidence.exists()

    class Meta:
        model = Milestone
        read_only_fields = ('state', 'created_at', 'updated_at')
        exclude = ('id',)
