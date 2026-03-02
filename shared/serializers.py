import os
import re
from django.db.models import Q

from rest_framework import serializers
from matching.models.interested_cta import InterestedCTA

from shared.mailjet.mailjet import sendEmailWithoutTemplate
from viral.models.user_profile import UserProfile


class SupportSuggestionSerializer(serializers.Serializer):
    author = serializers.EmailField(required=False)
    subject = serializers.CharField()
    message = serializers.CharField()

    def submit(self, validated_data):
        admin_email = os.getenv('ADMIN_EMAIL', 'abaca-dev@wearepixelmatters.com')
        sendEmailWithoutTemplate(admin_email, validated_data)


class InvitedUserSerializer(serializers.Serializer):
    user_profile = serializers.CharField(source='uid')
    email = serializers.SerializerMethodField()
    name = serializers.CharField(source='company.name')
    photo = serializers.ImageField(source='company.logo', use_url=True, allow_null=True, read_only=True)

    # The invited user email should only be revealed if the two companies are connected
    def get_email(self, user_profile: UserProfile):
        try:
            request_company = self.context['request'].user.userprofile.company
            invited_company = user_profile.company
        except:
            return None

        # Only companies of different types can be connected
        if request_company.type != invited_company.type: 
            companies_are_connected = InterestedCTA.objects.filter(
                Q(supporter=request_company, entrepreneur=invited_company) | Q(entrepreneur=request_company, supporter=invited_company),
                state_of_interest=InterestedCTA.CONNECTED
            ).exists()
            return invited_company.email if companies_are_connected else None
        
        return None


class InvitedGuestSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField()
