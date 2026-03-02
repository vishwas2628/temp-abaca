from rest_framework import serializers

from milestone_planner.models import Milestone, MilestonePlanner
from milestone_planner.serializers.list_milestones_serializer import ListMilestonesSerializer
from milestone_planner.serializers.milestone_planner_invited_user_serializer import (
    MilestonePlannerInvitedUserSerializer,
)
from shared.serializers import InvitedGuestSerializer
from viral.models.user_guest import UserGuest
from viral.models.user_profile import UserProfile


class RetrieveOrUpdateMilestonePlannerSerializer(serializers.ModelSerializer):
    """
    Serializer for the Owner retrieving its Milestone Planner (with milestones).
    """

    milestones = serializers.SerializerMethodField()
    invited_users = serializers.SlugRelatedField(slug_field='uid', many=True, queryset=UserProfile.objects.all())
    invited_guests = serializers.SlugRelatedField(slug_field='uid', many=True, queryset=UserGuest.objects.all())

    def to_representation(self, instance):
        self.fields['invited_users'] = MilestonePlannerInvitedUserSerializer(source='userinvitation_set', many=True)
        self.fields['invited_guests'] = InvitedGuestSerializer(many=True)
        return super().to_representation(instance)

    def get_milestones(self, milestone_planner):
        milestones = (
            Milestone.objects.select_related(
                'user_profile', 'category_level__category', 'category_level__level', 'category_level__category__group'
            )
            .prefetch_related('evidence__question', 'evidence__answers')
            .filter(user_profile__company=milestone_planner.company)
        )
        return ListMilestonesSerializer(milestones, many=True).data

    class Meta:
        model = MilestonePlanner
        fields = ('uid', 'passcode', 'invited_users', 'invited_guests', 'milestones')
        read_only_fields = ('company', 'created_at', 'updated_at')
