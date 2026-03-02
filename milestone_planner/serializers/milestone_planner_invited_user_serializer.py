from rest_framework import serializers
from milestone_planner.models import UserInvitation
from shared.serializers import InvitedUserSerializer


class MilestonePlannerInvitedUserSerializer(InvitedUserSerializer):
    user_profile = serializers.CharField(source='userprofile.uid')
    name = serializers.CharField(source='userprofile.company.name')
    photo = serializers.ImageField(source='userprofile.company.logo', use_url=True, allow_null=True, read_only=True)
    is_form_owner = serializers.BooleanField()

    def get_email(self, user_invitation: UserInvitation):
        return super().get_email(user_invitation.userprofile)

    class Meta:
        model = UserInvitation
        fields = ['is_form_owner']
