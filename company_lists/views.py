import re
from django.shortcuts import get_object_or_404
from django.db.models import Q, Prefetch
from django.contrib.postgres.aggregates import ArrayAgg

from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework_csv.renderers import CSVRenderer

from matching.models import SupporterInterestSector, SupporterInterestLocation
from matching.algorithm import getMatchesForEntrepreneurFromSupporters
from matching.algorithm_supporters import getMatchesForSupporterFromEntrepreneurs
from matching.models import Answer, Question, QuestionType, Response as MatchingResponse
from shared.models import random_uid
from shared.utils import format_demographic_response_value
from viral.models import Company
from grid.models import Category, Assessment

from company_lists.mixins import CompanyListsPermissionsMixin
from company_lists.models import CompanyList, Process, ProcessStep
from company_lists.permissions import (
    IsCompanyListInvitedUser,
    IsCompanyListOwnerOrReadOnly,
)
from company_lists.serializers import (
    GuestRetrieveCompanyListSerializer,
    ListCompaniesSerializer,
    ListEntrepreneurCompaniesCSVSerializer,
    ListInvitedGuestSerializer,
    ListInvitedUserSerializer,
    ListOrCreateCompanyListsSerializer,
    ListSharedCompanyListsSerializer,
    ListSupporterCompaniesCSVSerializer,
    RetrieveOrUpdateCompanyListSerializer,
)


class FetchCompanyListUsersView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        # TODO: here we are merging two serializer together, maybe in the future we need to apply custom pagination to
        # this for performance reasons if the list gets to big

        list_uid = kwargs.get("list_uid")

        try:
            company_list = CompanyList.objects.prefetch_related(
                "invited_users", "invited_guests"
            ).get(uid=list_uid, owner__user=self.request.user)

            invited_users = ListInvitedUserSerializer(
                company_list.invited_users.all(), many=True
            )
            invited_guests = ListInvitedGuestSerializer(
                company_list.invited_guests.all(), many=True
            )

            users = invited_users.data + invited_guests.data
            return Response(users)
        except CompanyList.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class CompanyListEntrepreneursCSVRenderer(CSVRenderer):
    header = [
        "uid",
        "name",
        "founded_date",
        "email",
        "website",
        "profile_url",
        "about",
        "location.formatted_address",
        "location.city",
        "location.region",
        "location.region_abbreviation",
        "location.country",
        "location.continent",
        "sectors",
        "sector_groups",
        "match_score",
        "connection_state",
        "viral_investment_level",
        "viral_category_levels",
    ]
    labels = {
        "viral_investment_level": "VIL",
        "viral_category_levels": "VIL Categories",
        "investing_level_range": "VIL Range",
        "location.formatted_address": "location.street_address",
        "location.groups__name": "location.groups",
    }


class CompanyListSupportersCSVRenderer(CompanyListEntrepreneursCSVRenderer):
    header = [
        "uid",
        "name",
        "email",
        "website",
        "profile_url",
        "about",
        "location.formatted_address",
        "location.city",
        "location.region",
        "location.region_abbreviation",
        "location.country",
        "location.continent",
        "sectors",
        "supporter_types",
        "sectors_of_interest",
        "sector_groups_of_interest",
        "locations_of_interest",
        "location_groups_of_interest",
        "match_score",
        "connection_state",
        "investing_level_range",
    ]


class FetchCompanyListCompanies(CompanyListsPermissionsMixin, generics.ListAPIView):
    lookup_field = "uid"
    permission_classes = (IsCompanyListOwnerOrReadOnly,)
    serializer_class = ListCompaniesSerializer

    # TEMPORARY: Disabled until front-end implements pagination:
    pagination_class = PageNumberPagination
    pagination_class.page_size = 8

    def _format_is_csv(self, request):
        return request.query_params.get("format", False) == "csv"

    def _user_with_company_type(self, company_type):
        is_authenticated = self.request.user and self.request.user.is_authenticated

        if not is_authenticated:
            return False

        request_company = self.request.user.userprofile.company
        return request_company.type == company_type

    def get_renderers(self):
        if self._format_is_csv(self.request):
            if self._user_with_company_type(Company.SUPPORTER):
                self.renderer_classes = (CompanyListEntrepreneursCSVRenderer,) + tuple(
                    api_settings.DEFAULT_RENDERER_CLASSES
                )
            elif self._user_with_company_type(Company.ENTREPRENEUR):
                self.renderer_classes = (CompanyListSupportersCSVRenderer,) + tuple(
                    api_settings.DEFAULT_RENDERER_CLASSES
                )

        return super().get_renderers()

    def get_serializer(self, *args, **kwargs):
        companies = args[0] if len(args) else []
        entrepreneur_companies = []
        supporter_companies = []
        scores = []

        for company in companies:
            if company.type == Company.ENTREPRENEUR:
                entrepreneur_companies.append(company)
            else:
                supporter_companies.append(company)

        # Gather all scores beforehand to avoid n+1 queries
        if self._user_with_company_type(Company.ENTREPRENEUR):
            supporters = [
                company.company_profile.supporter.first()
                for company in supporter_companies
            ]
            scores = (
                getMatchesForEntrepreneurFromSupporters(
                    self.request.user.userprofile, supporters=supporters
                )
                or []
            )
            scores += [
                {"company": company, "score": None}
                for company in entrepreneur_companies
            ]
        elif self._user_with_company_type(Company.SUPPORTER):
            supporter = self.request.user.userprofile.supporter.first()
            scores = (
                getMatchesForSupporterFromEntrepreneurs(
                    supporter, companies=entrepreneur_companies
                )
                or []
            )
            scores += [
                {"supporter": company.company_profile.supporter.first(), "score": None}
                for company in supporter_companies
            ]

        serializer_class = self.get_serializer_class()
        kwargs["context"] = self.get_serializer_context()
        kwargs["context"]["scores"] = scores
        return serializer_class(*args, **kwargs)

    def get_serializer_class(self):
        if self._format_is_csv(self.request):
            return (
                ListEntrepreneurCompaniesCSVSerializer
                if self._user_with_company_type(Company.SUPPORTER)
                else ListSupporterCompaniesCSVSerializer
            )
        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        is_authenticated = self.request.user and self.request.user.is_authenticated
        context["supporter"] = (
            self.request.user.userprofile.supporter.first()
            if is_authenticated
            else None
        )
        return context

    def get(self, request, *args, **kwargs):
        company_list = get_object_or_404(CompanyList, uid=self.kwargs["uid"])
        self.check_object_permissions(request, company_list)

        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        if self._format_is_csv(self.request):
            # Remove pagination for CSV output:
            self.pagination_class = None

        supporters_queryset = Company.objects.prefetch_related(
            # Company
            "sectors",
            "networks",
            "company_profile__user",
            # Supporter
            "company_profile__supporter",
            "company_profile__supporter__types",
            "company_profile__supporter__user_profile__company__locations",
            "company_profile__supporter__supporteroffering_set__category",
            "company_profile__supporter__supporteroffering_set__types",
            "company_profile__supporter__criteria_set__answers",
            "company_profile__supporter__criteria_set__question__question_type",
            "company_profile__supporter__criteria_set__question__question_category",
            "company_profile__supporter__criteria_set__question__answer_set",
            Prefetch(
                "company_profile__supporter__sectors_of_interest",
                queryset=SupporterInterestSector.objects.select_related("group")
                .prefetch_related("sector__groups")
                .filter(group=None),
                to_attr="ungrouped_sectors",
            ),
            Prefetch(
                "company_profile__supporter__sectors_of_interest",
                queryset=SupporterInterestSector.objects.select_related("group")
                .prefetch_related("sector__groups")
                .exclude(group=None),
                to_attr="grouped_sectors",
            ),
            Prefetch(
                "company_profile__supporter__locations_of_interest",
                queryset=SupporterInterestLocation.objects.select_related("group")
                .prefetch_related("location__groups")
                .filter(group=None),
                to_attr="ungrouped_locations",
            ),
            Prefetch(
                "company_profile__supporter__locations_of_interest",
                queryset=SupporterInterestLocation.objects.select_related("group")
                .prefetch_related("location__groups")
                .exclude(group=None),
                to_attr="grouped_locations",
            ),
        ).filter(
            type=Company.SUPPORTER,
            companylist__uid=self.kwargs["uid"],
        )

        entrepreneurs_queryset = Company.objects.prefetch_related(
            "company_profile", "locations", "sectors__groups", "networks__locations"
        ).filter(
            type=Company.ENTREPRENEUR,
            companylist__uid=self.kwargs["uid"],
        )

        return supporters_queryset.union(entrepreneurs_queryset).order_by("id")


class ListOrCreateCompanyListsView(generics.ListCreateAPIView):
    """
    List or Create Company Lists
    """

    serializer_class = ListOrCreateCompanyListsSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """
        Filter company lists owned by the requesting user.
        """
        supporter = self.request.user.userprofile.supporter.first()
        return (
            CompanyList.objects.annotate(
                verified_companies=ArrayAgg(
                    "companies__id",
                    filter=Q(
                        companies__company_profile__user__emailaddress__verified=True
                    ),
                    distinct=True,
                ),
            ).prefetch_related(
                "companies",
                "invited_users",
                "invited_users__user",
                "invited_users__company",
                "invited_guests",
            )
            .filter(
                (
                    Q(
                        company_list_type=CompanyList.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS
                    ) & (
                        Q(affiliate__company__company_profile__user=self.request.user)
                        | (
                            Q(affiliate__supporters__id=supporter.id)
                            if supporter
                            else Q()
                        )
                    )
                )
                | (
                    Q(company_list_type=CompanyList.COMPANY_LIST_TYPE_STATIC)
                    & Q(owner__user=self.request.user)
                )
            )
            .distinct()
            .order_by("-pinned", "-company_list_type", "-updated_at")
        )


class ListSharedCompanyListsView(generics.ListAPIView):
    """
    List Company Lists shared with a user
    """

    queryset = (
        CompanyList.objects.annotate(
            verified_companies=ArrayAgg(
                "companies__id",
                filter=Q(companies__company_profile__user__emailaddress__verified=True),
                distinct=True,
            ),
        )
        .prefetch_related("companies")
        .order_by("-updated_at")
        .all()
    )
    serializer_class = ListSharedCompanyListsSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """
        Filter company lists where the requesting user has been invited.
        """
        queryset = super().get_queryset()
        return queryset.filter(invited_users__user=self.request.user)


class RetrieveUpdateOrDeleteCompanyListView(
    CompanyListsPermissionsMixin, generics.RetrieveUpdateDestroyAPIView
):
    lookup_field = "uid"
    permission_classes = (IsCompanyListOwnerOrReadOnly,)
    queryset = (
        CompanyList.objects.prefetch_related(
            "owner__company",
            "invited_users__user",
            "invited_users__company",
            "invited_guests",
            "companies",
        )
        .order_by("-pinned", "-updated_at")
        .all()
    )

    def _reset_link(self):
        company_list = self.get_object()

        # Generate a new list UID
        company_list.uid = random_uid()
        self.kwargs[self.lookup_field] = company_list.uid

        # Remove guest users
        company_list.invited_guests.clear()

        company_list.save()

    def _reset_passcode(self):
        company_list = self.get_object()
        company_list.passcode = random_uid()
        company_list.save()

    def patch(self, request, *args, **kwargs):
        with_reset_link = request.query_params.get("reset", False) == "link"
        with_reset_passcode = request.query_params.get("reset", False) == "passcode"

        if with_reset_link:
            self._reset_link()

        if with_reset_passcode:
            self._reset_passcode()

        return self.partial_update(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        company_list = self.get_object()

        # Add guest to invited guests (if not already)
        if self._is_guest(request):
            self._add_guest_to_invited(company_list, request.query_params.get("email"))

        serializer = self.get_serializer(company_list)
        return Response(serializer.data)

    def get_serializer_class(self):
        if self._is_guest(self.request):
            return GuestRetrieveCompanyListSerializer
        return RetrieveOrUpdateCompanyListSerializer


class RemoveUserFromSharedCompanyListsView(generics.GenericAPIView):
    lookup_field = "uid"
    permission_classes = (IsCompanyListInvitedUser,)
    queryset = CompanyList.objects.all()

    def delete(self, request, *args, **kwargs):
        company_list = self.get_object()
        invited_user = company_list.invited_users.filter(user=request.user)

        if invited_user.exists():
            company_list.invited_users.remove(invited_user.first())
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(status=status.HTTP_400_BAD_REQUEST)


class CompanyListChoicesView(generics.GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, pk, *args, **kwargs):
        company = get_object_or_404(Company, pk=pk)
        company_lists = CompanyList.objects.filter(owner__company=company).order_by(
            "title"
        )
        return Response(
            [
                {
                    "id": company_list.id,
                    "title": company_list.title,
                }
                for company_list in company_lists
            ]
        )


class ListProcessesView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        processes = Process.objects.filter(
            company_id=self.request.user.userprofile.company_id
        )
        return Response(
            [
                {
                    "uid": process.id,
                    "title": process.title,
                    "description": process.description,
                }
                for process in processes
            ]
        )


class RetrieveProcessView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, process_id, *args, **kwargs):
        try:
            process = Process.objects.get(id=process_id)
        except Process.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        output = {
            "id": process.id,
            "title": process.title,
            "description": process.description,
            "steps": [
                {
                    "id": step.id,
                    "title": step.title,
                    "description": step.description,
                    "order": step.order,
                    "company_list_id": step.company_list_id,
                }
                for step in process.steps.order_by("order")
            ],
        }

        return Response(output)


class RetrieveProcessDemographicStatsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    minimum_companies_per_step = 5

    def get(self, request, process_id, *args, **kwargs):
        # We first try to retrieve the requested Process and Question from the database.
        try:
            process = Process.objects.prefetch_related(
                "steps", "steps__company_list", "steps__company_list__companies"
            ).get(id=process_id)
            question = Question.objects.prefetch_related("answer_set").get(
                slug__iexact=self.request.GET.get("question_slug")
            )
        except (Process.DoesNotExist, Question.DoesNotExist):
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Then we fetch all possible Answers from the database.
        answers = question.answer_set.all()

        # Start preparing the data to be returned in the response.
        # It should match the following schema: /company_lists/tests/schemas/process-demographics-schema.py.
        data = []

        # First, we iterate over each Step of the Process.
        for step in process.steps.order_by("order"):
            # We create a dictionary with initial data for this step.
            # This must contain:
            #   - the title of the Company List associated with this step
            #   - a list with all the companies and their count/percentage of each answer
            #   - a list with all answers and their counts (aggregated)
            #   - the total number of companies that have submitted responses
            step_data = {
                "step": step.title,
                "companies": [],
                "responses": [
                    {
                        "value": format_demographic_response_value(answer.value),
                        "count": 0,
                        "percentage": 0,
                    }
                    for answer in answers
                ],
                "companies_with_responses": 0,
                "is_locked": False,
            }

            # We'll need the total number of responses in this step to calculate the percentage of each answer.
            total_responses_in_step = 0

            # We iterate over each Company in the CompanyList of this Step in order to populate step_data['companies'].
            for company in step.company_list.companies.all():
                # We fetch the latest response of each Team Member of the Company from the database.
                responses = (
                    MatchingResponse.objects.prefetch_related("answers")
                    .filter(
                        team_member__is_active=True,
                        team_member__company=company,
                        question=question,
                    )
                    .distinct("team_member_id")
                    .order_by("team_member_id", "-created_at")
                )

                # We filter out blank responses.
                responses = list(
                    filter(lambda response: response.answers.count(), responses)
                )

                # We prepare a list to store the responses' data of this Company.
                company_responses = []

                # We iterate over the Responses to count the frequency of each Answer option.
                for response in responses:
                    # We iterate over each Answer in this Response, as there might be multiple.
                    for value in response.answers.values_list("value", flat=True):
                        # Format the response value (remove "For example" and everything after it)
                        value = format_demographic_response_value(value)

                        # We increment, or initialize, the count of the Answer
                        if entry := next(
                            (
                                entry
                                for entry in company_responses
                                if entry["value"] == value
                            ),
                            None,
                        ):
                            entry["count"] += 1
                        else:
                            company_responses.append({"value": value, "count": 1})

                        # Increment the count in the global answers list
                        if entry := next(
                            (
                                entry
                                for entry in step_data["responses"]
                                if entry["value"] == value
                            ),
                            None,
                        ):
                            entry["count"] += 1
                            total_responses_in_step += 1

                # We calculate the percentage of each Answer for this Company.
                if len(responses):
                    total_responses = len(responses)
                    for item in company_responses:
                        item["percentage"] = item["count"] / total_responses

                # We append the Company's data to the Step's data.
                step_data["companies"].append(
                    {
                        "id": company.id,
                        "name": company.name,
                        "team_members_count": company.teammember_set.filter(
                            is_active=True
                        ).count(),
                        "team_members_with_responses_count": len(responses),
                        "responses": company_responses,
                    }
                )

            # We calculate the percentage of each Answer for this Step.
            if total_responses_in_step:
                for response in step_data["responses"]:
                    response["percentage"] = response["count"] / total_responses_in_step

            # We calculate the total number of companies that have submitted responses.
            step_data["companies_with_responses"] = sum(
                1
                for company in step_data["companies"]
                if company["team_members_with_responses_count"] > 0
            )

            # If not enough companies submitted responses, we omit the data for this step
            if step_data["companies_with_responses"] < self.minimum_companies_per_step:
                step_data["is_locked"] = True
                for company in step_data["companies"]:
                    for response in company["responses"]:
                        response["count"] = 0
                        response["percentage"] = 0
                for response in step_data["responses"]:
                    response["count"] = 0
                    response["percentage"] = 0

            # We append the Step's data to the final response.
            data.append(step_data)

        return Response(data)


class MilestoneProgressBaseView(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        # Retrieve Company List
        try:
            company_list = CompanyList.objects.get(uid=kwargs["uid"])
        except CompanyList.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Collect VIL category names
        categories = dict(
            Category.objects.filter(group__slug="entrepreneurs").values_list(
                "id", "name"
            )
        )
        category_names = list(categories.values())

        # Prepare return data
        data = {
            "companies": [],
            "vil_averages": {
                "start_vil": 0,
                "end_vil": 0,
            },
            "vil_totals": {
                "level": 0,
                "milestones": 0,
            },
        }

        # Iterate over companies
        for company in company_list.companies.all():
            # Prepare company data
            company_data = {}
            # Retrieve assessments
            first_assessment_queryset = (
                Assessment.objects.filter(evaluated=company.id)
                .order_by("created_at")
                .first()
            )
            last_assessment_queryset = (
                Assessment.objects.filter(evaluated=company.id)
                .order_by("-created_at")
                .first()
            )

            if start := request.query_params.get("start"):
                first_assessment_queryset = first_assessment_queryset.filter(
                    created_at__gte=start
                )

            if end := request.query_params.get("end"):
                last_assessment_queryset = last_assessment_queryset.filter(
                    created_at__lte=end
                )

            first_assessment = first_assessment_queryset
            last_assessment = last_assessment_queryset

            # Skip company if no assessments
            if not first_assessment or not last_assessment:
                continue

            # Parse assessments
            first_assessment = self._parse_assessment(categories, first_assessment)
            last_assessment = self._parse_assessment(categories, last_assessment)

            # Add company data
            company_data["company_id"] = company.id
            company_data["company_name"] = company.name
            company_data["first_assessment"] = first_assessment
            company_data["last_assessment"] = last_assessment
            company_data["vil_level_progress"] = (
                last_assessment["vil"] - first_assessment["vil"]
            )
            company_data["milestone_progress"] = (
                last_assessment["milestones"] - first_assessment["milestones"]
            )
            company_data["categories_progress"] = []

            for i, category_name in enumerate(category_names):
                first_level = (
                    first_assessment["levels"][i]["level"]
                    if first_assessment["levels"][i]["level"] is not None
                    else 0
                )
                last_level = (
                    last_assessment["levels"][i]["level"]
                    if last_assessment["levels"][i]["level"] is not None
                    else 0
                )
                milestones = last_level - first_level

                # Create a dictionary for category progress
                company_data["categories_progress"].append(
                    {
                        "name": category_name,
                        "milestones": milestones,
                        "first_assessment_level": first_level,
                        "last_assessment_level": last_level,
                    }
                )

            company_data["max_progress_category"] = max(
                company_data["categories_progress"],
                key=lambda category: category["milestones"],
            )

            # Add values for averages calculation
            data["vil_averages"]["start_vil"] += first_assessment["vil"]
            data["vil_averages"]["end_vil"] += last_assessment["vil"]
            data["vil_totals"]["level"] += company_data["vil_level_progress"]
            data["vil_totals"]["milestones"] += company_data["milestone_progress"]

            # Append company data to return data
            data["companies"].append(company_data)

        # Calculate list progress of each category
        aggregated_progress = {}

        for company in data["companies"]:
            for category in company["categories_progress"]:
                name = category["name"]
                milestones = category["milestones"]
                first_level = category["first_assessment_level"]
                last_level = category["last_assessment_level"]

                if name in aggregated_progress:
                    aggregated_progress[name]["milestones"] += milestones
                    aggregated_progress[name]["first_level"] += first_level
                    aggregated_progress[name]["last_level"] += last_level

                    # Compare individual milestones with recorded largest and least progress
                    if (
                        milestones
                        > aggregated_progress[name]["max_individual_milestones"]
                    ):
                        aggregated_progress[name]["largest_progress"] = {
                            "company_name": company["company_name"],
                            "first_level": first_level,
                            "last_level": last_level,
                        }
                        aggregated_progress[name]["max_individual_milestones"] = (
                            milestones
                        )
                    if (
                        milestones
                        < aggregated_progress[name]["min_individual_milestones"]
                    ):
                        aggregated_progress[name]["least_progress"] = {
                            "company_name": company["company_name"],
                            "first_level": first_level,
                            "last_level": last_level,
                        }
                        aggregated_progress[name]["min_individual_milestones"] = (
                            milestones
                        )
                else:
                    aggregated_progress[name] = {
                        "name": name,
                        "milestones": milestones,
                        "first_level": first_level,
                        "last_level": last_level,
                        "largest_progress": {
                            "company_name": company["company_name"],
                            "first_level": first_level,
                            "last_level": last_level,
                        },
                        "least_progress": {
                            "company_name": company["company_name"],
                            "first_level": first_level,
                            "last_level": last_level,
                        },
                        "max_individual_milestones": milestones,
                        "min_individual_milestones": milestones,
                    }

        for key in aggregated_progress:
            aggregated_progress[key].pop("max_individual_milestones", None)
            aggregated_progress[key].pop("min_individual_milestones", None)

        if len(data["companies"]):
            # Calculate averages
            data["vil_averages"]["start_vil"] /= len(data["companies"])
            data["vil_averages"]["end_vil"] /= len(data["companies"])

            # Add list categories progress data
            data["categories_progress"] = list(aggregated_progress.values())

            max_progress_category = max(
                data["categories_progress"], key=lambda category: category["milestones"]
            )
            lowest_progress_category = min(
                data["categories_progress"], key=lambda category: category["milestones"]
            )

            data["categories_insights"] = {
                "max_progress_category": {
                    "name": max_progress_category["name"],
                    "milestones": max_progress_category["milestones"],
                },
                "lowest_progress_category": {
                    "name": lowest_progress_category["name"],
                    "milestones": lowest_progress_category["milestones"],
                },
            }

            # Add companies insights data
            max_level_company = max(
                data["companies"], key=lambda company: company["vil_level_progress"]
            )
            max_milestones_company = max(
                data["companies"], key=lambda company: company["milestone_progress"]
            )

            data["company_insights"] = {
                "max_vil_level_progress": {
                    "company_name": max_level_company["company_name"],
                    "first_assessment_level": max_level_company["first_assessment"][
                        "vil"
                    ],
                    "last_assessment_level": max_level_company["last_assessment"][
                        "vil"
                    ],
                },
                "max_milestones_progress": {
                    "company_name": max_milestones_company["company_name"],
                    "milestones": max_milestones_company["milestone_progress"],
                },
            }

        return Response(data)

    def _parse_assessment(self, categories, assessment):
        levels = [
            {
                "name": categories[item["category"]],
                "level": item["level"],
            }
            for item in assessment.data
        ]

        return {
            "vil": assessment.level.value,
            "levels": levels,
            "milestones": sum(
                [i["level"] for i in levels if isinstance(i["level"], int)]
            ),
            "date": assessment.created_at,
        }
