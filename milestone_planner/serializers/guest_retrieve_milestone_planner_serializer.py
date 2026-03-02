from rest_framework import serializers

from milestone_planner.models import MilestonePlanner, Milestone
from milestone_planner.serializers import ListMilestonesSerializer


class GuestRetrieveMilestonePlannerSerializer(serializers.ModelSerializer):
    """
    Serializer for a Guest retrieving a Milestone Planner (with milestones).
    """
    milestones = serializers.SerializerMethodField()

    def get_milestones(self, milestone_planner):
        milestones = Milestone.objects.select_related(
            'user_profile', 'category_level__category', 'category_level__level', 'category_level__category__group'
        ).prefetch_related('evidence__question', 'evidence__answers').filter(user_profile__company=milestone_planner.company)
        return ListMilestonesSerializer(milestones, many=True).data

    class Meta:
        model = MilestonePlanner
        fields = ('uid', 'company', 'milestones')
        read_only_fields = ('created_at', 'updated_at')
