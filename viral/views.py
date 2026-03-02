import os
import re
import time
import bugsnag
import chargebee

from datetime import datetime

from django.db.models import Q, Count
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
from rest_framework.exceptions import ParseError

from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
    IsAdminUser,
)
from rest_framework.decorators import api_view
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from allauth.account import app_settings as allauth_settings
from allauth.account.utils import complete_signup

from rest_auth.registration.views import RegisterView, LoginView
from rest_auth.app_settings import create_token, TokenSerializer
from rest_auth.models import TokenModel
from rest_framework import filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from urllib.parse import urlencode
from company_lists.permissions import IsCompanyListOwnerOrReadOnly
from matching.models.answer import Answer
from matching.models.interested_cta import InterestedCTA

from viral.permissions import IsGuest
from viral.models import (
    Affiliate as AffiliateModel,
    Sector,
    UserProfile,
    Company,
    UserMetadata,
    TeamMember,
    Subscription,
    AdminTokens,
    AffiliateProgramEntry,
    AffiliateProgramSupporterSubmission,
    LocationGroup,
    AffiliateSubmissionDraft,
)
from viral.serializers import *
from viral.serializers import TeamMemberSerializer
from grid.serializers import AssessmentSerializer
from grid.models import Category
from watson import search as watson
from viral.utils import (
    build_login_user,
    validate_loginas_admin,
    search_google_places,
    rewrite_affiliate_spreadsheet,
)
from viral.signals import finished_affiliate_flow
from viral.mixins.affiliate_submission_in_company_lists_mixin import (
    AffiliateSubmissionInCompanyListsMixin,
)
from shared.mailjet import sendSuccessCreatingAccount
from shared.mixins import AuthUserThroughAdminMixin
from shared.utils import format_demographic_response_value, get_uri_scheme

from matching.models import SupporterInterestSector, Response as MatchingResponse
from matching.algorithm_supporters import getSupporterMatchByCompany
from matching.permissions import IsSupporter
from matching.serializers import (
    AffiliateSupporterProgramSubmissionSerializer,
    AffiliateSupporterProgramSerializer,
    QuestionBundleResponseSerializer,
)

from gspread.exceptions import APIError as GSpreadAPIError

from matching.tests.schemas.response_value_schema import response_value
from jsonschema.validators import validate
from jsonschema.exceptions import ValidationError as JSONValidationError

from company_lists.models import CompanyList


@api_view()
def django_rest_auth_null():
    return Response(status=status.HTTP_400_BAD_REQUEST)


class AffiliateList(generics.ListAPIView):
    """
    Lists all Affiliates (without including Question Bundles)
    """

    queryset = Affiliate.objects.all()
    serializer_class = AffiliateSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)


class Affiliate(generics.RetrieveAPIView):
    """
    Retrieves an Affiliate (without including Question Bundles)
    """

    queryset = AffiliateModel.objects.all()
    serializer_class = AffiliateSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    lookup_fields = ['slug__iexact', 'pk']

    def get(self, request, *args, **kwargs):
        self.lookup_field = next(
            (
                field
                for field in self.lookup_fields
                if field in kwargs and bool(kwargs[field])
            )
        )

        instance = self.get_object()

        serializer = AffiliateSerializer(instance)
        return Response(serializer.data)


class AffiliateQuestionBundles(generics.RetrieveAPIView):
    """
    Retrieves a Question Bundle from an Affiliate
    """

    queryset = AffiliateModel.objects.prefetch_related(
        'question_bundles__questions__question_type',
        'question_bundles__questions__question_category',
        'question_bundles__questions__answer_set',
    ).all()
    serializer_class = AffiliateQuestionBundleSerializer

    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = AffiliateQuestionBundleSerializer(
            instance.question_bundles.all(), many=True
        )
        return Response(serializer.data)


class AffiliateSupporterDefault(generics.GenericAPIView):
    """
    Retrieves the default Affiliate for Supporters.
    """

    queryset = AffiliateModel.objects.filter(
        flow_target=Company.SUPPORTER, default_flow=True
    )
    serializer_class = AffiliateWithQuestionBundleSerializer

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.prefetch_related(
            'networks',
            'networks__locations',
            'question_bundles',
            'question_bundles__questions',
            'question_bundles__questions__answer_set',
            'question_bundles__questions__question_type',
            'question_bundles__questions__question_category',
        )
        instance = get_object_or_404(queryset)
        self.check_object_permissions(self.request, instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class AffiliateSupporterView(generics.RetrieveAPIView):
    """
    Retrieves an Affiliate for Supporters.
    """

    queryset = AffiliateModel.objects.filter(flow_type=AffiliateModel.PROGRAM)
    lookup_fields = ['slug__iexact', 'pk']

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.prefetch_related(
            'networks',
            'question_bundles',
            'question_bundles__questions',
            'question_bundles__questions__answer_set',
            'question_bundles__questions__question_type',
            'question_bundles__questions__question_category',
        )

    def get(self, request, *args, **kwargs):
        self.lookup_field = next(
            (
                field
                for field in self.lookup_fields
                if field in kwargs and bool(kwargs[field])
            )
        )

        instance = self.get_object()

        if instance.flow_target != Company.SUPPORTER:
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = AffiliateWithQuestionBundleSerializer(instance)
        return Response(serializer.data)


class AffiliateProgramEntryDetailView(
    AuthUserThroughAdminMixin, generics.RetrieveAPIView
):
    """
    Retrieves a specific program entry by UID
    """

    queryset = AffiliateProgramEntry.objects.all()
    serializer_class = AffiliateSubmissionSerializer
    lookup_field = 'uid'
    permission_classes = (IsAuthenticatedOrReadOnly,)


class AffiliateProgramEntryListView(AuthUserThroughAdminMixin, generics.ListAPIView):
    """
    Lists affiliate program entries for Supporters.

    Can be filtered by:
    1 - A submission's user profile UID: ?user_profile=uid
    2 - A submission's affiliate ID: ?affiliate=id
    """

    queryset = AffiliateProgramEntry.objects.all()
    serializer_class = AffiliateSubmissionsListSerializer
    permission_classes = (IsAuthenticated, IsSupporter)

    def get_queryset(self):
        queryset = super().get_queryset()

        """
        Optionally restrict the returned program entries to a given user profile UID,
        by filtering against a `user_profile` query parameter in the URL.
        """
        user_profile_uid = self.request.query_params.get('user_profile', None)
        if user_profile_uid is not None:
            queryset = queryset.filter(user_profile__uid=user_profile_uid)

        """
        Optionally restrict the returned program entries to a given affiliate ID.
        """
        affiliate_id = self.request.query_params.get('affiliate', None)
        if affiliate_id is not None:
            queryset = queryset.filter(affiliate__pk=affiliate_id)

        """
        Supporters only have access to submissions that have been sent to:
        a) An affiliate they are tagged on as a Supporter;
        b) An affiliate that tags a network which they are a member of;
        """
        try:
            supporter_company = Company.objects.prefetch_related('networks').get(
                company_profile__user=self.request.user
            )
            by_supporter_affiliates = Q(
                affiliate__supporters__user_profile__company=supporter_company
            ) | Q(affiliate__networks__in=supporter_company.networks.all())
            queryset = queryset.filter(by_supporter_affiliates)
        except Exception as e:
            pass

        return queryset.order_by('-created_at').distinct('created_at')


class VendorAffiliateSubmissions(generics.GenericAPIView):
    """
    Return custom submission list/item only for admins to be used by vendors
    TODO: Refactor duplicated logic taken from: submit_affiliate_webhook
    """

    permission_classes = (IsAdminUser,)
    queryset = AffiliateProgramEntry.objects.all()
    pagination_class = PageNumberPagination
    pagination_class.page_size = 10

    def _get_categories(self):
        if not hasattr(self, 'categories'):
            self.categories = Category.objects.all()
        return self.categories

    def _fetch_submission_assessments(self, submission):
        assessments = {}
        # Add Viral Level Assessment
        assessment = submission.assessment
        assessment_key = 'Venture Investment Level'
        viral_level = assessment.level.value if assessment else 0
        if assessment:
            categories = self._get_categories()
            assessments[assessment_key] = {'Level': viral_level}
            for value in assessment.data:
                level = value.get('level') or 0
                category = next(
                    (
                        category
                        for category in categories
                        if category.pk == value.get('category')
                    ),
                    None,
                )

                if level != None and category:
                    assessments[assessment_key][category.name] = level

        return assessments

    def _fetch_submission_questions(self, submission):
        questions = {}
        # Add Question Bundles responses
        responses = submission.responses.all()
        if responses.exists():
            for response in responses:
                question_key = response.question.slug or response.question.id
                question_type = response.question.question_type.type
                is_text_type = question_type == QuestionType.FREE_RESPONSE
                is_date_type = question_type == QuestionType.DATE
                is_numeric_type = question_type == QuestionType.NUMERIC

                if response.answers.exists():
                    questions[question_key] = list(
                        map(lambda answer: answer.value, response.answers.all())
                    )
                elif (
                    is_text_type
                    and 'text' in response.value
                    and len(response.value['text'])
                ):
                    questions[question_key] = response.value or {'text': ''}
                elif (
                    is_date_type
                    and 'date' in response.value
                    and len(response.value['date'])
                ):
                    questions[question_key] = response.value or {'date': ''}
                elif is_numeric_type:
                    value_type = next(
                        (
                            vtype
                            for vtype in ['value', 'min', 'max']
                            if vtype in response.value
                        ),
                        None,
                    )
                    questions[question_key] = (
                        response.value
                        if value_type and response.value[value_type]
                        else {value_type: 0}
                    )

        return questions

    def _fetch_submission_match_scores(self, company, affiliate):
        match_scores = []
        # Add match score for Supporters associated to the Affiliate flow
        if affiliate.supporters.exists():
            for supporter in affiliate.supporters.all():
                matching = getSupporterMatchByCompany(supporter, company)
                matching_score = matching['score'] if matching else 0
                match_scores.append(
                    {
                        'supporter_ID': supporter.id,
                        'supporter_name': supporter.name,
                        'match_score': matching_score,
                        'match_summary': '',
                    }
                )
        return match_scores

    def _fetch_submission(self, submission):
        company = submission.user_profile.company
        company_location = company.locations.values(
            'formatted_address',
            'latitude',
            'longitude',
            'city',
            'region',
            'region_abbreviation',
            'country',
            'continent',
        ).first()
        company_sectors = list(map(lambda sector: sector.name, company.sectors.all()))
        app_base_url = 'https://' + os.getenv('APP_BASE_URL', 'my.abaca.app')

        return {
            'submission_ID': submission.id,
            'submission_link': app_base_url + '/program/submission/' + submission.uid,
            'submitted_at': str(submission.created_at),
            'company_uid': company.uid,
            'Abaca_ID': company.id,
            'Abaca_profile': app_base_url + '/profile/v/' + company.access_hash,
            'company_name': company.name,
            'email': company.email,
            'website': company.website,
            'location': company_location,
            'sectors': company_sectors,
            'assessments': self._fetch_submission_assessments(submission),
            'questions': self._fetch_submission_questions(submission),
            'match_scores': self._fetch_submission_match_scores(
                company, submission.affiliate
            ),
        }

    def _get_submission(self, submission_id, affiliate_id):
        submission_data = {}

        try:
            submission = (
                AffiliateProgramEntry.objects.select_related(
                    'user_profile__company', 'assessment'
                )
                .prefetch_related(
                    'user_profile__company__locations',
                    'user_profile__company__sectors',
                    'affiliate__supporters',
                    'responses__answers',
                    'responses__question__question_type',
                )
                .get(pk=submission_id, affiliate=affiliate_id)
            )

            submission_data = {
                'affiliate_ID': submission.affiliate.id,
                **self._fetch_submission(submission),
            }

            return Response(submission_data, status=status.HTTP_200_OK)
        except Exception as error:
            bugsnag.notify(error)
            return Response(status=status.HTTP_404_NOT_FOUND)

    def _get_submissions_list(self, request, affiliate_id):
        submissions_list = {}
        affiliate_submissions = AffiliateProgramEntry.objects.filter(
            affiliate=affiliate_id
        ).order_by('created_at')

        if len(affiliate_submissions):
            affiliate = affiliate_submissions.first().affiliate
            affiliate_serializer = AffiliateSerializer(affiliate)
            submissions_list['affiliate'] = affiliate_serializer.data
            submissions_list['submissions'] = []

            paginated_submissions = self.paginate_queryset(affiliate_submissions)
            paginated_submissions_pks = [
                submission.pk for submission in paginated_submissions
            ]
            paginated_submissions_with_prefetch = (
                AffiliateProgramEntry.objects.filter(pk__in=paginated_submissions_pks)
                .select_related('user_profile__company', 'assessment')
                .prefetch_related(
                    'user_profile__company__locations',
                    'user_profile__company__sectors',
                    'affiliate__supporters',
                    'responses__answers',
                    'responses__question__question_type',
                )
                .order_by('created_at')
            )

            for submission in paginated_submissions_with_prefetch:
                data = self._fetch_submission(submission)
                submissions_list['submissions'].append(data)

            response = self.get_paginated_response(submissions_list['submissions'])
            response.data['affiliate'] = submissions_list['affiliate']
            return response
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def get(self, request, *args, **kwargs):
        affiliate_id = self.kwargs.get('affiliate_id', None)
        submission_id = self.kwargs.get('pk', None)

        if submission_id and affiliate_id:
            return self._get_submission(submission_id, affiliate_id)
        elif affiliate_id:
            return self._get_submissions_list(request, affiliate_id)

        return Response(status=status.HTTP_400_BAD_REQUEST)


class SectorList(generics.ListAPIView):
    serializer_class = SectorWithGroupsSerializer
    lookup_field = 'filter'

    def get_queryset(self):
        if 'filter' in self.request.query_params:
            query = self.request.query_params.get('filter')
            if query:
                return watson.filter(Sector, query)
            else:
                return None
        return Sector.objects.all()


class SectorGroupsList(generics.ListAPIView):
    serializer_class = GroupSerializer
    queryset = Group.objects.all()


class SectorGroupsListPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'per_page'


class SectorGroupsListWithSectors(generics.ListAPIView):
    serializer_class = GroupWithSectorsSerializer
    pagination_class = SectorGroupsListPagination

    def get_serializer_context(self):
        context = super().get_serializer_context()
        needle = self.request.query_params.get('filter', None)
        if needle:
            context['filtered_sectors'] = watson.filter(Sector, needle)
        return context

    def _fetch_most_selected_sectors(self):
        most_selected_sectors = (
            SupporterInterestSector.objects.values('sector__id', 'sector__groups')
            .annotate(num_selections=Count('sector__id'))
            .order_by('-num_selections')
            .values_list('sector__groups', flat=True)
        )
        most_selected_sectors = list(dict.fromkeys(most_selected_sectors))
        sector_groups = list(Group.objects.all())
        results = []

        # Order sector groups by most selected sectors
        for group_id in most_selected_sectors:
            group = next(
                (group for group in sector_groups if group.id == group_id), None
            )
            if group:
                results.append(group)

        return results

    def get_queryset(self):
        if 'filter' in self.request.query_params:
            needle = self.request.query_params.get('filter')
            if needle:
                filters = Q()

                filtered_groups = watson.filter(Group, needle)
                if len(filtered_groups):
                    filters &= Q(pk__in=filtered_groups)

                filtered_sectors = watson.filter(Sector, needle)
                if len(filtered_sectors):
                    filters &= Q(sectors__in=list(filtered_sectors))

                if len(filters):
                    return Group.objects.filter(filters).order_by('id').distinct('id')

                # Fallback search when watson does not have results
                return (
                    Group.objects.filter(name__icontains=needle)
                    .order_by('id')
                    .distinct('id')
                )

        return self._fetch_most_selected_sectors()


class LocationSearch(generics.ListAPIView):
    serializer_class = LocationSearchSerializer
    lookup_field = 'filter'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        needle = self.request.query_params.get('filter', '')
        if len(needle) > 1:
            context['filtered_locations'] = (
                Location.objects.filter(formatted_address__icontains=needle)
                .order_by('id')
                .distinct('id')
            )
        return context

    def get(self, request, *args, **kwargs):
        if 'filter' in self.request.query_params:
            needle = self.request.query_params.get('filter', '')
            if len(needle) > 1:
                group_filters = Q(name__icontains=needle) | Q(
                    locations__formatted_address__icontains=needle
                )
                group_results = (
                    LocationGroup.objects.filter(group_filters)
                    .order_by('id')
                    .distinct('id')
                )
                google_results = search_google_places(needle, only_types=['geocode'])

                serializer = self.get_serializer(
                    {'grouped_locations': group_results, 'locations': google_results}
                )
                return Response(serializer.data)

        return Response(status=status.HTTP_404_NOT_FOUND)


class SelfAssessmentRegisterView(generics.CreateAPIView):
    serializer_class = SelfAssessmentRegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = serializer.create(validated_data=serializer.validated_data)
        return Response(response, status=status.HTTP_201_CREATED)


class UserRegistrationWithAssessmentView(RegisterView):
    serializer_class = UserRegisterWithAssessmentSerializer

    def get_response_data(self, user):
        return TokenSerializer(user.auth_token).data

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.perform_create(serializer)
        return Response(self.get_response_data(user), status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        user = serializer.save(self.request)
        create_token(self.token_model, user, serializer)
        complete_signup(
            self.request._request, user, allauth_settings.EMAIL_VERIFICATION, None
        )
        return user


class RegisterUserView(RegisterView):
    serializer_class = RegisterUserSerializer

    def get_response_data(self, user):
        return TokenSerializer(user.auth_token).data

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.perform_create(serializer)
        return Response(self.get_response_data(user), status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        user = serializer.save(self.request)
        create_token(self.token_model, user, serializer)
        complete_signup(
            self.request._request, user, allauth_settings.EMAIL_VERIFICATION, None
        )
        return user


class UpdateEmail(generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UpdateEmailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success', True})


class ResendEmailVerification(generics.CreateAPIView):
    """
    View to resend a verification email.

    Attention: This view must always return success in order
    to don't leak if the email exists on the database or not.
    """

    serializer_class = ResendEmailVerificationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({'success': True})


class ConfirmEmail(generics.RetrieveAPIView):
    def get(self, request, *args, **kwargs):
        key = kwargs['key']
        email_confirmation = EmailConfirmationHMAC.from_key(key)
        if email_confirmation == None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        email_confirmation.confirm(request)
        user = get_user_model().objects.get(
            email__iexact=email_confirmation.email_address.email
        )

        if settings.CHARGEBEE and user.userprofile.company.type == Company.SUPPORTER:
            # Update Company details in Chargebee
            try:
                subscription = Subscription.objects.get(user=user)
                subscription.update_company_details()
            except Subscription.DoesNotExist:
                pass

        sendSuccessCreatingAccount(email_confirmation.email_address.email, user)
        return build_login_user(user)


class ChangePassword(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ChangePasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success', True})


class CompanyView(generics.RetrieveUpdateAPIView):
    multiple_lookup_fields = ['pk', 'access_hash']
    permission_classes = (IsAuthenticatedOrReadOnly,)
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

    def get_object(self):
        queryset = self.get_queryset()
        filter = {}
        for field in self.multiple_lookup_fields:
            if self.kwargs[field]:
                filter[field] = self.kwargs[field]

        obj = get_object_or_404(queryset, **filter)
        self.check_object_permissions(self.request, obj)
        return obj

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.is_authenticated:
            serializer = CompanySerializer(instance)
        else:
            serializer = PartialCompanySerializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            if request.user.has_perm('viral.edit_any_company'):
                UserProfile.objects.get(company=instance)
            else:
                UserProfile.objects.get(user=request.user, company=instance)
        except:
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = UpdateCompanySerializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            if request.user.has_perm('viral.edit_any_company'):
                UserProfile.objects.get(company=instance)
            else:
                UserProfile.objects.get(user=request.user, company=instance)
        except:
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = UpdateCompanySerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CompanySearchPagination(PageNumberPagination):
    page_size = 30


class CompanySearchView(generics.ListAPIView):
    """
    Search for companies of the same type as the request user,
    or a specific type if specified in a query param
    """

    lookup_field = 'filter'
    serializer_class = CompanySearchSerializer
    permission_classes = (IsAuthenticated,)

    pagination_class = CompanySearchPagination

    def get_queryset(self):
        try:
            # Get the company of the authenticated user
            request_company = Company.objects.get(
                company_profile__user=self.request.user
            )

            # Get the type of company to search for (if not specified
            # in a query param, use the type of the request user company)
            try:
                company_type = int(
                    self.request.query_params.get('company_type', request_company.type)
                )
            except ValueError:
                raise ValidationError(detail='Invalid company type')

            companies = (
                Company.objects.prefetch_related('company_profile__user')
                .filter(type=company_type)
                .exclude(company_profile=None)
            )
            query = self.request.query_params.get('filter')
            results = []

            # Prevent empty searches
            if not query:
                return results

            results = watson.filter(companies, query)

            # Fallback search when watson does not have results
            if not len(results):
                results = companies.filter(name__icontains=query)

            return results
        except Company.DoesNotExist:
            return []


class CompanyAssessmentsView(generics.RetrieveAPIView):
    queryset = Company.objects.all()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        assessments = Assessment.objects.filter(evaluated=instance.id).order_by(
            '-created_at'
        )

        serializer = AssessmentSerializer(assessments, many=True)

        return Response(serializer.data)


class RecoverUser(generics.GenericAPIView):
    serializer_class = RecoverUserSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success', True})


class RetrieveUserFromKey(generics.GenericAPIView):
    serializer_class = RetrieveUserFromKeySerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['key'] = self.kwargs['key']
        return context

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = serializer.retrieve(serializer.validated_data)
        return Response(response)


class SendResetPasswordEmailView(generics.CreateAPIView):
    serializer_class = SendResetPasswordEmailSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success', True})


class ResetPasswordView(generics.CreateAPIView):
    serializer_class = ResetPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success', True})


class VerifyResetPasswordView(generics.CreateAPIView):
    serializer_class = VerifyResetPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success', True})


class ValidateSessionView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        request_token = request.META.get('HTTP_AUTHORIZATION')

        try:
            AdminTokens.objects.get(key=request_token[6:])
            return validate_loginas_admin(request.user)
        except AdminTokens.DoesNotExist:
            return build_login_user(request.user)


class CustomLoginView(LoginView):
    def get_response(self):
        response = super().get_response()

        try:
            user_profile = UserProfile.objects.get(user=self.user)
            email_address_verified = EmailAddress.objects.filter(
                email__iexact=self.user.email, verified=True
            ).exists()
            response.data['user_profile_id'] = user_profile.id
            response.data['verified_account'] = email_address_verified
            response.data['user'] = {'email': self.user.email}
        except UserProfile.DoesNotExist:
            response = Response(
                {'error': _('Profile not found'), 'code': 'profile_not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return response


class RetrieveUserProfileView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()


class ListUserProfilesView(generics.ListAPIView):
    # permission_classes = (IsAuthenticated,)
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ['=company__uid']


class UserMetadataListView(generics.ListCreateAPIView):
    """
    View to handle metadata requests for the logged user.
    """

    permission_classes = (IsAuthenticatedOrReadOnly,)
    queryset = UserMetadata.objects.all()
    serializer_class = UserMetadataSerializer

    def get_user_profile(self, request):
        user = request.user
        user_profile = UserProfile.objects.get(user=user)
        return user_profile

    def filter_queryset(self, queryset):
        """
        Filter the list of metadata only for the logged user
        """
        user_profile = self.get_user_profile(self.request)
        return self.get_queryset().filter(user_profile=user_profile)

    def post(self, request, *args, **kwargs):
        user_profile = self.get_user_profile(request)
        request.data['user_profile'] = user_profile.id

        return self.create(request, args, kwargs)


class SupportersLevelRange(generics.CreateAPIView):
    """
    Receive a custom viral level range and email, then send it all via email to the owner.
    """

    serializer_class = SupportersLevelRangeSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success', True})


class NetworkList(generics.ListAPIView):
    queryset = Network.objects.all()
    serializer_class = NetworkSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (filters.SearchFilter,)

    search_fields = (
        'name',
        'slug',
        'locations__formatted_address',
        'locations__city',
        'locations__region',
        'locations__country',
        'locations__continent',
    )


class NetworkMembersView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        network_id = pk

        try:
            data = []
            network_members = Network.objects.get(id=network_id).company_set.all()

            for member in network_members:
                user = member.company_profile.user

                data.append(
                    {
                        'id': member.id,
                        'name': member.name,
                        'about': member.about,
                        'type': Company.USER_TYPE[member.type][1],
                        'company_website': member.website,
                        'company_email': member.email,
                        'user_email': user.email,
                        'profile': f'https://{os.getenv("APP_BASE_URL", "my.abaca.app")}/profile/v/{member.access_hash}',
                        'uid': member.uid,
                        'locations': member.locations.values(
                            'formatted_address',
                            'latitude',
                            'longitude',
                            'city',
                            'region',
                            'region_abbreviation',
                            'country',
                            'continent',
                        ).first(),
                    }
                )

            return Response(data)
        except Network.DoesNotExist:
            return Response(
                {'error': 'Network not found'}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class NetworkMetricsView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        network_id = pk

        try:
            network_members = Network.objects.get(id=network_id).company_set
            entrepreneurs = network_members.filter(
                type=Company.ENTREPRENEUR
            ).values_list('id', flat=True)
            supporters = network_members.filter(type=Company.SUPPORTER).values_list(
                'id', flat=True
            )
            connections_queryset = InterestedCTA.objects.filter(
                supporter__in=list(supporters), entrepreneur__in=list(entrepreneurs)
            )
            mutual_connections = connections_queryset.filter(
                state_of_interest=InterestedCTA.CONNECTED
            )
            connection_requests = connections_queryset.filter(
                state_of_interest=InterestedCTA.INTERESTED
            )

            data = {
                'total_members': network_members.count(),
                'entrepeneurs': entrepreneurs.count(),
                'supporters': supporters.count(),
                'connection_requests': connection_requests.count(),
                'mutual_connections': mutual_connections.count(),
            }

            return Response(data)
        except Network.DoesNotExist:
            return Response(
                {'error': 'Network not found'}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PrimaryRegisterView(generics.CreateAPIView):
    """
    Receive a user without password, the company information, affiliate, group
    and set an initial state of the assessment with all the values null
    """

    serializer_class = PrimaryRegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.create(validated_data=serializer.validated_data)
        if not hasattr(user, 'auth_token'):
            create_token(TokenModel, user, serializer)
        response = {'auth_token': user.auth_token.key, 'email': user.email}
        return Response(response, status=status.HTTP_201_CREATED)


class PendingUserUpdateView(generics.UpdateAPIView):
    """
    Receive a user without password, update existing data
    and set an initial state of the assessment with all the values null
    """

    serializer_class = PendingUserUpdateSerializer

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.update(validated_data=serializer.validated_data)
        if not hasattr(user, 'auth_token'):
            create_token(TokenModel, user, serializer)
        response = {'auth_token': user.auth_token.key, 'email': user.email}
        return Response(response, status=status.HTTP_200_OK)


class PendingUserSelfAssessmentRegisterView(generics.CreateAPIView):
    """
    Receive the email of the user and set an initial state
    of the assessment
    """

    serializer_class = PendingUserSelfAssessmentSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = serializer.save()
        return Response(response, status=status.HTTP_201_CREATED)


class PendingUserCreatePasswordView(generics.GenericAPIView):
    serializer_class = PendingUserCreatePasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = serializer.save()
        return Response(response, status=status.HTTP_201_CREATED)


class VendorRegisterView(generics.CreateAPIView):
    serializer_class = VendorRegisterSerializer

    @csrf_exempt
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer_data = serializer.create(validated_data=serializer.validated_data)

        redirect_url = get_uri_scheme() + os.getenv('APP_BASE_URL', 'my.abaca.app')
        redirect_url += serializer_data['path']

        if 'params' in serializer_data:
            redirect_url += '?' + urlencode(serializer_data['params'])

        return HttpResponseRedirect(redirect_to=redirect_url)


class PendingUserProgramAssessmentRegisterView(generics.CreateAPIView):
    """
    Receive the email of the user and set an initial state
    of the assessment
    """

    serializer_class = PendingUserAssessmentProgramSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = serializer.save()
        return Response(response, status=status.HTTP_201_CREATED)


class PendingUserQuestionBundlesRegisterView(generics.CreateAPIView):
    """
    Receive the email of the user and store his responses
    """

    serializer_class = PendingUserQuestionBundlesProgramSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED)


class PendingUserFinishedProgramView(AffiliateSubmissionInCompanyListsMixin, APIView):
    """
    View to trigger a finished Affiliate program
    """

    def get(self, request, *args, **kwargs):
        request_email = request.query_params.get('email', None)

        try:
            user = get_user_model().objects.get(email__iexact=request_email)
            user_profile = UserProfile.objects.get(user=user)
            affiliate = user_profile.source
            program_entry = (
                AffiliateProgramEntry.objects.filter(
                    user_profile__user__email__iexact=request_email, affiliate=affiliate
                )
                .order_by('-created_at')
                .first()
            )

            if (
                program_entry
                and not user.has_usable_password()
                and affiliate.flow_type == AffiliateModel.PROGRAM
            ):
                # TODO: Drop signal usage in favor of mixins
                finished_affiliate_flow.send(
                    sender=self.__class__,
                    user_profile=user_profile,
                    affiliate=affiliate,
                    entrepreneur_company=user_profile.company,
                    program_entry=program_entry,
                )
                self.populate_affiliate_company_lists(affiliate, user_profile.company)
        except (
            get_user_model().DoesNotExist,
            UserProfile.DoesNotExist,
            AffiliateProgramEntry.DoesNotExist,
        ):
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_200_OK)


class ProgramAssessmentRegisterView(generics.CreateAPIView):
    serializer_class = ProgramAssessmentSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED)


class ProgramQuestionBundlesRegisterView(generics.CreateAPIView):
    serializer_class = ProgramQuestionBundlesSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED)


class VendorEntrepreneursListView(generics.ListAPIView):
    """
    Return custom entrepreneurs list only for admins to be used by vendors

    TODO: The vendor endpoints have a few uniformity issues which do not
    follow the naming convention that we use for the schema keys: Snake Case
    For the sake of scalability and maintainability, in the future we should not
    allow stakeholders to propose non-standard structures and naming conventions.
    """

    permission_classes = (IsAdminUser,)
    queryset = UserProfile.objects.prefetch_related(
        'company', 'company__locations', 'company__sectors', 'user'
    ).filter(company__type=Company.ENTREPRENEUR)
    serializer_class = VendorEntrepreneurSerializer
    pagination_class = PageNumberPagination
    pagination_class.page_size = 50

    def get_queryset(self):
        queryset = super().get_queryset()
        filters = {}

        date_filters = {
            'created_since': 'company__created_at__gte',
            'created_until': 'company__created_at__lte',
        }
        for param, field in date_filters.items():
            query_value = self.request.query_params.get(param, None)

            if query_value:
                try:
                    date = datetime.strptime(query_value, '%Y-%m-%d').date()
                    filters[field] = date
                except Exception as error:
                    bugsnag.notify(error)

        location_filters = ('country', 'city', 'region')
        for loc_filter in location_filters:
            query_value = self.request.query_params.get(loc_filter, None)
            query_key = 'company__locations__%s' % (loc_filter)

            if query_value:
                filters[query_key] = query_value

        return queryset.filter(**filters)


class VendorSupportersListView(generics.ListAPIView):
    """
    Return custom supporters list only for admins to be used by vendors
    """

    permission_classes = (IsAdminUser,)
    queryset = UserProfile.objects.prefetch_related(
        'company', 'company__locations', 'company__sectors', 'user', 'supporter'
    ).filter(company__type=Company.SUPPORTER)
    serializer_class = VendorSupporterSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        filters = {}

        date_filters = {
            'created_since': 'company__created_at__gte',
            'created_until': 'company__created_at__lte',
        }
        for param, field in date_filters.items():
            query_value = self.request.query_params.get(param, None)

            if query_value:
                try:
                    date = datetime.strptime(query_value, '%Y-%m-%d').date()
                    filters[field] = date
                except Exception as error:
                    bugsnag.notify(error)

        location_params = ('country', 'city', 'region')
        for param in location_params:
            query_value = self.request.query_params.get(param, None)
            query_key = 'company__locations__%s' % (param)

            if query_value:
                filters[query_key] = query_value

        supporter_params = ('icountry', 'icity', 'iregion')
        for param in supporter_params:
            query_value = self.request.query_params.get(param, None)
            query_key = 'supporter__locations__%s' % (param[1:])

            if query_value:
                filters[query_key] = query_value

        return queryset.filter(**filters)


class CreateAffiliateSupporterProgramSubmissionView(generics.GenericAPIView):
    """
    Create submission of Affiliate Supporter programs.
    """

    serializer_class = AffiliateSupporterProgramSubmissionSerializer
    permission_classes = (IsAuthenticated, IsSupporter)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission = serializer.save(owner=request.user)
        return Response(submission, status=status.HTTP_201_CREATED)


class RetrieveAffiliateSupporterProgramSubmissionView(
    AuthUserThroughAdminMixin, generics.RetrieveAPIView
):
    """
    Retrieve a submission of an Affiliate Supporter program by UID.
    """

    queryset = AffiliateProgramSupporterSubmission.objects.all()
    serializer_class = AffiliateSupporterProgramSerializer
    lookup_field = 'uid'
    permission_classes = (IsAuthenticatedOrReadOnly,)


class UsersGuestView(generics.GenericAPIView):
    serializer_class = UserGuestSerializer
    permission_classes = (IsGuest,)

    def post(self, request, *args, **kwargs):
        """
        Create a new user guest, if the email already exists returns the existing record as a result.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RegenerateAffiliateSpreadsheetView(APIView):
    authentication_classes = (SessionAuthentication, TokenAuthentication)
    permission_classes = (IsAdminUser,)

    def post(self, request, *args, **kwargs):
        try:
            affiliate = AffiliateModel.objects.get(id=kwargs['pk'])
        except AffiliateModel.DoesNotExist:
            return HttpResponse(404)

        try:
            rewrite_affiliate_spreadsheet(affiliate)
            return HttpResponse(status=status.HTTP_200_OK)
        except GSpreadAPIError as exception:
            print(exception.response.json())
            return JsonResponse(
                exception.response.json(), status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as error:
            bugsnag.notify(
                Exception(
                    'An error occurred while regenerating an affiliate spreadsheet.'
                ),
                meta_data={'context': {'error': error}},
            )
            return HttpResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AffiliateSubmissionDraftListView(generics.ListCreateAPIView):
    serializer_class = AffiliateSubmissionDraftSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AffiliateSubmissionDraft.objects.filter(user=self.request.user).order_by(
            '-updated_at'
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        return super().perform_create(serializer)


class AffiliateSubmissionDraftView(generics.RetrieveAPIView):
    serializer_class = AffiliateSubmissionDraftSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AffiliateSubmissionDraft.objects.filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        self.lookup_url_kwarg = 'pk' if kwargs.get('pk') else 'slug__iexact'
        self.lookup_field = f'affiliate__{self.lookup_url_kwarg}'
        return super().get(request, *args, **kwargs)


class AffiliateSubmissionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        def get_submisions_info(submission):
            shared_info = [1]
            owners = []
            owners_ids = {}

            if submission.affiliate.flow_type == AffiliateModel.PROGRAM:
                shared_info.append(2)

            if submission.affiliate.show_team_section:
                shared_info.append(3)

            if submission.affiliate.company:
                owners.append(
                    {
                        'name': submission.affiliate.company.name,
                        'logo': submission.affiliate.company.logo.url
                        if submission.affiliate.company.logo
                        else None,
                        'id': submission.affiliate.company.id,
                    }
                )
                owners_ids[submission.affiliate.company.id] = True

            for supporter in submission.affiliate.supporters.all():
                if not supporter.user_profile.company.id in owners_ids:
                    owners.append(
                        {
                            'name': supporter.user_profile.company.name,
                            'logo': supporter.user_profile.company.logo.url
                            if supporter.user_profile.company.logo
                            else None,
                            'id': supporter.user_profile.company.id,
                        }
                    )

            # This should not be moved because the logo of the networks has already the complete url
            if os.environ.get('APP_ENV') == 'local':
                for element in owners:
                    if element['logo']:
                        element['logo'] = os.environ.get('API_DOMAIN') + element['logo']

            for network in submission.affiliate.networks.all():
                owners.append(
                    {
                        'name': network.name,
                        'logo': network.logo,
                    }
                )

            return {
                'affiliate': {
                    'name': submission.affiliate.name,
                    'id': submission.affiliate.id,
                },
                'owners': owners,
                'shared_info': shared_info,
                'last_update': submission.updated_at,
            }

        data = {'drafts': [], 'submitted': []}

        drafts = AffiliateSubmissionDraft.objects.filter(user=request.user).order_by(
            '-updated_at'
        )

        for draft in drafts:
            data['drafts'].append(get_submisions_info(draft))

        submissions = []

        if request.user.userprofile.company.type == Company.ENTREPRENEUR:
            submissions = AffiliateProgramEntry.objects.filter(
                user_profile=request.user.userprofile
            ).order_by('-updated_at')

        if request.user.userprofile.company.type == Company.SUPPORTER:
            submissions = AffiliateProgramSupporterSubmission.objects.filter(
                supporter__user_profile=request.user.userprofile
            ).order_by('-updated_at')

        for submission in submissions:
            data['submitted'].append(get_submisions_info(submission))
            data['submitted'][-1]['submission_uid'] = submission.uid

        return Response(data)

    def _is_valid(self, assessment_data, responses_data, team_members_data):
        if not any(
            [bool(category_level['level']) for category_level in assessment_data]
        ):
            return False

        for response in responses_data:
            if not self._is_valid_response(response, required=True):
                return False

        for team_member in team_members_data:
            if not all(
                [
                    team_member.get(field)
                    for field in ['first_name', 'last_name', 'email', 'position']
                ]
            ):
                return False
            if not re.match(
                r'^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$',
                team_member.get('email'),
            ):
                return False
            for response in team_member.get('responses', []):
                if not self._is_valid_response(response, required=False):
                    return False

        return True

    def _is_valid_response(self, response, required=True):
        if 'value' in response:
            if all(
                [
                    not required,
                    not response['value'].get('value'),
                    not response['value'].get('text'),
                    not response['value'].get('min'),
                    not response['value'].get('max'),
                ]
            ):
                return True
            try:
                validate(response['value'], schema=response_value)
                if 'min' in response['value'] and 'max' in response['value']:
                    if response['value']['min'] > response['value']['max']:
                        return False
                elif 'text' in response['value'] and not response['value']['text']:
                    return False
                return True
            except JSONValidationError:
                return False
        else:
            return bool(response.get('answers', [])) or not required

    def _save_assessment(self, assessment_data, affiliate, user):
        for category_level in assessment_data:
            category_level['level'] = category_level['level'] or None
        serializer = ViralLevelSerializer(data=assessment_data, many=True)
        serializer.is_valid()
        levels = serializer.validated_data
        level = calculate_viral_level(levels=levels)

        assessment, created = Assessment.objects.update_or_create(
            user=user.id,
            evaluated=user.userprofile.company.id,
            state=Assessment.BEGAN_STATE,
            defaults={
                'level': level,
                'data': assessment_data,
                'state': Assessment.REGISTERED_USER_STATE
                if user.has_usable_password()
                else Assessment.FINISHED_STATE,
            },
        )

        if not assessment.hash_token:
            assessment.hash_token = generate_hash(time.time())
            assessment.save()

        if bool(affiliate.spreadsheet) and not created:
            update_spreadsheet(
                affiliate,
                assessment.hash_token,
                scores=levels,
                viral_level=level.value,
                state=assessment.state,
            )
        else:
            save_assessment_to_spreadsheet(
                levels,
                user.userprofile.company,
                user.email,
                level.value,
                affiliate,
                assessment.hash_token,
                state=assessment.state,
            )

        return assessment

    def _save_responses(self, responses_data, user_profile):
        serializer = QuestionBundleResponseSerializer(data=responses_data, many=True)
        serializer.is_valid()
        responses = []
        for response_data in serializer.validated_data:
            response = MatchingResponse.objects.create(
                question=response_data['question'],
                user_profile=user_profile,
                value=response_data.get('value'),
            )
            response.answers.set(response_data.get('answers', []))
            responses.append(response)
        for response in responses:
            profile_field = response.question.profile_field
            has_profile_field_associated = profile_field != None
            if has_profile_field_associated:
                source_model = apps.get_model(
                    app_label=profile_field.app_label,
                    model_name=profile_field.model_name,
                )
                relation_to_profile = profile_field.user_profile_relation
                by_user_profile = {relation_to_profile: user_profile}
                try:
                    model_instance = source_model.objects.get(**by_user_profile)
                    question_type = response.question.question_type.type
                    if response.value:
                        if question_type == QuestionType.FREE_RESPONSE:
                            text_value = str(response.value.get('text', ''))
                            setattr(
                                model_instance, profile_field.field_name, text_value
                            )
                        elif question_type == QuestionType.DATE:
                            date_value = response.value.get('date', datetime.now())
                            date_value = datetime.strptime(
                                date_value, '%Y-%m-%d'
                            ).date()
                            setattr(
                                model_instance, profile_field.field_name, date_value
                            )
                    elif response.answers.exists():
                        setattr(
                            model_instance,
                            profile_field.field_name,
                            response.answers.all(),
                        )
                    model_instance.save()
                except Exception as e:
                    bugsnag.notify(
                        Exception('Could not sync profile field.'),
                        meta_data={'context': {'error': e}},
                    )
        return responses

    def _save_team_members(self, team_members_data, user_profile):
        TeamMember.objects.filter(company=user_profile.company).update(is_active=False)

        for team_member_index, team_member_data in enumerate(team_members_data):
            team_member, created = TeamMember.objects.update_or_create(
                id=team_member_data.get('id'),
                defaults={
                    'company': user_profile.company,
                    'first_name': team_member_data.get('first_name'),
                    'last_name': team_member_data.get('last_name'),
                    'email': team_member_data.get('email'),
                    'position': team_member_data.get('position'),
                    'is_active': True,
                },
            )

            for response_index, response_data in enumerate(
                team_member_data.get('responses', [])
            ):
                response = MatchingResponse.objects.create(
                    team_member=team_member,
                    user_profile=user_profile,
                    question_id=response_data.get('question'),
                    value=response_data.get('value'),
                )
                response.answers.set(response_data.get('answers', []))
                team_members_data[team_member_index]['responses'][response_index] = (
                    response.id
                )

    # Copied from the pre-existing PendingUserQuestionBundlesProgramSerializer
    def _update_profile_fields(self, responses, user_profile):
        for response in responses:
            profile_field = response.question.profile_field
            has_profile_field_associated = profile_field != None

            if has_profile_field_associated:
                source_model = apps.get_model(
                    app_label=profile_field.app_label,
                    model_name=profile_field.model_name,
                )
                relation_to_profile = profile_field.user_profile_relation
                by_user_profile = {relation_to_profile: user_profile}

                try:
                    # Find user's model instance
                    model_instance = source_model.objects.get(**by_user_profile)

                    # TEMP: For now, only text & date values are supported
                    question_type = response.question.question_type.type

                    if response.value:
                        if question_type == QuestionType.FREE_RESPONSE:
                            text_value = str(response.value.get('text', ''))
                            setattr(
                                model_instance, profile_field.field_name, text_value
                            )
                        elif question_type == QuestionType.DATE:
                            date_value = response.value.get('date', datetime.now())
                            date_value = datetime.strptime(
                                date_value, '%Y-%m-%d'
                            ).date()
                            setattr(
                                model_instance, profile_field.field_name, date_value
                            )
                    elif response.answers.exists():
                        setattr(
                            model_instance,
                            profile_field.field_name,
                            response.answers.all(),
                        )
                    model_instance.save()
                except Exception as e:
                    bugsnag.notify(
                        Exception('Could not sync profile field.'),
                        meta_data={'context': {'error': e}},
                    )

    # Copied from the pre-existing AffiliateSubmissionInCompanyListsMixin
    def _populate_affiliate_company_lists(
        self, affiliate: Affiliate, company: Company
    ) -> None:
        # Include:
        # - lists explicitly linked to this affiliate via `Affiliate.company_lists`
        # - the auto-created "Affiliate Submissions" smart list (`CompanyList.affiliate`)
        linked_lists = affiliate.company_lists.all()
        smart_list = CompanyList.objects.filter(
            company_list_type=CompanyList.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS,
            affiliate=affiliate,
        )

        candidate_lists = CompanyList.objects.filter(
            Q(pk__in=linked_lists.values("pk")) | Q(pk__in=smart_list.values("pk"))
        ).distinct()

        # NOTE: Avoid `exclude(companies__pk=...)` on an M2M: it can drop lists that have
        # zero companies due to INNER JOIN semantics. Using a pk-subquery preserves empty lists.
        company_lists_to_populate = candidate_lists.exclude(
            pk__in=candidate_lists.filter(companies__pk=company.pk).values("pk")
        )

        # Only (easy) way to bulk create/update m2m fields:
        through_model = CompanyList.companies.through
        through_model.objects.bulk_create(
            [
                through_model(companylist_id=pk, company_id=company.pk)
                for pk in company_lists_to_populate.values_list('pk', flat=True)
            ],
            ignore_conflicts=True,
        )

    def post(self, request, *args, **kwargs):
        try:
            draft = AffiliateSubmissionDraft.objects.get(
                user=request.user, id=request.data.get('draft_id')
            )
        except (ValidationError, AffiliateSubmissionDraft.DoesNotExist):
            return Response(status=status.HTTP_404_NOT_FOUND)

        affiliate = draft.affiliate
        user_profile = request.user.userprofile
        company = user_profile.company

        assessment_data = draft.data.get('assessment', [])
        responses_data = draft.data.get('responses', [])
        team_members_data = draft.data.get('teamMembers', [])
        responses = []

        if not self._is_valid(assessment_data, responses_data, team_members_data):
            return Response(
                {'errors': [_('Missing data.')]}, status=status.HTTP_400_BAD_REQUEST
            )

        assessment = self._save_assessment(assessment_data, affiliate, request.user)
        if affiliate.flow_type == affiliate.PROGRAM:
            responses = self._save_responses(responses_data, user_profile)
            self._update_profile_fields(responses, user_profile)
            if affiliate.show_team_section:
                # team_members_data is mutated by this function:
                # for each team member, the 'responses' field must be
                # converted into an array of Matching Response IDs
                self._save_team_members(team_members_data, user_profile)

        self._populate_affiliate_company_lists(affiliate, company)

        if user_profile.company.type == Company.ENTREPRENEUR:
            program_entry = AffiliateProgramEntry.objects.create(
                affiliate=affiliate,
                user_profile=user_profile,
                assessment=assessment,
                team_members=team_members_data,
            )
            program_entry.responses.set(responses)
            program_entry.save()

            add_affiliate_program_entry_to_google_sheet(program_entry)

            finished_affiliate_flow.send(
                sender=self.__class__,
                user_profile=user_profile,
                affiliate=affiliate,
                entrepreneur_company=company,
                program_entry=program_entry,
            )

        draft.delete()

        return Response(status=status.HTTP_201_CREATED)


class TeamMembersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        team_members = TeamMember.objects.filter(
            company__company_profile__user=request.user, is_active=True
        ).all()
        serializer = TeamMemberSerializer(team_members, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = TeamMemberSerializer(data=request.data, many=True)
        if serializer.is_valid():
            TeamMember.objects.filter(
                company=self.request.user.userprofile.company
            ).update(is_active=False)
            serializer.save(user_profile=self.request.user.userprofile)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FetchListDemographicCompositionView(APIView):
    permission_classes = [IsCompanyListOwnerOrReadOnly, IsAuthenticated, IsSupporter]
    needed_amount_of_responses = 5

    def get(self, request, *args, **kwargs):
        list_uid = self.request.query_params.get('list_uid', '')
        question = self.request.query_params.get('question', '')

        try:
            company_list = get_object_or_404(CompanyList, uid=list_uid)
            self.check_object_permissions(request, company_list)

            try:
                question = Question.objects.get(id=question)
            except (Question.DoesNotExist, ValueError):
                question = Question.objects.get(slug=question)

            answers = Answer.objects.filter(question=question).all()

        except (Question.DoesNotExist, Answer.DoesNotExist):
            return Response(status=status.HTTP_404_NOT_FOUND)

        data = {
            'question': question.resource_question,
            'companies': [],
            'responses': [
                {
                    'value': format_demographic_response_value(answer.value),
                    'count': 0,
                    'percentage': 0,
                }
                for answer in answers
            ],
            'companies_with_responses': 0,
        }

        # Initialize the count of Team Members with Responses
        total_number_of_team_members_with_responses = 0

        # Get the responses for each company
        for company in company_list.companies.all():
            responses = (
                MatchingResponse.objects.prefetch_related('answers')
                .filter(
                    team_member__is_active=True,
                    team_member__company=company,
                    question=question,
                )
                .distinct('team_member_id')
                .order_by('team_member_id', '-created_at')
            )

            responses = list(
                filter(lambda response: response.answers.count(), responses)
            )

            company_responses = []

            for response in responses:
                response_answers = response.answers.values_list('value', flat=True)

                for value in response_answers:
                    # Format the response value (remove "For example" and everything after it)
                    value = format_demographic_response_value(value)

                    # We increment, or initialize, the count of the Answer
                    if entry := next(
                        (
                            entry
                            for entry in company_responses
                            if entry['value'] == value
                        ),
                        None,
                    ):
                        entry['count'] += 1
                    else:
                        company_responses.append({'value': value, 'count': 1})

                    # Increment the count in the global answers list
                    if entry := next(
                        (
                            entry
                            for entry in data['responses']
                            if entry['value'] == value
                        ),
                        None,
                    ):
                        entry['count'] += 1

            # We calculate the percentage of each Answer for this Company.
            if len(responses):
                total_responses = len(responses)
                for item in company_responses:
                    item['percentage'] = item['count'] / total_responses

            data['companies'].append(
                {
                    'name': company.name,
                    'id': company.id,
                    'team_members_count': TeamMember.objects.filter(
                        company=company, is_active=True
                    ).count(),
                    'team_members_with_responses_count': len(responses),
                    'responses': company_responses,
                }
            )

            # Update the Companies with Responses and Team Members with Responses counters
            if len(responses):
                data['companies_with_responses'] += 1
                total_number_of_team_members_with_responses += len(responses)

        # If we don't have enough companies with responses (at least 5 companies), we don't want to show the responses
        if data['companies_with_responses'] < self.needed_amount_of_responses:
            for company in data['companies']:
                company['responses'] = []
            data['responses'] = []
        else:
            # We calculate the percentage of each Answer.
            for response in data['responses']:
                response['percentage'] = (
                    response['count'] / total_number_of_team_members_with_responses
                )

        return Response(data)


class SupporterOwnedAffiliatesSubmissionsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsSupporter]

    def get(self, request, *args, **kwargs):
        def get_submisions_info(submission, isDraft=False, isSupporterSubmission=False):
            shared_info = [1]

            if submission.affiliate.flow_type == AffiliateModel.PROGRAM:
                shared_info.append(2)

            if submission.affiliate.show_team_section:
                shared_info.append(3)

            if isDraft:
                owner_data = UserProfile.objects.get(user=submission.user).company
            elif isSupporterSubmission:
                owner_data = submission.supporter.user_profile.company
            else:
                owner_data = submission.user_profile.company

            return {
                'affiliate': {
                    'name': submission.affiliate.name,
                    'id': submission.affiliate.id,
                },
                'owners': [
                    {
                        'name': owner_data.name,
                        'logo': owner_data.logo.url if owner_data.logo else None,
                        'id': owner_data.id,
                        'email': owner_data.email,
                    }
                ],
                'shared_info': shared_info,
                'last_update': submission.updated_at,
                'company_type': owner_data.type,
            }

        data = {'drafts': [], 'submitted': []}

        """
        Supporters only have access to submissions that have been sent to:
        a) An affiliate they are tagged on as a Supporter;
        b) An affiliate that tags a network which they are a member of;
        """
        supporter_company = Company.objects.get(company_profile__user=self.request.user)
        by_supporter_affiliates = Q(
            affiliate__supporters__user_profile__company=supporter_company
        ) | Q(affiliate__networks__in=supporter_company.networks.all())
        entrepreneurs_submissions = AffiliateProgramEntry.objects.filter(
            by_supporter_affiliates
        ).order_by('-updated_at')
        supporters_submissions = AffiliateProgramSupporterSubmission.objects.filter(
            by_supporter_affiliates
        ).order_by('-updated_at')
        drafts = AffiliateSubmissionDraft.objects.filter(
            by_supporter_affiliates
        ).order_by('-updated_at')

        for draft in drafts:
            data['drafts'].append(get_submisions_info(draft, True))

        for submission in entrepreneurs_submissions:
            data['submitted'].append(get_submisions_info(submission))
            data['submitted'][-1]['submission_uid'] = submission.uid

        for submission in supporters_submissions:
            data['submitted'].append(get_submisions_info(submission, False, True))
            data['submitted'][-1]['submission_uid'] = submission.uid

        return Response(data)


class SubscriptionView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsSupporter]
    serializer_class = SubscriptionSerializer

    def get(self, request):
        try:
            subscription = Subscription.sync(request.user)
            return Response(self.get_serializer(subscription).data)
        except Exception:
            return Response(status=status.HTTP_404_NOT_FOUND)


class ChargebeePortalView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsSupporter]

    def get(self, request):
        try:
            subscription = Subscription.objects.get(user=request.user)
        except Subscription.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            portal_session = chargebee.PortalSession.create(
                {'customer': {'id': subscription.customer_id}}
            )._response['portal_session']
            return Response(portal_session)
        except chargebee.APIError as error:
            bugsnag.notify(error)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChargebeeCheckoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsSupporter]

    def get(self, request):
        try:
            subscription = Subscription.objects.get(user=request.user)
        except Subscription.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            checkout = chargebee.HostedPage.checkout_existing(
                {
                    'subscription': {
                        'id': subscription.subscription_id,
                        'plan_id': request.query_params.get('plan'),
                    },
                }
            )._response['hosted_page']
            return Response(checkout)
        except chargebee.APIError as error:
            bugsnag.notify(error)
            return Response(status=status.HTTP_400_BAD_REQUEST)
