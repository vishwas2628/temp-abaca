from rest_framework.exceptions import PermissionDenied, ParseError
from rest_framework.permissions import BasePermission

from viral.models import UserGuest, Company


class CanViewSubmission(BasePermission):
    def _is_owner(self, request, submission):
        return request.user.is_authenticated and submission.company_id == request.user.userprofile.company_id
    
    def _is_invited_user(self, request, submission):
        return request.user.is_authenticated and submission.invited_users.filter(user=request.user).exists()

    def _is_entrepreneur(self, request):
        return request.user.is_authenticated and request.user.userprofile.company.type == Company.ENTREPRENEUR

    def _is_guest(self, request):
        return UserGuest.objects.filter(email__iexact=request.GET.get('email')).exists()

    def _check_passcode(self, request, submission):
        passcode = request.GET.get('passcode')

        # If submission is passcode-protected, and the wrong passcode was provided
        if submission.passcode and passcode != submission.passcode:
            # Raise specific error if the previous passcode was provided
            if passcode and passcode == submission.previous_passcode:
                raise PermissionDenied(detail='Passcode has been updated', code='passcode_updated')

            raise PermissionDenied(detail='Invalid passcode', code='invalid_passcode')

    def has_object_permission(self, request, view, submission): 
        # Entrepreneurs are not allowed to view other user's submissions (HTTP 403)
        if self._is_entrepreneur(request) and not self._is_owner(request, submission):
            return False
        
        # Only invited users or guests are allowed to view the submission (HTTP 403)
        if request.user.is_authenticated and not self._is_invited_user(request, submission):
            return False
        
        # Unless the user is the owner or an invited user, a valid
        # passcode must be provided (if passcode protected) (HTTP 403)
        if not self._is_owner(request, submission) and not self._is_invited_user(request, submission):
            self._check_passcode(request, submission)

        # Either a guest email or an auth token must be provided (HTTP 400)
        if not request.user.is_authenticated and not self._is_guest(request):
            raise ParseError(detail='Enter a valid email address.', code='invalid')
    
        return True
