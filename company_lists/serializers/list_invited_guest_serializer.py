from rest_framework import serializers

from viral.models import UserGuest


class ListInvitedGuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserGuest
        exclude = ('id', 'created_at', 'updated_at')
