from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework import permissions, exceptions

from viral.models import UserGuest, Company


class IsMilestoneOwnerOrReadOnly(permissions.BasePermission):

    def has_object_permission(self, request, view, milestone):
        is_safe_operation = request.method in permissions.SAFE_METHODS
        is_milestone_owner = milestone.user_profile.user == request.user or request.user.is_superuser

        return is_safe_operation or is_milestone_owner


class IsMilestonePlannerOwnerOrUserWithPermissionsToRead(permissions.BasePermission):
    """
    Determine if:
    a) The request user is the owner of the given MilestonePlanner
    or
    b) It's a safe method and is either:
    b1) An authenticated Supporter
    b2) A valid guest
    """

    def _is_owner_or_admin(self, request, milestone_planner):
        return milestone_planner.company.company_profile.pk == request.user.userprofile.pk or request.user.is_superuser if request.user and request.user.is_authenticated else False

    def _has_valid_passcode(self, request, milestone_planner):
        request_passcode = request.query_params.get('passcode', None)
        return bool(milestone_planner.passcode) is False or milestone_planner.passcode == request_passcode
    
    def _is_invited_user(self, request, milestone_planner):
        return request.user.is_authenticated and milestone_planner.invited_users.filter(user=request.user).exists()

    def _check_passcode(self, request, milestone_planner):
        if self._is_owner_or_admin(request, milestone_planner):
            return True
        
        if self._is_invited_user(request, milestone_planner):
            return True
        
        list_has_passcode = bool(milestone_planner.passcode)
        was_updated_recently = bool(milestone_planner.previous_passcode) and \
            milestone_planner.passcode != milestone_planner.previous_passcode
        has_valid_passcode = self._has_valid_passcode(request, milestone_planner)

        if list_has_passcode and not has_valid_passcode:
            if was_updated_recently:
                raise exceptions.PermissionDenied(detail='Passcode has been updated.', code='passcode_updated')
            raise exceptions.PermissionDenied(detail='Invalid passcode', code='invalid_passcode')
        
        return True

    def _is_valid_guest(self, request):
        # Skip verification if user is authenticated.
        if request.user and request.user.is_authenticated:
            return False

        guest_email = request.query_params.get('email', None)
        # Check if it's a valid email:
        try:
            validate_email(guest_email)
        except ValidationError as error:
            raise exceptions.ValidationError(error)

        # Check if email is registered:
        return UserGuest.objects.filter(email__iexact=guest_email).exists()

    def _is_supporter_logged(self, request):
        return request.user and request.user.is_authenticated and request.user.userprofile.company.type == Company.SUPPORTER

    def has_object_permission(self, request, view, milestone_planner):
        is_safe_method = request.method in permissions.SAFE_METHODS

        return (
            self._is_owner_or_admin(request, milestone_planner) or
            is_safe_method and
            # Checking Supporter first to avoid asking unnecessarily
            # a passcode and then blocking access to Entrepreneurs:
            (self._is_supporter_logged(request) and
             self._check_passcode(request, milestone_planner) or
             # Checking passcode first to ensure that only allowed
             # Guests will access a Milestone Planner:
             self._check_passcode(request, milestone_planner) and
             self._is_valid_guest(request))
        )
