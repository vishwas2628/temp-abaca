from rest_framework import permissions, exceptions
from company_lists.models import CompanyList


class IsCompanyListOwnerOrReadOnly(permissions.BasePermission):
    """
    Determine if:
    a) The request user is the owner of the given CompanyList
    or
    b) It's a safe method and:
    b1) It's an authenticated user invited to the given CompanyList
    b2) It's an existing user guest
    """

    def _is_owner_or_admin(self, request, company_list):
        if request.user and request.user.is_authenticated:
            if request.user.is_superuser:
                return True
            elif company_list.company_list_type == CompanyList.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS:
                affiliate_company = company_list.affiliate.company
                return request.user.userprofile.supporter.first() in company_list.affiliate.supporters.all() or (
                    affiliate_company and affiliate_company.company_profile.user == request.user)
            else:
                return company_list.owner.pk == request.user.userprofile.pk
        return False

    def _has_valid_passcode(self, request, company_list):
        request_passcode = request.query_params.get('passcode', None)
        return bool(company_list.passcode) is False or company_list.passcode == request_passcode

    def _check_passcode(self, request, company_list):
        is_owner_or_admin = self._is_owner_or_admin(request, company_list)
        list_has_passcode = bool(company_list.passcode)
        was_updated_recently = bool(company_list.previous_passcode) and \
            company_list.passcode != company_list.previous_passcode
        has_valid_passcode = self._has_valid_passcode(request, company_list)

        if not is_owner_or_admin and list_has_passcode and not has_valid_passcode:
            if was_updated_recently:
                raise exceptions.PermissionDenied(detail='Passcode has been updated.', code='passcode_updated')
            raise exceptions.PermissionDenied(detail='Invalid passcode', code='invalid_passcode')
        return True

    def _is_valid_guest(self, request):
        is_authenticated = request.user and request.user.is_authenticated
        guest_email = request.query_params.get('email', None)

        if is_authenticated:
            return False

        if not bool(guest_email):
            raise exceptions.ValidationError(detail='Missing email', code='missing_email')
        return True

    def _is_user_invited(self, request, company_list):
        is_authenticated = request.user and request.user.is_authenticated
        return company_list.invited_users.filter(user=request.user).exists() if is_authenticated else False

    def has_object_permission(self, request, view, company_list):
        is_safe_method = request.method in permissions.SAFE_METHODS

        return (
            self._is_owner_or_admin(request, company_list) or
            is_safe_method and
            self._check_passcode(request, company_list) and
            (self._is_user_invited(request, company_list) or
             self._is_valid_guest(request))
        )


class IsCompanyListInvitedUser(permissions.BasePermission):
    """
    Determine if it's an authenticated user invited to the given CompanyList
    """

    def _is_user_invited(self, request, company_list):
        is_authenticated = request.user and request.user.is_authenticated
        return company_list.invited_users.filter(user=request.user).exists() if is_authenticated else False

    def has_object_permission(self, request, view, company_list):
        return self._is_user_invited(request, company_list)
