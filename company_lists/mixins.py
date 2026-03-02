from rest_framework.response import Response
from rest_framework import status

from viral.models import UserGuest
from company_lists.models import CompanyList


class CompanyListsPermissionsMixin:
    """
    Base class to enforce company list access permissions.
    """

    def _is_guest(self, request):
        if not hasattr(self, 'guest'):
            try:
                guest_email = request.query_params.get('email', None) if hasattr(request, 'query_params') else None
                self.guest = UserGuest.objects.get(email__iexact=guest_email)
            except (UserGuest.DoesNotExist):
                self.guest = None

        return bool(self.guest)

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
                return Response({'error': 'passcode_updated'}, status=status.HTTP_400_BAD_REQUEST)
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        return True

    def _add_guest_to_invited(self, company_list, guest_email):
        in_invited_guests = company_list.invited_guests.filter(email__iexact=guest_email).exists()

        if not in_invited_guests:
            user_guest = UserGuest.objects.get(email__iexact=guest_email)
            company_list.invited_guests.add(user_guest)
