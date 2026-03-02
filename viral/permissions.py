from rest_framework import permissions, authentication, exceptions
from django.contrib.auth.models import User

from datetime import datetime, timedelta

from viral.models import UserProfile, AdminTokens


class IsGuest(permissions.BasePermission):
    """
    Custom permission to only allow guests
    """

    def has_permission(self, request, view):
        return not request.user or not request.user.is_authenticated


class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to see and edit it
    """

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.user.is_superuser


class IsCompanyOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        try:
            user_profile = UserProfile.objects.get(
                user=request.user, company=obj)
            return True
        except:
            return request.user.is_superuser


class AdminLoginAsAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        request_token = request.META.get('HTTP_AUTHORIZATION')
        if not request_token:
            return None

        try:
            admin_token = AdminTokens.objects.get(key=request_token[6:])

            date_now = datetime.now()
            token_creation_date = admin_token.created_at
            token_expiration_date = token_creation_date + timedelta(minutes=60)

            if date_now > token_expiration_date:
                raise exceptions.AuthenticationFailed('Invalid admin token')

            user_id = admin_token.user.id
            user = User.objects.get(pk=user_id)
        except AdminTokens.DoesNotExist:
            return None

        return (user, None)
