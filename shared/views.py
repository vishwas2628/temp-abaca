import os
import json
import bugsnag
import datetime
import http.client


from django.db import connection
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate
from django.core.management import call_command
from rest_framework.authtoken.models import Token

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import (
    IsAdminUser,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from shared.models.consent import Consent


from shared.serializers import SupportSuggestionSerializer
from shared.mailjet.mailjet import requestContactExclusion
from viral.models import UserProfile
from viral.utils import (
    confirm_admin_login_session,
    validate_admin_token,
    get_usable_admin_token,
)

from .Typesense import Typesense


class InitTestingDatabaseView(APIView):
    """
    View to initialize mock database.
    It runs the setup and stores a savepoint.
    """

    def get(self, request, format=None):
        try:
            # 1. Setup mock database
            call_command('database_savepoint', action='setup', verbosity=1)
            # 2. Store database savepoint
            call_command('database_savepoint', action='store', verbosity=1)
            return Response(status=status.HTTP_200_OK)
        except Exception as error:
            print('\r')
            print(error)
            bugsnag.notify(error)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResetTestingDatabaseView(APIView):
    """
    View to restore database from savepoint.
    By default it only restores the public schema.

    Optional query parameters:
    * tests/database/reset/?matching : Restore matching schema
    """

    def get(self, request, format=None):
        try:
            with_matching = 'matching' in self.request.query_params
            call_command(
                'database_savepoint',
                action='restore',
                matching=with_matching,
                verbosity=1,
            )
            return Response(status=status.HTTP_200_OK)
        except Exception as error:
            print('\r')
            print(error)
            bugsnag.notify(error)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MailjetUnsubView(APIView):
    """
    View that gets called by Mailjet webhook
    (defined on the account settings) that gets
    triggered when a user unsubscribes a campaign

    TEMP: Gets called on: /weekly/unsubscribe
    """

    def _set_request_failure(self, message, info={}):
        bugsnag.notify(Exception('Mailjet: {}.'.format(message)), meta_data=info)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, format=None):
        webhook_data = {}

        # Mailjet unsubscribe webhook currently returns
        # a list with a single object
        if isinstance(request.data, list):
            webhook_data = request.data[0]
        elif isinstance(request.data, dict):
            webhook_data = request.data

        email = webhook_data.get('email', None)
        event = webhook_data.get('event', None)
        is_unsub_event = event and event == 'unsub'

        # TEMP: While Mailjet unsubscribe doesn't work
        uid = webhook_data.get('uid', None)
        is_mailjet_campaign = 'mj_campaign_id' in webhook_data
        if uid:
            is_unsub_event = UserProfile.objects.filter(
                company__uid=uid, user__email=email
            ).exists()
        elif not is_mailjet_campaign:
            return self._set_request_failure(
                'received invalid data', {'context': {'data': webhook_data, 'uid': uid}}
            )

        if email and is_unsub_event:
            result = requestContactExclusion(email)

            if result and result.status_code in [200, 304]:
                return Response(status=status.HTTP_200_OK)
            else:
                return self._set_request_failure(
                    'could not unsubscribe user',
                    {'context': {'data': webhook_data, 'result': result}},
                )
        else:
            return self._set_request_failure('missing data')


class AdminValidateSessionView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        return validate_admin_token(request.user)


class AdminConfirmSessionView(generics.GenericAPIView):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, *args, **kwargs):
        session = confirm_admin_login_session(kwargs['hash'])

        if not session:
            return Response(status=status.HTTP_403_FORBIDDEN)

        return Response(session, status=status.HTTP_200_OK)


class AdminLoginAsUserView(APIView):
    """
    Admin view to login on the Abaca webapp as a certain user.
    """

    def get(self, request, company_id, format=None):
        try:
            user_profile = UserProfile.objects.get(company__pk=company_id)
            admin_token = get_usable_admin_token(user_profile.user)
            new_session_url = 'https://' + os.getenv('APP_BASE_URL', 'my.abaca.app')
            new_session_url += '/auth/admin/%s' % user_profile.company.access_hash
            return HttpResponseRedirect(redirect_to=new_session_url)
        except Exception as error:
            bugsnag.notify(Exception('Admin Login as User failed'), meta_data=error)
            return Response(status=status.HTTP_400_BAD_REQUEST)


class SupportSuggestionView(generics.GenericAPIView):
    """
    View that sends an email to the Admin with a user suggestion.
    """

    serializer_class = SupportSuggestionSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.submit(validated_data=serializer.validated_data)
        return Response(status=status.HTTP_201_CREATED)


class ConsentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if (type := request.query_params.get('type')) not in dict(
            Consent.CONSENT_TYPE_CHOICES
        ):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        return Response(
            Consent.objects.filter(user=request.user, consent_type=type).exists()
        )

    def post(self, request):
        if (type := request.data.get('type')) not in dict(Consent.CONSENT_TYPE_CHOICES):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        Consent.objects.update_or_create(user=request.user, consent_type=type)

        return Response(status=status.HTTP_200_OK)


class AdminTokenView(APIView):
    def post(self, request, *args, **kwargs):
        user = authenticate(
            username=request.data['username'], password=request.data['password']
        )
        if user is None:
            return Response('invalid credentials')

        token, created = Token.objects.get_or_create(user=user)
        return Response(token.key)


class AdminTypesenseView(APIView):
    # permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        typesense = Typesense()
        data = typesense.seed()
        return Response(data)
