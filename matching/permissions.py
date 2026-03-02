from rest_framework import permissions

from viral.models import UserProfile
from matching.models import Supporter


class IsSupporter(permissions.BasePermission):

    def has_permission(self, request, view):
        return Supporter.objects.filter(user_profile__user=request.user).exists()
