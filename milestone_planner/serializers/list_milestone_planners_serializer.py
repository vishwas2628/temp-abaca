from rest_framework import serializers

from milestone_planner.models import MilestonePlanner
from milestone_planner.serializers.milestone_planner_invited_user_serializer import MilestonePlannerInvitedUserSerializer
from shared.serializers import InvitedGuestSerializer


class ListMilestonePlannersSerializer(serializers.ModelSerializer):
    invited_users = MilestonePlannerInvitedUserSerializer(source='userinvitation_set', many=True)
    invited_guests = InvitedGuestSerializer(many=True)

    class Meta:
        model = MilestonePlanner
        fields = ('uid', 'passcode', 'invited_users', 'invited_guests')
