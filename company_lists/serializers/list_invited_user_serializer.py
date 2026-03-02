from rest_framework import serializers

from viral.models import Company
from matching.models import InterestedCTA


class ListInvitedUserSerializer(serializers.Serializer):
    user_profile = serializers.CharField(source='uid')
    email = serializers.SerializerMethodField()
    name = serializers.CharField(source='company.name')
    photo = serializers.ImageField(source='company.logo', use_url=True, allow_null=True, read_only=True)

    def get_email(self, user_profile):
        if not self.context['request'].user or not self.context['request'].user.is_authenticated:
            return None

        request_profile = self.context['request'].user.userprofile
        company = user_profile.company
        supporter = company if company.type == Company.SUPPORTER else request_profile.company
        entrepreneur = company if company.type == Company.ENTREPRENEUR else request_profile.company

        companies_are_connected = InterestedCTA.objects.filter(
            supporter=supporter, entrepreneur=entrepreneur, state_of_interest=InterestedCTA.CONNECTED).exists()
        return company.email if companies_are_connected else ""
