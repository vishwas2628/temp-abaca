# TODO: Move all views into separated files once we have tests covering them all.
import datetime
import bugsnag

from allauth.account import app_settings as allauth_settings
from allauth.account.utils import complete_signup
from django.db import connection
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404
from rest_auth.app_settings import TokenSerializer, create_token
from rest_auth.registration.views import RegisterView
from rest_framework import generics, status, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response as ServerResponse
from rest_framework.authentication import SessionAuthentication, TokenAuthentication

from shared.mixins import AuthUserThroughAdminMixin
from grid.models import Assessment
from viral.models import Affiliate, Company, UserProfile
from viral.serializers import AffiliateSerializer
from viral.utils import build_login_user

from matching.algorithm import (getEntrepreneurInterestMatches,
                                getEntrepreneurMatchByCompany, getMatches)
from matching.algorithm_supporters import (getMatchesSupporter,
                                           getSupporterInterestMatches,
                                           getSupporterMatchByCompany)
from matching.models import (Criteria, CriteriaWeight, InterestedCTA, Question,
                             QuestionBundle, QuestionCategory, QuestionType,
                             Response, Supporter, SupporterOffering,
                             SupporterOfferingCategories,
                             SupporterOfferingTypes, SupporterType)
from matching.permissions import IsSupporter
from matching.serializers import (
    CreateSupporterSerializer, CriteriaWeightSerializer,
    FinishedPendingSupporterSerializer, InterestedCTASerializer,
    MatchingCreateOrUpdateCriteriaSerializer,
    MatchingCriteriaBySupporterSerializer,
    MatchingQuestionsForAdditionalCriteriaSerializer, MatchingScoresImpactSerializer, MatchingSerializer,
    MatchingSupportersAffiliateSerializer, MatchingSupportersSerializer,
    QuestionSerializer, RegisterPendingSupporterSerializer,
    ResponseSerializerSubmitData, SupporterCreateEntrepreneurLinkSerializer,
    SupporterOfferingCategoriesSerializer, SupporterOfferingCreatorSerializer,
    SupporterOfferingTypesSerializer, SupporterSerializer,
    SupporterTypeSerializer, UpdateSupporterOfferingSerializer,
    UpdateSupporterSerializer, QuestionBundleSerializer,
    AlgorithmCalculatorSearchCompaniesSerializer, AlgorithmCalculatorMatchingCriteriaSerializer)
from matching.utils import calculate_interest


class ResponseList(generics.ListCreateAPIView):
    """
    get:
    Lists the responses of the authenticated user.

    post:
    Create a response for the authenticated user.
    """
    queryset = Response.objects.all()
    serializer_class = ResponseSerializerSubmitData
    permission_classes = (IsAuthenticated,)

    # Filter list view by user profile
    def get_queryset(self):
        user_profile = UserProfile.objects.get(user=self.request.user)
        queryset = self.queryset
        queryset = queryset.filter(user_profile=user_profile)
        return queryset

    def create(self, request, *args, **kwargs):
        # Append user profile id to the request data
        user_profile_id = UserProfile.objects.get(user=request.user).id
        request.data["user_profile"] = user_profile_id

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return ServerResponse(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class LatestResponseList(generics.ListAPIView):
    """
    Lists the latest responses of the authenticated user.
    """
    queryset = Response.objects.all()
    serializer_class = ResponseSerializerSubmitData
    permission_classes = (IsAuthenticated,)

    # Filter list view by user profile and latest responses
    def get_queryset(self):
        user_profile = UserProfile.objects.get(user=self.request.user)
        queryset = self.queryset
        queryset = queryset.filter(user_profile=user_profile).order_by(
            'question_id', 'team_member_id', '-created_at').distinct('question_id', 'team_member_id')
        return queryset


class QuestionsPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = "per_page"


class QuestionsList(generics.ListAPIView):
    """
    This viewset is to retrive questions for the company.

    The retrived questions are based on the questions that aren't
    answers yet and also takes into account the expire date of
    the answer.
    """
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = (IsAuthenticated,)

    pagination_class = QuestionsPagination

    def list(self, request, *args, **kwargs):
        self._fetch_user_profile()
        self._exclude_questions_answered_recently()
        self._filter_questions_by_param()
        self._exclude_question_types_by_param()

        # Get filtered questions
        questions = self.filter_queryset(self.get_queryset())

        # Paginate the results
        page = self.paginate_queryset(questions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(questions, many=True)
        return ServerResponse(serializer.data, status=status.HTTP_200_OK)

    def _fetch_user_profile(self):
        try:
            self.user_profile = UserProfile.objects.get(user=self.request.user)
        except UserProfile.DoesNotExist:
            return ServerResponse(
                {'error': 'Profile not found', 'code': 'profile_not_found'},
                status=status.HTTP_404_NOT_FOUND)

    def _exclude_questions_answered_recently(self):
        # Get all responses made by the user without the outdated
        # responses to filter the list of questions
        now = datetime.datetime.now()

        responses_to_exclude = []
        if self.user_profile.company.type == Company.ENTREPRENEUR:
            responses = Response.objects.filter(
                user_profile=self.user_profile)
            responses_to_exclude = list(filter(
                lambda res: res.created_at + res.question.ttl > now, responses))
        elif self.user_profile.company.type == Company.SUPPORTER:
            supporter = get_object_or_404(
                Supporter, user_profile=self.user_profile)
            responses_to_exclude = list(filter(
                lambda res: res.created_at + res.question.ttl > now, supporter.get_criteria()))

        ids_to_exclude = map(lambda res: res.question.id, responses_to_exclude)
        self.queryset = self.queryset.exclude(id__in=list(ids_to_exclude))

    def _filter_questions_by_param(self):
        # Check if there's a "only" query param
        # to filter questions that target only "criteria" or "profile"
        only_param = self.request.query_params.get('only', None)
        available_filters = {
            'criteria': {'profile_field__isnull': True},
            'profile': {'profile_field__isnull': False}
        }
        is_valid_param = isinstance(
            only_param, str) and only_param in available_filters

        if is_valid_param:
            query_filter = available_filters[only_param]
            self.queryset = self.queryset.filter(**query_filter)

    def _exclude_question_types_by_param(self):
        # Check if there's a "exclude" query param
        # to filter question types on the list of questions
        exclude_param = self.request.query_params.get('exclude', None)
        if exclude_param:
            exclude_param = exclude_param.split(",")
            question_types = [type for type, _ in QuestionType.TYPE_CHOICES]
            question_types_to_exclude = list(
                set(question_types) & set(exclude_param))
            self.queryset = self.queryset.exclude(
                question_type__type__in=question_types_to_exclude)


class QuestionAnswerResponseView(generics.ListAPIView):
    """
    Returns all questions with their related answers and user responses
    in a single efficient call (joined through prefetch_related).
    """
    serializer_class = QuestionSerializer
    permission_classes = (IsAdminUser,)

    def get_queryset(self):
        company_id = self.kwargs.get("company_id")

        # Base queryset for questions
        queryset = Question.objects.all().prefetch_related("answers")

        # Filter responses: all, or only from a specific company
        if company_id:
            # Filter responses from a specific company
            responses_qs = Response.objects.filter(user_profile__company_id=company_id)
        else:
            # All responses (for all companies)
            responses_qs = Response.objects.all()

        # Prefetch responses into questions efficiently
        queryset = queryset.prefetch_related(
            Prefetch("responses", queryset=responses_qs.select_related("user_profile"))
        )

        return queryset

    def list(self, request, *args, **kwargs):
        company_id = self.kwargs.get("company_id")
        queryset = self.get_queryset()

        data = []
        for question in queryset:
            q_data = QuestionSerializer(question).data
            q_data["answers"] = list(
                question.answers.values("id", "value", "order", "instructions")
            )

            # Add responses (already filtered in queryset)
            q_data["responses"] = list(
                question.responses.values(
                    "id", "value", "created_at",
                    "user_profile__company_id",
                    "user_profile__company__name",
                )
            )
            data.append(q_data)

        # If company_id was passed and there are no responses
        if company_id:
            company_exists = Company.objects.filter(id=company_id).exists()
            has_responses = any(q["responses"] for q in data)
            if not company_exists or not has_responses:
                return ServerResponse(
                    {"detail": "Company not found or no responses found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        return ServerResponse(data, status=status.HTTP_200_OK)   
    
class MatchingView(AuthUserThroughAdminMixin, generics.GenericAPIView):
    """
    List the matching scores of an authenticated user.

    Available query paramaters:
    Paginate results: ?page=2
    Filter matches by network slug: ?network=vilcap
    Exclude connections from matches: ?exclude=connections
    """
    permission_classes = (IsAuthenticated,)

    ENTREPRENEUR_TYPE = Company.ENTREPRENEUR
    SUPPORTER_TYPE = Company.SUPPORTER

    custom_filters = [
        {
            'key': 'name',
            'query': {
                ENTREPRENEUR_TYPE: 'user_profile__company__name__icontains',
                SUPPORTER_TYPE: 'name__icontains'
            }
        },
        {
            'key': 'network',
            'query': {
                ENTREPRENEUR_TYPE: 'user_profile__company__networks__slug',
                SUPPORTER_TYPE: 'networks__slug'
            }
        }
    ]

    def get_queryset(self):
        # No need for the queryset since we're doing things manually.
        pass

    def _validate_user_profile(self):
        logged_user = self.request.user

        try:
            self.user_profile = UserProfile.objects.select_related('company').get(
                user=logged_user)
            self.company_type = self.user_profile.company.type
            return True
        except UserProfile.DoesNotExist:
            return False

    def _set_pagination(self):
        page_param = self.request.GET.get("page")
        self.page = int(
            page_param) if page_param and page_param.isdigit() else 1

    def _set_exclusions(self):
        exclude_params = self.request.query_params.get(
            'exclude', [])
        self.exclusions = exclude_params.split(
            ",") if len(exclude_params) else None

    def _set_filters(self):
        self.filters = []

        for query_filter in self.custom_filters:
            # Grab query values
            query_param = query_filter['key']
            query_filter = query_filter['query'][self.company_type]
            query_values = self.request.query_params.get(query_param)

            # Check if query relation is "any" instead of the default "all"
            query_any_param = "{}_any".format(query_param)
            query_any_value = self.request.query_params.getlist(
                query_any_param, False)
            to_filter_any = query_any_value if isinstance(
                query_any_value, bool) else False

            if query_values:
                matching_filter = {
                    'options': {
                        'any': to_filter_any
                    },
                    'queries': []
                }

                for value in query_values.split(','):
                    matching_filter['queries'].append({
                        query_filter: value
                    })

                self.filters.append(matching_filter)

    def _fetch_entrepreneur_matches(self):
        results = getMatches(self.user_profile, page=self.page,
                             match_exclusions=self.exclusions, match_filters=self.filters)
        serializer = MatchingSerializer(results, many=True)
        return serializer.data

    def _fetch_supporter_matches(self):
        supporter = Supporter.objects.select_related('locations_weight').select_related('sectors_weight').select_related(
            'level_weight').prefetch_related('sectors').prefetch_related('locations').get(user_profile=self.user_profile)
        results = getMatchesSupporter(
            supporter, page=self.page, match_exclusions=self.exclusions, match_filters=self.filters)
        serializer = MatchingSupportersAffiliateSerializer(
            results, many=True, context={'supporter': supporter})
        return serializer.data

    def get(self, request, format=None, company=None):
        if not self._validate_user_profile():
            return ServerResponse(
                {'error': 'Profile not found', 'code': 'profile_not_found'},
                status=status.HTTP_404_NOT_FOUND)

        self._set_pagination()
        self._set_exclusions()
        self._set_filters()

        matches = []

        if self.company_type == Company.ENTREPRENEUR:
            matches = self._fetch_entrepreneur_matches()
        elif self.company_type == Company.SUPPORTER:
            matches = self._fetch_supporter_matches()

        return ServerResponse(matches, status=status.HTTP_200_OK)


class MatchingByCompanyView(AuthUserThroughAdminMixin, generics.RetrieveAPIView):
    """
    List the matching score of a given company by ID
    for the authenticated user.
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        logged_user = self.request.user
        company_id = kwargs.get('company', None)

        try:
            user_profile = UserProfile.objects.select_related('company').get(
                user=logged_user)
            match_profile = UserProfile.objects.select_related(
                'company').get(company=company_id)
        except UserProfile.DoesNotExist:
            return ServerResponse(
                {'error': 'Profile not found', 'code': 'profile_not_found'},
                status=status.HTTP_404_NOT_FOUND)

        is_entrepreneur = user_profile.company.type == 0
        is_supporter = user_profile.company.type == 1

        if is_entrepreneur:
            match = getEntrepreneurMatchByCompany(user_profile, match_profile)
            serializer = MatchingSerializer(match)
        elif is_supporter:
            supporter = Supporter.objects.select_related('locations_weight') \
                .select_related('sectors_weight').select_related('level_weight') \
                .prefetch_related('sectors').prefetch_related('locations').get(user_profile=user_profile)
            match = getSupporterMatchByCompany(
                supporter, match_profile.company)
            serializer = MatchingSupportersSerializer(match)

        if match:
            return ServerResponse(serializer.data, status=status.HTTP_200_OK)
        else:
            return ServerResponse(status=status.HTTP_404_NOT_FOUND)


class MatchingLoadingStateView(generics.GenericAPIView):
    """
    This view retrives the current matching calculations
    loading state of the authenticated user.
    """
    permissions_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        logged_user = self.request.user

        try:
            user_profile = UserProfile.objects.select_related('company').get(user=logged_user)
        except UserProfile.DoesNotExist:
            return ServerResponse(
                {'error': 'Profile not found', 'code': 'profile_not_found'},
                status=status.HTTP_404_NOT_FOUND)

        loading_check = (
            'company_id', user_profile.company.id) if user_profile.company.type == Company.ENTREPRENEUR else (
            'supporter_id', user_profile.supporter.first().id)

        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    "select exists(select 1 from matching.ongoing_calculations where %s = %i)" %
                    loading_check)
                is_loading = cursor.fetchone()[0]
                return ServerResponse({'loading': is_loading})
            except Exception as error:
                bugsnag.notify(Exception("Error while fetching ongoing calculation."),
                               meta_data={"context": {"error": error}})
                # Explicitly assume that no ongoing calculations exist:
                return ServerResponse({'loading': False})
            finally:
                cursor.close()


class RetrieveMatchingScoresImpactView(generics.GenericAPIView):
    """
    This view retrieves the percentual impact that each
    individual criteria has on the final matching percentage.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MatchingScoresImpactSerializer

    def _get_match_impact_details(self, entrepreneur, supporter, auth_company_type):
        with connection.cursor() as cursor:
            # Matches and impacts
            cursor.execute(f'''
                SELECT
                    ls.company_id,
                    ls.supporter_id,
                    COALESCE(ls.score, 0) AS location_score,
                    COALESCE(ls.max_score, 0) AS location_max_score,
                    COALESCE(ss.score, 0) AS sector_score,
                    COALESCE(ss.max_score, 0) AS sector_max_score,
                    COALESCE(lvs.score, 0) AS level_score,
                    COALESCE(lvs.max_score, 0) AS level_max_score,
                    COALESCE(rs.score, 0) AS response_score,
                    COALESCE(rs.max_score, 0) AS response_max_score,
                    COALESCE(ts.score, 0) AS total_score,
                    (COALESCE(ls.max_score, 0) + COALESCE(ss.max_score, 0) + COALESCE(lvs.max_score, 0) + COALESCE(rs.max_score, 0)) AS max_total_score,
                    CASE WHEN mlv.is_unanswered THEN NULL ELSE COALESCE(mlv.is_match, FALSE) END AS location_match,
                    CASE WHEN msv.is_unanswered THEN NULL ELSE COALESCE(msv.is_match, FALSE) END AS sector_match,
                    CASE WHEN mav.is_unanswered THEN NULL ELSE COALESCE(mav.is_match, FALSE) END AS level_match
                FROM matching.location_score AS ls
                LEFT JOIN matching.sector_score AS ss ON ss.company_id = ls.company_id AND ss.supporter_id = ls.supporter_id
                LEFT JOIN matching.level_score AS lvs ON lvs.company_id = ls.company_id AND lvs.supporter_id = ls.supporter_id
                LEFT JOIN matching.response_score AS rs ON rs.company_id = ls.company_id AND rs.supporter_id = ls.supporter_id
                LEFT JOIN matching.total_score AS ts ON ts.company_id = ls.company_id AND ts.supporter_id = ls.supporter_id
                LEFT JOIN matching.match_location_view AS mlv ON mlv.company_id = ls.company_id AND mlv.supporter_id = ls.supporter_id
                LEFT JOIN matching.match_sector_view AS msv ON msv.company_id = ls.company_id AND msv.supporter_id = ls.supporter_id
                LEFT JOIN matching.match_assessment_view AS mav ON mav.company_id = ls.company_id AND mav.supporter_id = ls.supporter_id
                WHERE ls.company_id = {entrepreneur.pk} AND ls.supporter_id = {supporter.pk}
            ''')
            details = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))
            if details['max_total_score']:
                details['location_impact'] = max(-99,
                                                 min(int(details['location_score'] / details['max_total_score'] * 100),
                                                     99))
                details['sector_impact'] = max(-99,
                                               min(int(details['sector_score'] / details['max_total_score'] * 100),
                                                   99))
                details['level_impact'] = max(-99,
                                              min(int(details['level_score'] / details['max_total_score'] * 100),
                                                  99))
                details['response_impact'] = max(-99,
                                                 min(int(details['response_score'] / details['max_total_score'] * 100),
                                                     99))
                details['score'] = max(0, min(int(details['total_score'] / details['max_total_score'] * 100), 99))
            else:
                details['location_impact'] = 0
                details['sector_impact'] = 0
                details['level_impact'] = 0
                details['response_impact'] = 0
                details['score'] = 99
            return details

    def get_object(self, auth_user, company_uid):
        try:
            auth_company = Company.objects.prefetch_related('locations', 'sectors').get(company_profile__user=auth_user)
            request_company = Company.objects.prefetch_related('locations', 'sectors').get(uid=company_uid)

            # Skip authenticated users that are ambiguously requesting details of themselves
            if (auth_company.type == request_company.type):
                return None

            entrepreneur = auth_company if auth_company.type == Company.ENTREPRENEUR else request_company
            entrepreneur.level = Assessment.objects.filter(
                evaluated=entrepreneur.pk).values_list(
                'level__value', 'level__title').latest('created_at')
            supporter = Supporter.objects.prefetch_related('locations', 'sectors').get(
                user_profile__company=auth_company if auth_company.type == Company.SUPPORTER else request_company
            )

            return auth_company.type, entrepreneur, supporter, self._get_match_impact_details(
                entrepreneur, supporter, auth_company.type)

        except (Company.DoesNotExist, Supporter.DoesNotExist):
            return None

    def get_serializer(self, *args, **kwargs):
        # Overriding this generic method to allow including extra context onto the serializer class
        serializer_class = self.get_serializer_class()
        kwargs['context'] = {
            **self.get_serializer_context(),
            **kwargs['context']
        }
        return serializer_class(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        company_uid = kwargs.get('company', None)

        try:
            auth_company_type, entrepreneur, supporter, criteria_by_impact = self.get_object(
                request.user, company_uid)
        except(Exception):
            return ServerResponse(
                {'error': 'No match found', 'code': 'match_not_found'},
                status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(criteria_by_impact, context={
            'auth_company_type': auth_company_type,
            'entrepreneur': entrepreneur,
            'supporter': supporter
        })
        return ServerResponse(serializer.data)


class SupportersTypesList(generics.ListAPIView):
    """
    This viewset is to retrive types of supporters.
    """
    serializer_class = SupporterTypeSerializer

    def get_queryset(self):
        """
        This view should return the pulic supporter types or
        assoaciated to the auth user
        """

        supporterTypesQuery = Q(public=True) | Q(supporter__user_profile__user__id=self.request.user.id) if self.request.user.is_authenticated else Q(public=True)

        return SupporterType.objects.filter(supporterTypesQuery).distinct()


class RegisterSupporterView(RegisterView):
    serializer_class = CreateSupporterSerializer

    def get_response_data(self, serializer_data):
        return {
            'company': serializer_data['company'].id,
            'supporter': serializer_data['supporter'].id,
            **TokenSerializer(serializer_data['user'].auth_token).data
        }

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializar_data = self.perform_create(serializer)
        return ServerResponse(self.get_response_data(serializar_data),
                              status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        serializar_data = serializer.save(self.request)
        create_token(self.token_model, serializar_data['user'], serializer)

        notifications_enabled = self.request.query_params.get(
            'notifications', None) != 'off'
        email_notifications_setting = allauth_settings.EMAIL_VERIFICATION if notifications_enabled else allauth_settings.EmailVerificationMethod.NONE

        complete_signup(self.request._request, serializar_data['user'],
                        email_notifications_setting,
                        None)

        return serializar_data


class RegisterPendingSupporterView(generics.GenericAPIView):
    """
    Submit a multi-step/request registration of pending supporters:
    * 1 - Submit an email which will generate a registration token
    * 2 - Submit either all or progressively the remaining fields along with the registration token
    """
    serializer_class = RegisterPendingSupporterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = serializer.create_or_update(validated_data=serializer.validated_data)
        return ServerResponse(response, status=status.HTTP_200_OK)


class FinishedPendingSupporterView(generics.GenericAPIView):
    """
    Finish a Supporter Pending Registration
    """
    serializer_class = FinishedPendingSupporterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pending_user = serializer.finish(validated_data=serializer.validated_data)
        return build_login_user(pending_user)


class SupportersView(generics.RetrieveUpdateAPIView):
    """
    get:
    Retrieve a Supporter either through:
    * Supporter ID : supporters/:id
    * User Profile ID : supporters/?user_profile=:user_profile_id
    * Company ID : supporters/?company=:company_id

    put:
    Update Supporter fields for the authenticated user.
    """
    multiple_lookup_fields = ['pk']
    serializer_class = SupporterSerializer
    lookup_field = "user_profile"
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """
        This view should return a the supporter with id equal
        to the one send in the request.
        """
        user_profile_param = self.request.query_params.get(
            'user_profile', None)
        company_param = self.request.query_params.get('company', None)

        if user_profile_param and user_profile_param.isdigit():
            return Supporter.objects.filter(
                user_profile__id=user_profile_param)
        elif company_param:
            if company_param.isdigit():
                user_profile = UserProfile.objects.filter(
                    company=company_param).first()
            else:
                company = Company.objects.get(access_hash=company_param)
                user_profile = UserProfile.objects.get(
                    company=company)
            if user_profile:
                return Supporter.objects.filter(
                    user_profile=user_profile)
        else:
            return Supporter.objects.all()

    def get_object(self):
        queryset = self.get_queryset()
        filter = {}
        for field in self.multiple_lookup_fields:
            if (self.kwargs[field]):
                filter[field] = self.kwargs[field]

        obj = get_object_or_404(queryset, **filter)
        self.check_object_permissions(self.request, obj)
        return obj

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        if not instance:
            return ServerResponse(
                {'error': 'Supporter not found', 'code': 'supporter_not_found'},
                status=status.HTTP_404_NOT_FOUND)

        serializer = SupporterSerializer(instance, many=False)
        return ServerResponse(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            user_profile = UserProfile.objects.get(
                user=request.user)
            Supporter.objects.get(user_profile=user_profile, id=instance.id)
        except:
            return ServerResponse(status=status.HTTP_403_FORBIDDEN)

        serializer = UpdateSupporterSerializer(
            instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return ServerResponse(serializer.data)


class SupportCategoriesTypes(generics.GenericAPIView):
    """
    This viewset is to retrive categories and type of support.
    The retrived types are organized by category.
    """
    queryset = SupporterOfferingCategories.objects.all()

    def get(self, request, *args, **kwargs):
        response = []
        categories = self.get_queryset()
        for category in categories:
            category_dict = SupporterOfferingCategoriesSerializer(
                category).data
            category_dict['category_types'] = SupporterOfferingTypesSerializer(
                SupporterOfferingTypes.objects.filter(category=category), many=True).data
            response.append(category_dict)
        return ServerResponse(response)


class CreateOfferView(generics.RetrieveUpdateDestroyAPIView):
    """
    View to handle metadata requests for the logged user.
    """
    multiple_lookup_fields = ['pk']
    queryset = SupporterOffering.objects.all()
    serializer_class = SupporterOfferingCreatorSerializer

    def get_support_offer_types(self, request):
        category = request.data["category"]
        offer_types = SupporterOfferingTypes.objects.filter(
            category=category).values_list('id', flat=True)

        return offer_types

    def get_object(self):
        queryset = Supporter.objects.all()
        filter = {}
        for field in self.multiple_lookup_fields:
            if (self.kwargs[field]):
                filter[field] = self.kwargs[field]

        obj = get_object_or_404(queryset, **filter)
        self.check_object_permissions(self.request, obj)
        return obj

    def post(self, request, *args, **kwargs):
        try:
            supporter_id = request.data['supporter']
            types = request.data["types"]
            if len(types) > 0:
                support_offer_types = self.get_support_offer_types(request)
                has_unsupported = any(
                    type not in support_offer_types for type in types)
                if has_unsupported:
                    return ServerResponse(
                        {'error': 'Type not associated with selected category', 'code': 'incorrect_type'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                user_profile = UserProfile.objects.get(
                    user=request.user)
                Supporter.objects.get(
                    user_profile=user_profile, id=supporter_id)
            except:
                return ServerResponse(status=status.HTTP_403_FORBIDDEN)

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            supporter = serializer.save()
            supporter.types.set(types)

            return ServerResponse({"Status": "success"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return ServerResponse({'error': 'Some internal error occurred'},
                                  status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        category = request.data['category']
        try:
            supporterOffer = SupporterOffering.objects.get(
                supporter=instance, category=category)
        except:
            return ServerResponse(status=status.HTTP_403_FORBIDDEN)

        serializer = UpdateSupporterOfferingSerializer(
            supporterOffer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return ServerResponse(serializer.data)

    def delete(self, request, *args, **kwargs):
        supporter = self.get_object()
        id = request.query_params['category']
        try:
            supporterOffer = SupporterOffering.objects.all()
            supportOfferFiltered = supporterOffer.filter(
                supporter=supporter, category=id)
        except:
            return ServerResponse(status=status.HTTP_403_FORBIDDEN)

        supportOfferFiltered.delete()

        return ServerResponse(status=status.HTTP_204_NO_CONTENT)


class CriteriaWeightList(generics.ListAPIView):
    queryset = CriteriaWeight.objects.all().order_by('value')
    serializer_class = CriteriaWeightSerializer


class MatchingCriteriaBySupporter(AuthUserThroughAdminMixin, generics.ListCreateAPIView):
    """
    View that lists or creates criteria for the authenticated Supporter
    """
    serializer_class = MatchingCriteriaBySupporterSerializer
    permission_classes = (IsAuthenticated, IsSupporter)

    def get_queryset(self):
        return Criteria.objects.filter(supporter__user_profile__user=self.request.user, is_active=True)

    def create(self, request, *args, **kwargs):
        # Validate user
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            supporter = Supporter.objects.get(user_profile=user_profile)
        except (UserProfile.DoesNotExist, Supporter.DoesNotExist):
            return ServerResponse(
                {'error': 'Supporter not found', 'code': 'supporter_not_found'},
                status=status.HTTP_404_NOT_FOUND)

        try:
            question = Question.objects.get(id=request.data['question'])
        except Question.DoesNotExist:
            return ServerResponse(
                {'error': 'Question not found', 'code': 'question_not_found'},
                status=status.HTTP_404_NOT_FOUND)

        supporter_data = {
            'name': f'{supporter.name} - {question.slug}',
            'supporter': supporter.id,
            'is_active': True,
        }

        # Validate request data
        serializer = MatchingCreateOrUpdateCriteriaSerializer(
            data={**supporter_data, **request.data}, many=False)
        serializer.is_valid(raise_exception=True)

        try:
            serializer.instance = Criteria.objects.get(
                supporter=serializer.validated_data['supporter'], question=serializer.validated_data['question'])
        except Criteria.DoesNotExist:
            pass

        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return ServerResponse(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class InterestedCTAView(AuthUserThroughAdminMixin, generics.ListCreateAPIView):
    """
    View that lists connections or creates
    new ones for an authenticated user
    """
    serializer_class = InterestedCTASerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """
        This view should return the company id of the logged user.
        """
        user_profile = UserProfile.objects.get(user=self.request.user)
        auth_company = user_profile.company
        auth_company_type = user_profile.company.type

        # Check if logged user type
        is_supporter = auth_company_type == 1

        if is_supporter:
            created = InterestedCTA.objects.filter(supporter=auth_company)
            return created
        else:
            created = InterestedCTA.objects.filter(entrepreneur=auth_company)
            return created

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_queryset()

        if not instance:
            return ServerResponse(
                {'error': 'Interest not found', 'code': 'interest_not_found'},
                status=status.HTTP_404_NOT_FOUND)

        serializer = InterestedCTASerializer(instance, many=True)
        return ServerResponse(serializer.data)

    def create(self, request, *args, **kwargs):
        user_profile = UserProfile.objects.get(user=request.user)
        auth_company = user_profile.company
        auth_company_type = user_profile.company.type

        # Check if logged user type
        is_supporter = auth_company_type == 1
        is_entrepreneur = auth_company_type == 0

        # If logged user is supporter update value interested entrepreneur
        if is_supporter:
            entrepreneur_company_id = request.data['entrepreneur']
            entrepreneur_company = Company.objects.get(
                id=entrepreneur_company_id)
            supporter_is_interested = request.data['supporter_is_interested']

            obj, created = InterestedCTA.objects.get_or_create(
                supporter=auth_company, entrepreneur=entrepreneur_company,
                defaults={'supporter_is_interested': supporter_is_interested})
            if created:
                calculate_interest(obj, None)

                return ServerResponse(status=status.HTTP_201_CREATED)
            else:
                newObj = InterestedCTA.objects.get(id=obj.id)
                newObj.supporter_is_interested = supporter_is_interested
                newObj.save()

                # Calculate and update state
                calculate_interest(obj, newObj)

                return ServerResponse(status=status.HTTP_200_OK)

        # If logged user is entrepreneur update value interested supporter
        elif is_entrepreneur:
            supporter_company_id = request.data['supporter']
            supporter_company = Company.objects.get(id=supporter_company_id)
            entrepreneur_is_interested = request.data['entrepreneur_is_interested']

            obj, created = InterestedCTA.objects.get_or_create(
                supporter=supporter_company, entrepreneur=auth_company,
                defaults={'entrepreneur_is_interested': entrepreneur_is_interested})

            if created:
                calculate_interest(obj, None)
                return ServerResponse(status=status.HTTP_201_CREATED)
            else:
                obj2 = InterestedCTA.objects.get(id=obj.id)
                obj2.entrepreneur_is_interested = entrepreneur_is_interested
                obj2.save()

                # Calculate and update state
                calculate_interest(obj, obj2)

                return ServerResponse(status=status.HTTP_200_OK)
        else:
            return ServerResponse(status=status.HTTP_403_FORBIDDEN)


class MatchingInterestedView(generics.ListAPIView):
    """
    View that lists the interests
    of an authenticated user by connection:
    user (interests of the user)
    targets (interested in the user)
    mutual (connected)
    """
    # This object will hold the interest resulting conditions:
    # (entrepreneur_is_interested, supporter_is_interested, state_of_interest)
    # based on the requested interest (user, targets, mutual)
    interest_conditions = {}
    connections = ['user', 'targets', 'mutual']

    permission_classes = (IsAuthenticated,)
    queryset = InterestedCTA.objects.all()
    pagination_class = PageNumberPagination
    pagination_class.page_size = 12

    ENTREPRENEUR_TYPE = Company.ENTREPRENEUR
    SUPPORTER_TYPE = Company.SUPPORTER

    custom_filters = [
        {
            'key': 'name',
            'query': {
                ENTREPRENEUR_TYPE: 'user_profile__company__name__icontains',
                SUPPORTER_TYPE: 'name__icontains'
            }
        },
        {
            'key': 'network',
            'query': {
                ENTREPRENEUR_TYPE: 'user_profile__company__networks__slug',
                SUPPORTER_TYPE: 'networks__slug'
            }
        }
    ]

    def _validate_user_profile(self):
        logged_user = self.request.user

        try:
            self.user_profile = UserProfile.objects.select_related(
                'company').get(user=logged_user)
            self.company_type = self.user_profile.company.type
        except UserProfile.DoesNotExist:
            return ServerResponse(
                {'error': 'Profile not found', 'code': 'profile_not_found'},
                status=status.HTTP_404_NOT_FOUND)

    def _set_requested_interest(self, kwargs):
        self.requested_interest = kwargs['connection'] if kwargs['connection'] in self.connections else None

        if self.requested_interest == None:
            return ServerResponse(status=status.HTTP_400_BAD_REQUEST)
        elif self.requested_interest == 'mutual':
            # If it's mutual we can set right away the interest condition
            self.setInterestConditionsAsMutual()
        else:
            # As the 'user' and 'targets' interest relies on
            # having at least one of the entities interested, we can
            # already assume that the State of Interest needs to be interested
            self.setStateOfInterestAs(InterestedCTA.INTERESTED)

    def _set_filters(self):
        self.filters = []

        for query_filter in self.custom_filters:
            # Grab query values
            query_param = query_filter['key']
            query_filter = query_filter['query'][self.company_type]
            query_values = self.request.query_params.get(query_param)

            # Check if query relation is "any" instead of the default "all"
            query_any_param = "{}_any".format(query_param)
            query_any_value = self.request.query_params.getlist(
                query_any_param, False)
            to_filter_any = query_any_value if isinstance(
                query_any_value, bool) else False

            if query_values:
                matching_filter = {
                    'options': {
                        'any': to_filter_any
                    },
                    'queries': []
                }

                for value in query_values.split(','):
                    matching_filter['queries'].append({
                        query_filter: value
                    })

                self.filters.append(matching_filter)

    def _set_entrepreneur_interest_conditions(self):
        if self.requested_interest == 'user':
            self.setEntrepreneurAsInterestedInSupporter()
        elif self.requested_interest == 'targets':
            self.setSupporterAsInterestedInEntrepreneur()

    def _fetch_entrepreneur_interest_matches(self):
        try:
            interests = InterestedCTA.objects.filter(
                entrepreneur=self.user_profile.company,
                supporter__company_profile__user__emailaddress__verified=True,
                **self.interest_conditions)
            matching_results = getEntrepreneurInterestMatches(
                self.user_profile.company, interests, match_filters=self.filters)
            paginated_results = self.paginate_queryset(matching_results)
            serializer = MatchingSerializer(paginated_results, many=True)
            return self.get_paginated_response(serializer.data)
        except InterestedCTA.DoesNotExist:
            return ServerResponse(
                {'error': 'Interest not found', 'code': 'interest_not_found'},
                status=status.HTTP_404_NOT_FOUND)

    def _set_supporter_interest_conditions(self):
        if self.requested_interest == 'user':
            self.setSupporterAsInterestedInEntrepreneur()
        elif self.requested_interest == 'targets':
            self.setEntrepreneurAsInterestedInSupporter()

    def _fetch_supporter_interest_matches(self):
        try:
            interests = InterestedCTA.objects.filter(
                supporter=self.user_profile.company,
                entrepreneur__company_profile__user__emailaddress__verified=True,
                **self.interest_conditions)
            supporter = Supporter.objects.get(user_profile=self.user_profile)
            matching_results = getSupporterInterestMatches(
                supporter, interests, match_filters=self.filters)
            paginated_results = self.paginate_queryset(matching_results)
            serializer = MatchingSupportersAffiliateSerializer(
                paginated_results, many=True, context={'supporter': supporter})
            return self.get_paginated_response(serializer.data)
        except InterestedCTA.DoesNotExist:
            return ServerResponse(
                {'error': 'Interest not found', 'code': 'interest_not_found'},
                status=status.HTTP_404_NOT_FOUND)

    def get(self, request, *args, **kwargs):
        self._validate_user_profile()
        self._set_requested_interest(kwargs)
        self._set_filters()

        if self.company_type == self.ENTREPRENEUR_TYPE:
            self._set_entrepreneur_interest_conditions()
            return self._fetch_entrepreneur_interest_matches()
        elif self.company_type == self.SUPPORTER_TYPE:
            self._set_supporter_interest_conditions()
            return self._fetch_supporter_interest_matches()

    def setStateOfInterestAs(self, state):
        self.interest_conditions['state_of_interest'] = state

    def setInterestConditionsAsMutual(self):
        self.interest_conditions['entrepreneur_is_interested'] = InterestedCTA.INTERESTED
        self.interest_conditions['supporter_is_interested'] = InterestedCTA.INTERESTED
        self.interest_conditions['state_of_interest'] = InterestedCTA.CONNECTED

    def setEntrepreneurAsInterestedInSupporter(self):
        self.interest_conditions['entrepreneur_is_interested'] = InterestedCTA.INTERESTED
        self.interest_conditions['supporter_is_interested'] = InterestedCTA.INITIAL_VALUE

    def setSupporterAsInterestedInEntrepreneur(self):
        self.interest_conditions['entrepreneur_is_interested'] = InterestedCTA.INITIAL_VALUE
        self.interest_conditions['supporter_is_interested'] = InterestedCTA.INTERESTED


class SupporterListOrCreateAffiliatesView(generics.ListCreateAPIView):
    serializer_class = AffiliateSerializer
    queryset = Affiliate.objects.all()
    permission_classes = [IsAuthenticated, IsSupporter]

    def get_queryset(self):
        supporter = get_object_or_404(Supporter,
                                      user_profile__user=self.request.user)
        queryset = self.queryset
        queryset = queryset.filter(supporters=supporter)
        return queryset


class SupporterListOrCreateAssessmentLinkView(AuthUserThroughAdminMixin, SupporterListOrCreateAffiliatesView):
    """
    get:
    View to list the (self-assessment) affiliate flow(s)
    of the authenticated user.

    post:
    View to generate a "self-assessment" affiliate flow
    for the authenticated user (supporter) to share with entrepreneurs.

    Required fields:
    * slug - Affiliate URL identifier
    """

    def create(self, request):
        serializer = SupporterCreateEntrepreneurLinkSerializer(
            data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.data
        requested_slug = validated_data['slug']
        supporter = get_object_or_404(Supporter,
                                      user_profile__user=request.user)
        supporter_company = supporter.user_profile.company
        affiliate_name = supporter.name + ' - ' + requested_slug
        affiliate = {
            'name': affiliate_name,
            'shortcode': requested_slug,
            'slug': requested_slug,
            'email': supporter_company.email or request.user.email,
            'flow_type': Affiliate.SELF_ASSESSMENT
        }

        if supporter_company.website:
            affiliate['website'] = supporter_company.website

        if supporter_company.logo:
            affiliate['logo'] = supporter_company.logo

        created_affiliate = Affiliate.objects.create(**affiliate)
        created_affiliate.supporters.set([supporter.id])
        created_result = self.get_serializer(created_affiliate)

        return ServerResponse(created_result.data, status=status.HTTP_200_OK)


class MatchingQuestionsForAdditionalCriteriaView(generics.ListAPIView):
    """
    List all question-categories with its eligible question
    types which can be used for creating additional Criteria.
    """
    serializer_class = MatchingQuestionsForAdditionalCriteriaSerializer

    def get_queryset(self):
        eligible_question_types = [QuestionType.SINGLE_SELECT,
                                   QuestionType.MULTI_SELECT, QuestionType.NUMERIC, QuestionType.RANGE]

        # Fetch question-categories only with questions of type single/multi select
        queryset = QuestionCategory.objects.prefetch_related(
            Prefetch(
                'question_set',
                queryset=Question.objects
                .select_related('question_type')
                .prefetch_related('answer_set')
                .filter(short_name__isnull=False, question_type__type__in=eligible_question_types)
            )) \
            .filter(question__short_name__isnull=False, question__question_type__type__in=eligible_question_types) \
            .distinct()

        return queryset


class ListQuestionBundlesView(generics.ListAPIView):
    queryset = QuestionBundle.objects.prefetch_related(
        'questions__question_type', 'questions__question_category', 'questions__answer_set').all()
    serializer_class = QuestionBundleSerializer
    pagination_class = PageNumberPagination
    pagination_class.page_size = 10

    def get_queryset(self):
        """
        Optionally restricts the returned question bundles to a given category id or category level id,
        by filtering against a `category` or `category_level` query parameter in the URL.
        """
        queryset = self.queryset
        category_id = self.request.query_params.get('category')
        category_level_id = self.request.query_params.get('category_level')

        if bool(category_id) and category_id.isnumeric():
            queryset = queryset.filter(category__pk=category_id)
        if bool(category_level_id) and category_level_id.isnumeric():
            queryset = queryset.filter(category_level__pk=category_level_id)

        return queryset


class AlgorithmCalculatorSearchCompaniesView(generics.ListAPIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAdminUser]
    serializer_class = AlgorithmCalculatorSearchCompaniesSerializer

    def get_queryset(self):
        queryset = Company.objects.all()
        query = self.request.query_params.get('query')
        company_type = self.request.query_params.get('type')
        if query:
            queryset = queryset.filter(name__icontains=query)
        if type is not None:
            queryset = queryset.filter(type=company_type)
        return queryset.order_by('name')[:10]


class AlgorithmCalculatorMatchingCriteriaView(generics.GenericAPIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAdminUser]
    serializer_class = AlgorithmCalculatorMatchingCriteriaSerializer

    def _get_static_criteria(self, entrepreneur, supporter):
        with connection.cursor() as cursor:
            cursor.execute(f'''
                SELECT
                    level.weight_id AS level_weight_id,
                    level.is_match AS level_is_match,
                    level.is_unanswered AS level_is_unanswered,
                    sector.weight_id AS sector_weight_id,
                    sector.is_match AS sector_is_match,
                    sector.is_unanswered AS sector_is_unanswered,
                    location.weight_id AS location_weight_id,
                    location.is_match AS location_is_match,
                    location.is_unanswered AS location_is_unanswered
                FROM (
                    SELECT weight_id, is_match, is_unanswered
                    FROM matching.match_assessment_view
                    WHERE company_id = {entrepreneur.pk} AND supporter_id = {supporter.pk}
                ) AS level
                LEFT JOIN (
                    SELECT weight_id, is_match, is_unanswered
                    FROM matching.match_sector_view
                    WHERE company_id = {entrepreneur.pk} AND supporter_id = {supporter.pk}
                ) AS sector ON 1=1
                LEFT JOIN (
                    SELECT weight_id, is_match, is_unanswered
                    FROM matching.match_location_view
                    WHERE company_id = {entrepreneur.pk} AND supporter_id = {supporter.pk}
                ) AS location ON 1=1;
            ''')
            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row else False

    def _get_responses(self, entrepreneur, supporter):
        with connection.cursor() as cursor:
            cursor.execute(f'''
                SELECT DISTINCT ON (qc.question_id)
                    mc.name,
                    mc.criteria_weight_id,
                    (CASE WHEN mrv.company_id IS NULL THEN TRUE ELSE FALSE END) AS is_unanswered,
                    mrv.is_correct
                FROM matching.entrepreneur_supporter_view AS esv
                LEFT JOIN matching.question_criteria_view AS qc
                    ON qc.supporter_id = esv.supporter_id
                LEFT JOIN matching.match_response_view AS mrv
                    ON mrv.supporter_id = esv.supporter_id
                        AND mrv.company_id = esv.company_id
                        AND qc.question_id = mrv.question_id
                LEFT JOIN matching_criteria AS mc
                    ON mc.id = qc.criteria_id
                WHERE qc.question_id IS NOT NULL
                AND esv.company_id = {entrepreneur.pk}
                AND esv.supporter_id = {supporter.pk};
            ''')
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _get_match_state(self, is_match, is_unanswered):
        if is_unanswered:
            return 3
        else:
            return 1 if is_match else 2

    def get(self, request):
        supporter_id = request.query_params.get('supporter_id')
        entrepreneur_id = request.query_params.get('entrepreneur_id')

        supporter = get_object_or_404(Supporter, user_profile__company_id=supporter_id)
        entrepreneur = get_object_or_404(Company, id=entrepreneur_id)

        static_criteria_data = self._get_static_criteria(entrepreneur, supporter)

        if not static_criteria_data:
            return ServerResponse({}, status=status.HTTP_404_NOT_FOUND)

        responses_data = self._get_responses(entrepreneur, supporter)

        criteria = [
            {
                'name': 'Level',
                'weight_id': static_criteria_data['level_weight_id'],
                'match_state': self._get_match_state(
                    static_criteria_data['level_is_match'],
                    static_criteria_data['level_is_unanswered']
                )
            },
            {
                'name': 'Sector',
                'weight_id': static_criteria_data['sector_weight_id'],
                'match_state': self._get_match_state(
                    static_criteria_data['sector_is_match'],
                    static_criteria_data['sector_is_unanswered']
                )
            },
            {
                'name': 'Location',
                'weight_id': static_criteria_data['location_weight_id'],
                'match_state': self._get_match_state(
                    static_criteria_data['location_is_match'],
                    static_criteria_data['location_is_unanswered']
                )
            },
            *[{
                'name': response['name'],
                'weight_id': response['criteria_weight_id'],
                'match_state': self._get_match_state(
                    response['is_correct'],
                    response['is_unanswered']
                )
            } for response in responses_data]
        ]

        return ServerResponse(criteria, status=status.HTTP_200_OK)
