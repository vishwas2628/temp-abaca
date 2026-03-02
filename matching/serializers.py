"""
TODO: Move each serializer here into an individual file (when covered by tests)
"""
import os
import io
import settings
from itertools import groupby
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_auth.app_settings import create_token
from rest_auth.models import TokenModel

from allauth.account import app_settings as allauth_settings
from allauth.account.models import EmailAddress
from allauth.utils import get_user_model
from django.db import connection
from django.utils.translation import gettext_lazy as _
from psycopg2.extras import NumericRange
from rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers
from rest_framework.utils import model_meta
from rest_framework.validators import UniqueValidator

from matching.models import (Answer, Criteria, CriteriaWeight, InterestedCTA,
                             Question, QuestionCategory, QuestionType, QuestionBundle,
                             Response, Supporter, SupporterOffering,
                             SupporterOfferingCategories,
                             SupporterOfferingTypes, SupporterType)
from viral.models import (Affiliate, Company, Group, Location, LocationGroup, Network, Sector,
                          UserProfile, AffiliateProgramSupporterSubmission, Subscription, TeamMember)
from viral.serializers import (AffiliateSerializer, AffiliateProgramEntrySerializer,
                               CompanySerializer, GroupSerializer,
                               LocationSerializer, LocationGroupSerializer, SectorSerializer, GooglePlaceSerializer)
from viral.utils import fetch_google_location, run_new_user_webhook
from shared.models import PendingRegistration
from shared.mixins import ConditionalRequiredPerFieldMixin
from shared.validators import AbacaPasswordValidator, JSONSchemaSerializerValidator
from profiles.mixins import UpdateProfileFieldsSerializerMixin

from matching.tests.schemas.criteria_desired_schema import criteria_desired
from matching.tests.schemas.response_value_schema import response_value

from viral.models.company import unique_company_access_hash
from viral.mixins.affiliate_webhook_mixin import AffiliateWebhookMixin


class ResponseSerializerGetData(serializers.ModelSerializer):
    """
    Serializer for a Response
    VERSION: 2
    This is used to get data
    """

    class Meta:
        model = Response
        fields = ("id", "value", "answers")


class ResponseSerializerSubmitData(serializers.ModelSerializer):
    """
    Serializer for a Response
    VERSION: 1
    This is used before to submit data
    """

    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all(), help_text='Question ID')
    team_member = serializers.PrimaryKeyRelatedField(queryset=TeamMember.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Response
        fields = ("question", "value", "user_profile", "answers", "team_member", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")


class QuestionBundleResponseSerializer(serializers.ModelSerializer):
    """
    Serializer for Question Bundle Response
    """
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    team_member = serializers.PrimaryKeyRelatedField(queryset=TeamMember.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Response
        exclude = ("user_profile",)


class AnswerSerializer(serializers.ModelSerializer):
    """
    Serializer for a Answer
    """

    class Meta:
        model = Answer
        fields = ("id", "value", "instructions",)


class QuestionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionType
        fields = ("name", "type", "meta",)


class QuestionCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionCategory
        fields = "__all__"


class QuestionSerializer(serializers.ModelSerializer):
    """
    Serializer for a Question
    """
    answers = AnswerSerializer(source="answer_set", read_only=True, many=True)
    question_type = QuestionTypeSerializer()
    question_category = QuestionCategorySerializer()

    class Meta:
        model = Question
        fields = (
            "id", "entrepreneur_question", "resource_question", "ttl",
            "question_type", "question_category", "answers", "profile_field",
            "short_name", "is_team_member_question", "instructions", "slug",
        )


class QuestionBundleSerializer(serializers.ModelSerializer):
    """
    Serializer for a Question Bundle
    """
    questions = QuestionSerializer(many=True)

    class Meta:
        model = QuestionBundle
        fields = '__all__'


class QuestionBundleResponseWithQuestionSerializer(serializers.Serializer):
    """
    Serializer for a Question Bundle Response with Question & Answers
    """
    value = serializers.JSONField()
    answers = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    question = QuestionSerializer()

    class Meta:
        model = Response


class SupporterTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupporterType
        fields = "__all__"


class SupporterInterestSectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = "__all__"


class SupporterLocationOfInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = "__all__"


class CriteriaWeightSerializer(serializers.ModelSerializer):
    class Meta:
        model = CriteriaWeight
        fields = ('id', 'name', 'value')


class SupporterCompanySerializer(serializers.ModelSerializer):
    locations = LocationSerializer(many=True)

    class Meta:
        model = Company
        fields = '__all__'


class SupporterProfileSerializerWithCompany(serializers.ModelSerializer):
    is_offline = serializers.BooleanField()
    company = SupporterCompanySerializer()

    class Meta:
        model = UserProfile
        fields = '__all__'


class SupporterOfferingTypesSerializer (serializers.ModelSerializer):
    """
    Serializer for a Supporter Offering Types
    """

    class Meta:
        model = SupporterOfferingTypes
        fields = "__all__"


class SupporterOfferingCategoriesSerializer (serializers.ModelSerializer):
    """
    Serializer for a Supporter Offering Categories
    """

    class Meta:
        model = SupporterOfferingCategories
        fields = "__all__"


class SupporterOfferingsSerializer(serializers.ModelSerializer):
    category = SupporterOfferingCategoriesSerializer()
    types = SupporterOfferingTypesSerializer(many=True)

    class Meta:
        model = SupporterOffering
        fields = ('id', 'description', 'category', 'types',)


class SupporterCriteriaSerializer(serializers.ModelSerializer):
    question = QuestionSerializer()
    answers = AnswerSerializer(read_only=True, many=True)
    responses = ResponseSerializerGetData(
        source="get_responses", read_only=True, many=False)

    class Meta:
        model = Criteria
        fields = "__all__"


class SupporterCriteriaAffiliateSerializer(serializers.ModelSerializer):
    """
    Supporter Criteria serializer for Affiliate submissions.
    """
    question = QuestionSerializer()
    answers = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='value'
    )
    criteria_weight = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field='value'
    )

    class Meta:
        model = Criteria
        fields = ('id', 'question', 'desired', 'answers', 'criteria_weight', 'created_at')


class SupporterGroupedSectorsOfInterestSerializer(serializers.Serializer):
    group = GroupSerializer()
    sectors = SectorSerializer(many=True)


class SupporterGroupedLocationsOfInterestSerializer(serializers.Serializer):
    group = LocationGroupSerializer()
    locations = LocationSerializer(many=True)


class SupporterSectorsOfInterestSerializer(serializers.Serializer):
    sectors = serializers.SerializerMethodField()
    grouped_sectors = serializers.SerializerMethodField()

    def get_sectors(self, supporter):
        # Sectors selected by the user without an explicit group
        ungrouped_sectors = supporter.sectors_of_interest.filter(
            group__isnull=True)
        sectors_of_interest = [
            sector_of_interest.sector for sector_of_interest in ungrouped_sectors]
        serializer = SupporterInterestSectorSerializer(
            sectors_of_interest, many=True)
        return serializer.data

    def get_grouped_sectors(self, supporter):
        # Sectors selected by the user inside a group
        sectors_with_groups = supporter.sectors_of_interest.exclude(
            group__isnull=True)
        sector_groups = sectors_with_groups.distinct('group__id')
        grouped_sectors = []
        for group_of_interest in sector_groups:
            group_sectors = sectors_with_groups.filter(
                group=group_of_interest.group)
            sectors_of_interest = [
                sector_of_interest.sector for sector_of_interest in group_sectors]
            grouped_sectors.append({
                'group': group_of_interest.group,
                'sectors': sectors_of_interest
            })
        serializer = SupporterGroupedSectorsOfInterestSerializer(
            grouped_sectors, many=True)
        return serializer.data


class SupporterLocationsOfInterestSerializer(serializers.Serializer):
    locations = serializers.SerializerMethodField()
    grouped_locations = serializers.SerializerMethodField()

    def get_locations(self, supporter):
        # Locations selected by the user through Google Places
        ungrouped_locations = supporter.locations_of_interest.filter(
            group__isnull=True)
        locations_of_interest = [
            location_of_interest.location for location_of_interest in ungrouped_locations]
        serializer = SupporterLocationOfInterestSerializer(
            locations_of_interest, many=True)
        return serializer.data

    def get_grouped_locations(self, supporter):
        # Locations selected by the user inside a group
        locations_with_groups = supporter.locations_of_interest.exclude(
            group__isnull=True)
        location_groups = locations_with_groups.distinct('group__id')
        grouped_locations = []
        for group_of_interest in location_groups:
            group_locations = locations_with_groups.filter(
                group=group_of_interest.group)
            locations_of_interest = [
                location_of_interest.location for location_of_interest in group_locations]
            grouped_locations.append({
                'group': group_of_interest.group,
                'locations': locations_of_interest
            })
        serializer = SupporterGroupedLocationsOfInterestSerializer(
            grouped_locations, many=True)
        return serializer.data


class SupporterSerializer(serializers.ModelSerializer):
    """
    Serializer responsible for dealing with
    supporter data used for outputting model instances.

    TODO: Migrate sectors serializer to grouped_sectors
    """
    user_profile = SupporterProfileSerializerWithCompany()
    types = SupporterTypeSerializer(many=True)
    sectors = serializers.SerializerMethodField()
    grouped_sectors = serializers.SerializerMethodField()
    locations = serializers.SerializerMethodField()
    grouped_locations = serializers.SerializerMethodField()
    offerings = SupporterOfferingsSerializer(
        source="get_offers_with_prefetch", read_only=True, many=True)
    criteria = SupporterCriteriaSerializer(
        source="get_criteria_with_prefetch", read_only=True, many=True)
    investing_level_range = serializers.SerializerMethodField()

    class Meta:
        model = Supporter
        fields = ("id", "name", "about", "email", "investing_level_range", "locations_weight", "sectors_weight",
                  "level_weight", "user_profile", "types", "grouped_sectors", "sectors", "locations",
                  "grouped_locations", "offerings", "criteria")

    def get_investing_level_range(self, supporter):
        return [supporter.investing_level_range.lower, supporter.investing_level_range.upper]

    def get_sectors(self, supporter):
        # Sectors selected by the user without an explicit group
        ungrouped_sectors = supporter.sectors_of_interest.filter(
            group__isnull=True)
        sectors_of_interest = [
            sector_of_interest.sector for sector_of_interest in ungrouped_sectors]
        serializer = SupporterInterestSectorSerializer(
            sectors_of_interest, many=True)
        return serializer.data

    def get_grouped_sectors(self, supporter):
        # Sectors selected by the user inside a group
        sectors_with_groups = supporter.sectors_of_interest.exclude(
            group__isnull=True)
        sector_groups = sectors_with_groups.distinct('group__id')
        grouped_sectors = []
        for group_of_interest in sector_groups:
            group_sectors = sectors_with_groups.filter(
                group=group_of_interest.group)
            sectors_of_interest = [
                sector_of_interest.sector for sector_of_interest in group_sectors]
            grouped_sectors.append({
                'group': group_of_interest.group,
                'sectors': sectors_of_interest
            })
        serializer = SupporterGroupedSectorsOfInterestSerializer(
            grouped_sectors, many=True)
        return serializer.data

    def get_locations(self, supporter):
        # Locations selected by the user through Google Places
        ungrouped_locations = supporter.locations_of_interest.filter(
            group__isnull=True)
        locations_of_interest = [
            location_of_interest.location for location_of_interest in ungrouped_locations]
        serializer = SupporterLocationOfInterestSerializer(
            locations_of_interest, many=True)
        return serializer.data

    def get_grouped_locations(self, supporter):
        # Locations selected by the user inside a group
        locations_with_groups = supporter.locations_of_interest.exclude(
            group__isnull=True)
        location_groups = locations_with_groups.distinct('group__id')
        grouped_locations = []
        for group_of_interest in location_groups:
            group_locations = locations_with_groups.filter(
                group=group_of_interest.group)
            locations_of_interest = [
                location_of_interest.location for location_of_interest in group_locations]
            grouped_locations.append({
                'group': group_of_interest.group,
                'locations': locations_of_interest
            })
        serializer = SupporterGroupedLocationsOfInterestSerializer(
            grouped_locations, many=True)
        return serializer.data


class RetrieveSupporterSerializer(serializers.Serializer):
    """
    An optimized version of the SupporterSerializer

    TODO: Check if having a depth of nested serializers greater than 3
    is really required to avoid performance bottlenecks.
    """
    user_profile = SupporterProfileSerializerWithCompany()
    types = SupporterTypeSerializer(many=True)
    investing_level_range = serializers.SerializerMethodField()
    offerings = serializers.SerializerMethodField()
    criteria = serializers.SerializerMethodField()
    sectors = serializers.SerializerMethodField()
    grouped_sectors = serializers.SerializerMethodField()
    locations = serializers.SerializerMethodField()
    grouped_locations = serializers.SerializerMethodField()

    def get_investing_level_range(self, supporter):
        return [supporter.investing_level_range.lower, supporter.investing_level_range.upper]

    def get_offerings(self, supporter):
        offerings = SupporterOfferingsSerializer(supporter.supporteroffering_set, many=True)
        return offerings.data

    def get_criteria(self, supporter):
        criteria = SupporterCriteriaSerializer(supporter.criteria_set, many=True)
        return criteria.data

    def get_sectors(self, supporter):
        # Sectors selected by the user without an explicit group
        ungrouped_sectors = supporter.ungrouped_sectors if hasattr(supporter, 'ungrouped_sectors') \
            else list(supporter.sectors_of_interest.filter(group__isnull=True))
        sectors_of_interest = [
            sector_of_interest.sector for sector_of_interest in ungrouped_sectors]
        serializer = SupporterInterestSectorSerializer(
            sectors_of_interest, many=True)
        return serializer.data

    def get_grouped_sectors(self, supporter):
        # Sectors selected by the user inside a group
        sectors_with_groups = supporter.grouped_sectors if hasattr(supporter, 'grouped_sectors') \
            else list(supporter.sectors_of_interest.prefetch_related('sector__groups')
                      .exclude(group__isnull=True))
        grouped_sectors = []
        for sectors_by_group in groupby(sectors_with_groups, lambda sector_group: sector_group.group):
            grouped_sectors.append({
                'group': sectors_by_group[0],
                'sectors': [sector_of_interest.sector for sector_of_interest in sectors_by_group[1]],
            })
        serializer = SupporterGroupedSectorsOfInterestSerializer(
            grouped_sectors, many=True)
        return serializer.data

    def get_locations(self, supporter):
        # Locations selected by the user through Google Places
        ungrouped_locations = supporter.ungrouped_locations if hasattr(supporter, 'ungrouped_locations') \
            else list(supporter.locations_of_interest.filter(group__isnull=True))
        locations_of_interest = [
            location_of_interest.location for location_of_interest in ungrouped_locations]
        serializer = SupporterLocationOfInterestSerializer(
            locations_of_interest, many=True)
        return serializer.data

    def get_grouped_locations(self, supporter):
        # Locations selected by the user inside a group
        locations_with_groups = supporter.grouped_locations if hasattr(supporter, 'grouped_locations') \
            else list(supporter.locations_of_interest.exclude(group__isnull=True))
        grouped_locations = []
        for locations_by_group in groupby(locations_with_groups, lambda location_group: location_group.group):
            grouped_locations.append({
                'group': locations_by_group[0],
                'locations': [location_of_interest.location for location_of_interest in locations_by_group[1]],
            })
        serializer = SupporterGroupedLocationsOfInterestSerializer(
            grouped_locations, many=True)
        return serializer.data

    class Meta:
        model = Supporter
        fields = ("id", "name", "about", "email", "investing_level_range", "locations_weight", "sectors_weight",
                  "level_weight", "user_profile", "types", "grouped_sectors", "sectors", "locations",
                  "grouped_locations", "offerings", "criteria")


class MatchingSerializer(serializers.Serializer):
    """
    Serializer for the matching response.

    TODO: Improve SupporterSerializer performance for reversed relations (Criteria <=> Responses)
    """

    supporter = SupporterSerializer()
    score = serializers.FloatField(required=True)


class MatchingSupportersSerializer(serializers.Serializer):
    """
    Serializer for the matching response.
    """

    company = CompanySerializer()
    score = serializers.FloatField(required=True)
    level = serializers.IntegerField()


class MatchingSupportersAffiliateSerializer(serializers.Serializer):
    """
    Serializer for the matching response.
    """

    company = CompanySerializer()
    affiliates = AffiliateProgramEntrySerializer(many=True)
    score = serializers.FloatField(required=True)
    level = serializers.IntegerField()
    milestone_planner = serializers.SerializerMethodField()

    def get_milestone_planner(self, result):
        if milestone_planner := result['company'].milestone_planners.first():
            is_invited_user = milestone_planner.invited_users.filter(id=self.context['supporter'].user_profile.id).exists()
            return milestone_planner.uid if is_invited_user else None
        return None


class CreateSupporterCompanySerializer(serializers.ModelSerializer):
    location = LocationSerializer()
    networks = serializers.PrimaryKeyRelatedField(
        queryset=Network.objects.all(), many=True)

    class Meta:
        model = Company
        fields = ('name', 'location', 'networks', 'website')

    def create(self, validated_data):
        company_hash = os.urandom(5).hex()
        company = Company.objects.create(
            name=validated_data['name'], website=validated_data['website'], type=1, access_hash=company_hash)
        location = Location.objects.create(**validated_data.get('location'))
        company.locations.add(location)
        networks = validated_data['networks']
        company.networks.set(networks)
        return company


class GroupedSectorsSerializer(serializers.Serializer):
    group = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all())
    sectors = serializers.PrimaryKeyRelatedField(
        queryset=Sector.objects.all(), many=True)

    def validate(self, data):
        """
        Check that all sectors belong to the same group.
        """
        sector_ids = [sector.id for sector in data['sectors']]
        group_sectors = data['group'].sectors.filter(pk__in=sector_ids)

        if len(sector_ids) != len(group_sectors):
            raise serializers.ValidationError(
                "Sector(s) does not belong to Group")
        return data


class GroupedLocationsSerializer(serializers.Serializer):
    group = serializers.PrimaryKeyRelatedField(
        queryset=LocationGroup.objects.all())
    locations = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(), many=True)

    def validate(self, data):
        """
        Check that all locations belong to the same group.
        """
        location_ids = [location.id for location in data['locations']]
        group_locations = data['group'].locations.filter(pk__in=location_ids)

        if len(location_ids) != len(group_locations):
            raise serializers.ValidationError(
                "Location(s) does not belong to Group")
        return data


class SupporterInvestingLevelRangeField(serializers.Field):
    def to_representation(self, value):
        return [value.lower, value.upper]

    def to_internal_value(self, value):
        # Validate range
        if type(value) != list:
            raise serializers.ValidationError("Invalid investing level range")

        # Set as a unique valued range
        unique_range = set()
        value = [x for x in value if x not in unique_range and (
            unique_range.add(x) or True)]

        # Convert to a numeric range
        return NumericRange(*value)


class SupporterDataSerializer(serializers.Serializer):
    name = serializers.CharField()
    types = serializers.PrimaryKeyRelatedField(
        queryset=SupporterType.objects.all(), many=True)
    otherType = serializers.CharField(required=False, allow_null=True)
    sectors = serializers.PrimaryKeyRelatedField(
        queryset=Sector.objects.all(), many=True, required=False)
    grouped_sectors = GroupedSectorsSerializer(many=True, required=False)
    locations = GroupedLocationsSerializer(many=True, required=False)
    places = serializers.ListField(
        child=serializers.CharField(), required=False)
    investing_level_range = SupporterInvestingLevelRangeField()


class CreateSupporterSerializer(RegisterSerializer):
    email = serializers.EmailField(required=allauth_settings.EMAIL_REQUIRED, validators=[UniqueValidator(
        queryset=get_user_model().objects.values('email'), lookup='iexact')])
    company = CreateSupporterCompanySerializer()
    affiliate = serializers.PrimaryKeyRelatedField(
        queryset=Affiliate.objects.all())
    supporter = SupporterDataSerializer()

    def _create_user(self):
        self.user = super(CreateSupporterSerializer, self).save(self.request)

    def _create_company(self):
        validated_company = self.validated_data.pop('company')
        self.company = CreateSupporterCompanySerializer.create(
            CreateSupporterCompanySerializer(), validated_data=validated_company)
        self.company.email = self.user.email
        self.company.save()

    def _create_user_profile(self):
        validated_affiliate = self.validated_data.pop('affiliate')
        self.user_profile = UserProfile.objects.create(
            user=self.user, company=self.company, source=validated_affiliate)

    def _create_supporter(self):
        supporter_data = dict(self.validated_data.pop('supporter'))

        # Create Supporter
        self.supporter = Supporter.objects.create(
            name=supporter_data['name'], email=self.user.email,
            user_profile=self.user_profile, investing_level_range=supporter_data[
                'investing_level_range']
        )

        # Set Supporter Types
        self.supporter.types.set(supporter_data['types'])
        if 'otherType' in supporter_data and supporter_data['otherType']:
            newType = SupporterType.objects.create(
                name=supporter_data['otherType'])
            self.supporter.types.add(newType)

        # Set Supporter Sectors
        if 'sectors' in supporter_data:
            self.supporter.sectors.set(supporter_data['sectors'])

        if 'grouped_sectors' in supporter_data:
            for grouped_sectors in reversed(supporter_data['grouped_sectors']):
                grouped_sectors = dict(grouped_sectors)
                sectors = grouped_sectors['sectors']
                group = Group.objects.get(
                    pk=grouped_sectors['group'].pk)
                self.supporter.sectors.add(*sectors, through_defaults={
                    'group': group, 'supporter': self.supporter})

        # Set Supporter Locations
        if 'locations' in supporter_data:
            for grouped_locations in reversed(supporter_data['locations']):
                grouped_locations = dict(grouped_locations)
                locations = grouped_locations['locations']
                group = LocationGroup.objects.get(
                    pk=grouped_locations['group'].pk)
                self.supporter.locations.add(*locations, through_defaults={
                    'group': group, 'supporter': self.supporter})

        if 'places' in supporter_data:
            for place in supporter_data['places']:
                found_result = fetch_google_location(place_id=place)

                if found_result:
                    serialized_place = GooglePlaceSerializer(found_result[0])
                    location = Location.objects.create(**serialized_place.data)
                    self.supporter.locations.add(location)

    def save(self, request):
        self.request = request
        self._create_user()
        self._create_company()
        self._create_user_profile()
        self._create_supporter()

        if self.user_profile:
            run_new_user_webhook("New user registration", self.user_profile)
        
        return {
            'user': self.user,
            'company': self.company,
            'supporter': self.supporter
        }


class SupporterOfferingCreatorSerializer(serializers.ModelSerializer):
    description = serializers.CharField(allow_blank=True)
    category = serializers.PrimaryKeyRelatedField(
        queryset=SupporterOfferingCategories.objects.all(), many=False,)
    supporter = serializers.PrimaryKeyRelatedField(
        queryset=Supporter.objects.all(), many=False,)

    class Meta(object):
        model = SupporterOffering
        fields = "__all__"

    def create(self, validated_data):
        supporter_id = validated_data.get('supporter')
        description = validated_data.get('description')
        category = validated_data.get(
            'category')

        newOffering = SupporterOffering.objects.create(
            description=description, category=category, supporter=supporter_id)

        return newOffering


class SupporterInterestLocationSerializerField(serializers.Field):
    def to_representation(self, locations):
        return SupporterLocationOfInterestSerializer(locations, many=True).data

    def to_internal_value(self, selected_locations):
        validated_locations = GroupedLocationsSerializer(
            data=selected_locations, many=True)
        validated_locations.is_valid(raise_exception=True)
        return validated_locations.data


class UpdateSupporterSerializer(serializers.ModelSerializer):
    """
    Serializer responsible for dealing with
    supporter data used for updating the model.

    Notes:
    -> (group_sectors) was introduced to avoid
       breaking existing integrations that rely
       on the current (sectors) serializer.

    -> Since we have two ways of populating sectors,
       both (sectors) and (grouped_sectors) are optional.

    TODO: Migrate sectors and locations payload to a single uniform payload
    that would drop the custom (Google) places attribute.
    """
    types = serializers.PrimaryKeyRelatedField(
        queryset=SupporterType.objects.all(), many=True)
    grouped_sectors = GroupedSectorsSerializer(
        many=True, required=False)
    sectors = serializers.PrimaryKeyRelatedField(
        queryset=Sector.objects.all(), many=True, required=False)
    grouped_locations = GroupedLocationsSerializer(many=True, required=False)
    # For updating single Locations:
    locations = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(), many=True, required=False)
    # For creating single Locations:
    places = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = Supporter
        fields = ('name', 'about', 'email', 'types', 'grouped_locations', 'locations', 'places', 'locations_weight',
                  'grouped_sectors', 'sectors', 'sectors_weight', 'investing_level_range', 'level_weight')

    def update(self, instance, validated_data):
        if not len(validated_data.get('sectors', [])):
            # If empty, remove related sectors
            for sector in instance.sectors_of_interest.filter(group__isnull=True):
                sector.delete()

        if not len(validated_data.get('locations', [])):
            # If empty, delete user-unique locations
            for location in instance.locations.filter(groups__isnull=True):
                location.delete()

        # Dynamic model attributes' update:
        info = model_meta.get_field_info(instance)
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                field = getattr(instance, attr)
                field.set(value)
            else:
                setattr(instance, attr, value)

        if 'grouped_locations' in validated_data:
            locations = validated_data.pop('grouped_locations')
            for grouped_locations in reversed(locations):
                grouped_locations = dict(grouped_locations)
                locations = grouped_locations['locations']
                group = grouped_locations['group']
                instance.locations.add(*locations, through_defaults={
                    'group': group, 'supporter': instance})
        else:
            # Delete old related locations
            for location in instance.locations.filter(groups__isnull=False):
                instance.locations.remove(location)

        # Add new related grouped sectors
        if 'grouped_sectors' in validated_data:
            grouped_sectors_list = validated_data.pop('grouped_sectors')
            for grouped_sectors in reversed(grouped_sectors_list):
                instance.sectors.add(*grouped_sectors['sectors'], through_defaults={
                                     'group': grouped_sectors['group'], 'supporter': instance})
        else:
            # Delete old related grouped sectors
            for sector in instance.sectors_of_interest.filter(group__isnull=False):
                sector.delete()

        if 'otherType' in self.initial_data:
            otherType = self.initial_data['otherType']
            new_type = SupporterType.objects.create(name=otherType)
            instance.types.add(new_type)

        if 'places' in validated_data:
            places = validated_data.pop('places')
            for place in places:
                found_result = fetch_google_location(place_id=place)

                if found_result:
                    serialized_place = GooglePlaceSerializer(found_result[0])
                    location = Location.objects.create(**serialized_place.data)
                    instance.locations.add(location)

        instance.save()

        return instance


class UpdateSupporterOfferingSerializer(serializers.ModelSerializer):
    category = SupporterOfferingCategoriesSerializer
    types = SupporterOfferingTypesSerializer

    class Meta:
        model = SupporterOffering
        fields = ('description', 'category',
                  'types')

    def partial_update(self, instance, validated_data):
        if 'category' in validated_data:
            category = SupporterOfferingCategories.objects.create(
                **validated_data.pop('category'))
            instance.types.add(category)
        if 'types' in validated_data:
            types = SupporterOfferingTypes.objects.create(
                **validated_data.pop('types'))
            instance.locations.add(types)

        info = model_meta.get_field_info(instance)
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                field = getattr(instance, attr)
                field.set(value)
            else:
                setattr(instance, attr, value)
        instance.save()

        return instance


class MatchingCriteriaBySupporterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Criteria
        exclude = ('answers', 'created_at', 'updated_at')


class MatchingCreateOrUpdateCriteriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Criteria
        fields = ("name", "desired", "criteria_weight",
                  "supporter", "question", "answers", "is_active")


class QuestionForAdditionalCriteriaSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(source="answer_set", read_only=True, many=True)
    question_type = QuestionTypeSerializer()

    class Meta:
        model = Question
        fields = ("id", "is_common", "short_name", "question_type",
                  "entrepreneur_question", "resource_question", "answers")


class MatchingQuestionsForAdditionalCriteriaSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()

    def get_questions(self, question_category):
        serialized_questions = QuestionForAdditionalCriteriaSerializer(question_category.question_set, many=True)
        return serialized_questions.data

    class Meta:
        model = QuestionCategory
        fields = ("name", "description", "questions")


class InterestedCTASerializer(serializers.ModelSerializer):
    class Meta:
        model = InterestedCTA
        fields = '__all__'


class SupporterCreateEntrepreneurLinkSerializer(serializers.Serializer):
    slug = serializers.SlugField(max_length=50)

    default_error_messages = {
        'already_exists': _("This slug is already taken."),
    }

    def validate_slug(self, value):
        """
        Check that the slug does not yet exist.
        """
        if Affiliate.objects.filter(slug=value).exists():
            raise serializers.ValidationError(
                self.default_error_messages['already_exists'], code='already_exists',)
        return value


class PendingRegistrationSerializer(ConditionalRequiredPerFieldMixin, serializers.Serializer):
    """
    The base serializer for pending registrations.

    For the first request it will generate the token
    that needs to be used for all upcoming requests.
    """
    token = serializers.CharField(required=False, help_text='Generated token that gets returned after a request.')
    affiliate = serializers.PrimaryKeyRelatedField(required=False, queryset=Affiliate.objects.all())

    # References the current registration
    pending_registration = None

    ERROR_MISSING_DATA = 'missing_data'
    ERROR_UNIQUE = 'unique'
    ERROR_INVALID_TOKEN = 'invalid_token'

    default_error_messages = {
        ERROR_MISSING_DATA: _("Missing data."),
        ERROR_UNIQUE: _("This field must be unique."),
        ERROR_INVALID_TOKEN: _("Invalid token."),
    }

    def _has_request_field(self, field):
        return hasattr(self, 'initial_data') and bool(self.initial_data.get(field, None))

    def _get_default_affiliate(self):
        """
        This needs to be provided by the serializer(s)
        that will inherit this base class to specify
        if there's a default Affiliate
        """
        pass

    def _set_pending_registration(self, token):
        self.pending_registration = PendingRegistration.objects.select_related(
            'user', 'affiliate').prefetch_related('user__emailaddress_set').get(uid=token)

    def validate_token(self, value):
        if not PendingRegistration.objects.filter(uid=value).exists():
            self.fail(self.ERROR_INVALID_TOKEN)

        return value

    def update(self, validated_data):
        """
        This needs to be overriden by the serializer(s)
        that will inherit this base class
        """
        pass

    def create_or_update(self, validated_data):
        if self._has_request_field('token'):
            token = validated_data.get('token')
            has_data_to_update = len(validated_data) > 1
            self._set_pending_registration(token)

            if has_data_to_update:
                self.update(validated_data)
                return {'token': validated_data.get('token')}
            else:
                self.fail(self.ERROR_MISSING_DATA)
        else:
            affiliate = validated_data.get('affiliate', None) or self._get_default_affiliate()
            pending_email = validated_data.get('email')

            # Create User account
            user = get_user_model().objects.create_user(
                username=pending_email, email=pending_email)
            EmailAddress.objects.create(user=user, email=pending_email, primary=True)

            pending_registration = PendingRegistration.objects.create(user=user, affiliate=affiliate)

            if not hasattr(user, 'auth_token'):
                create_token(TokenModel, user, None)

            return {
                'token': pending_registration.uid,
                'auth_token': user.auth_token.key
            }


class PendingSupporterEmailSerializer(PendingRegistrationSerializer):
    email = serializers.EmailField(required=False, validators=[UniqueValidator(
        queryset=get_user_model().objects.values('email'), lookup='iexact')])

    def is_email_required(self):
        return not self._has_request_field('token')

    def update(self, validated_data):
        super().update(validated_data)
        pending_email = validated_data.get('email', None)

        if pending_email and pending_email != self.pending_registration.user.email:
            # Update username since it's based on the email
            self.pending_registration.user.email = pending_email
            self.pending_registration.user.username = pending_email
            self.pending_registration.user.save()
            # Change the email on the account manually without .change() to skip verification email
            current_email = self.pending_registration.user.emailaddress_set.first()
            current_email.email = pending_email
            current_email.verified = True
            current_email.primary = True
            current_email.save()


class PendingSupporterPasswordSerializer(PendingRegistrationSerializer):
    password1 = serializers.CharField(required=False, min_length=8, validators=[AbacaPasswordValidator()])
    password2 = serializers.CharField(required=False)

    ERROR_PASSWORD_MISMATCH = 'password_mismatch'
    ERROR_PASSWORD_MISSING_CONFIRMATION = 'password_missing_confirmation'

    default_error_messages = {
        ERROR_PASSWORD_MISMATCH: _("Password confirmation failed."),
        ERROR_PASSWORD_MISSING_CONFIRMATION: _("Missing password confirmation."),
    }

    @property
    def has_password_and_confirmation(self):
        return self._has_request_field('password1') and self._has_request_field('password2')

    def validate(self, attrs):
        super().validate(attrs)
        password1 = attrs.get('password1', None)
        password2 = attrs.get('password2', None)

        if password1 or password2:
            if not password2:
                self.fail(self.ERROR_PASSWORD_MISSING_CONFIRMATION)
            elif password1 != password2:
                self.fail(self.ERROR_PASSWORD_MISMATCH)

        return attrs

    def update(self, validated_data):
        super().update(validated_data)

        if self.has_password_and_confirmation:
            new_password = validated_data.get('password1')
            self.pending_registration.user.set_password(new_password)
            self.pending_registration.user.save()


class SupporterCompanySubmissionSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    type = serializers.HiddenField(default=Company.SUPPORTER)
    access_hash = serializers.HiddenField(default=unique_company_access_hash)
    location = LocationSerializer()
    networks = serializers.PrimaryKeyRelatedField(required=False, queryset=Network.objects.all(), many=True)

    def create(self, validated_company):
        # Create new location
        company_location = validated_company.pop('location')
        new_location = Location.objects.create(**company_location)

        created_company = super().create(validated_company)
        created_company.locations.add(new_location)
        created_company.save()
        return created_company

    def update(self, instance, validated_company):
        company_location = validated_company.pop('location', None)

        if company_location:
            # Delete previous location
            instance.locations.clear()
            # Create new location
            new_location = Location.objects.create(**company_location)

        updated_company = super().update(instance, validated_company)
        updated_company.locations.add(new_location)
        updated_company.save()
        return updated_company

    class Meta:
        model = Company
        fields = ('name', 'type', 'access_hash', 'location', 'networks')


class SupporterSubmissionSerializer(serializers.ModelSerializer):
    types = serializers.PrimaryKeyRelatedField(queryset=SupporterType.objects.all(), many=True, required=False)
    other_type = serializers.CharField(allow_null=True, required=False)
    investing_level_range = SupporterInvestingLevelRangeField()
    # Defaults to None as assignment should occur upon calling the .create() method
    name = serializers.HiddenField(default=serializers.CreateOnlyDefault(None))
    user_profile = serializers.HiddenField(default=serializers.CreateOnlyDefault(None))

    # Sectors of Interest
    sectors = serializers.PrimaryKeyRelatedField(queryset=Sector.objects.all(), many=True, required=False)
    grouped_sectors = GroupedSectorsSerializer(many=True, required=False)

    # Locations of Interest
    locations = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all(), many=True, required=False)
    grouped_locations = GroupedLocationsSerializer(many=True, required=False)
    # For creating single Locations:
    places = serializers.ListField(child=serializers.CharField(), required=False)

    ERROR_MISSING_SUPPORTER_TYPES = 'missing_supporter_types'

    default_error_messages = {
        ERROR_MISSING_SUPPORTER_TYPES: _("Missing Supporter types."),
    }

    def _add_other_type(self, validated_supporter, instance=None):
        other_type = validated_supporter.pop('other_type', None)

        if not other_type:
            return validated_supporter

        is_new_type = not instance.types.filter(name__icontains=other_type).exists() if instance else True

        if is_new_type:
            new_type = SupporterType.objects.create(name=other_type)
            validated_supporter['types'].append(new_type.pk)

        return validated_supporter

    def _set_grouped_sectors(self, supporter, grouped_sectors_list=None):
        if grouped_sectors_list:
            for grouped_sectors in reversed(grouped_sectors_list):
                grouped_sectors = dict(grouped_sectors)
                sectors = grouped_sectors['sectors']
                group = grouped_sectors['group']
                supporter.sectors.add(*sectors, through_defaults={
                    'group': group, 'supporter': supporter})
        return supporter

    def _set_grouped_locations(self, supporter, grouped_locations_list=None):
        # Remove old grouped locations
        for location in supporter.locations.exclude(groups=None):
            supporter.locations.remove(location)

        if grouped_locations_list:
            for grouped_locations in reversed(grouped_locations_list):
                grouped_locations = dict(grouped_locations)
                locations = grouped_locations['locations']
                group = grouped_locations['group']
                supporter.locations.add(*locations, through_defaults={
                    'group': group, 'supporter': supporter})
        return supporter

    def _set_locations_from_google(self, supporter, places_list=None):
        # If no incoming changes, skip the rest
        if places_list is None:
            return supporter

        # Add new locations
        for place in places_list:
            found_result = fetch_google_location(place_id=place)

            if found_result:
                serialized_place = GooglePlaceSerializer(found_result[0])
                location = Location.objects.create(**serialized_place.data)
                supporter.locations.add(location)

        return supporter

    def _remove_previous_interests(self, instance, validated_data):
        if not len(validated_data.get('sectors', [])):
            for sector in instance.sectors_of_interest.filter(group__isnull=True):
                sector.delete()

        if not len(validated_data.get('locations', [])):
            for location in instance.locations.filter(groups__isnull=True):
                location.delete()

    def create(self, validated_supporter):
        # Assign pre-existing data
        validated_supporter['name'] = self.context['name']
        validated_supporter['email'] = self.context['email']
        validated_supporter['user_profile'] = self.context['user_profile']
        validated_supporter['is_active'] = self.context['is_active'] if 'is_active' in self.context else True

        # Create other type before assigning it to the Supporter
        validated_supporter = self._add_other_type(validated_supporter)

        # Strip extra fields from the validated data before creating the Supporter
        validated_group_sectors = validated_supporter.pop('grouped_sectors', None)
        validated_locations = validated_supporter.pop('grouped_locations', None)
        validated_places = validated_supporter.pop('places', None)

        # Create Supporter and its Sectors and Locations of Interest
        created_supporter = super().create(validated_supporter)
        created_supporter = self._set_grouped_sectors(created_supporter, validated_group_sectors)
        created_supporter = self._set_grouped_locations(created_supporter, validated_locations)
        created_supporter = self._set_locations_from_google(created_supporter, validated_places)

        return created_supporter

    def update(self, instance, validated_supporter):
        # Assign pre-existing data
        validated_supporter['name'] = instance.user_profile.company.name if instance.user_profile else instance.email
        validated_supporter['email'] = instance.user_profile.user.email if instance.user_profile else instance.email
        validated_supporter['user_profile'] = instance.user_profile

        # Create other type before assigning it to the Supporter
        validated_supporter = self._add_other_type(validated_supporter)

        # Strip extra fields from the validated data before updating the Supporter
        validated_group_sectors = validated_supporter.pop('grouped_sectors', None)
        validated_locations = validated_supporter.pop('grouped_locations', None)
        validated_places = validated_supporter.pop('places', None)

        # Remove previous sectors & locations
        self._remove_previous_interests(instance, validated_supporter)

        # Update Supporter and its Sectors and Locations of Interest
        updated_supporter = super().update(instance, validated_supporter)
        updated_supporter = self._set_grouped_locations(updated_supporter, validated_locations)
        updated_supporter = self._set_locations_from_google(updated_supporter, validated_places)
        updated_supporter = self._set_grouped_sectors(updated_supporter, validated_group_sectors)

        return updated_supporter

    class Meta:
        model = Supporter
        fields = ('name', 'types', 'other_type', 'investing_level_range',
                  'grouped_sectors', 'sectors', 'grouped_locations', 'locations', 'places', 'user_profile')


class PendingSupporterDataSerializer(PendingRegistrationSerializer):
    supporter = SupporterSubmissionSerializer(required=False)
    company = SupporterCompanySubmissionSerializer(required=False)

    @property
    def has_company_data(self):
        return self._has_request_field('company')

    @property
    def has_supporter_data(self):
        return self._has_request_field('supporter')

    def _create_or_update_submission(self, supporter):
        submission, created = AffiliateProgramSupporterSubmission.objects.get_or_create(
            affiliate=self.pending_registration.affiliate, supporter=supporter)
        submission.investing_level_range = supporter.investing_level_range
        # Convert sectors & locations to JSON
        submission.sectors_of_interest = SupporterSectorsOfInterestSerializer(supporter).data
        submission.locations_of_interest = SupporterLocationsOfInterestSerializer(supporter).data
        submission.save()
        return submission

    def _update_existing_supporter(self, validated_data):
        supporter = Supporter.objects.select_related('user_profile').prefetch_related('user_profile__company').get(
            user_profile__user=self.pending_registration.user)

        if self.has_company_data:
            SupporterCompanySubmissionSerializer.update(
                SupporterCompanySubmissionSerializer(),
                supporter.user_profile.company,
                validated_data.get('company'))

        if self.has_supporter_data:
            existing_supporter = SupporterSubmissionSerializer.update(
                SupporterSubmissionSerializer(),
                supporter, validated_data.get('supporter'))
            self._create_or_update_submission(existing_supporter)

    def _create_supporter(self, validated_data):
        company = SupporterCompanySubmissionSerializer.create(
            SupporterCompanySubmissionSerializer(),
            validated_data.get('company'))
        user_profile = self._create_user_profile(self.pending_registration.user, company)
        created_supporter = SupporterSubmissionSerializer.create(
            SupporterSubmissionSerializer(
                context={
                    'name': company.name,
                    'email': self.pending_registration.user.email,
                    'user_profile': user_profile
                }),
            validated_data.get('supporter'))
        self._create_or_update_submission(created_supporter)

    def _create_or_update_inactive_supporter(self, validated_data):
        inactive_supporter = self._get_supporter()
        was_created = False

        if inactive_supporter:
            if self.has_company_data:
                # Create its company and assign a user_profile
                company = SupporterCompanySubmissionSerializer.create(
                    SupporterCompanySubmissionSerializer(),
                    validated_data.get('company'))
                user_profile = self._create_user_profile(self.pending_registration.user, company)
                inactive_supporter.user_profile = user_profile
                inactive_supporter.is_active = True
                inactive_supporter.save()

                if user_profile:
                    run_new_user_webhook("New user registration", user_profile)

            if self.has_supporter_data:
                inactive_supporter = SupporterSubmissionSerializer.update(
                    SupporterSubmissionSerializer(context={'is_active': False}),
                    inactive_supporter, validated_data.get('supporter'))
                self._create_or_update_submission(inactive_supporter)
        elif self.has_supporter_data:
            was_created = True
            supporter_name = supporter_email = self.pending_registration.user.email

            # Create an inactive Supporter
            inactive_supporter = SupporterSubmissionSerializer.create(
                SupporterSubmissionSerializer(
                    context={
                        'name': supporter_name,
                        'email': supporter_email,
                        'user_profile': None
                    }),
                validated_data.get('supporter'))
            self._create_or_update_submission(inactive_supporter)

        return inactive_supporter, was_created

    def update(self, validated_data):
        super().update(validated_data)

        if self._is_existing_supporter(with_user_profile=True):
            self._update_existing_supporter(validated_data)
        elif self._is_detached_submission():
            self._create_or_update_inactive_supporter(validated_data)
        elif self.has_company_data and self.has_supporter_data:
            self._create_supporter(validated_data)
        elif self.has_company_data != self.has_supporter_data:
            self.fail(self.ERROR_MISSING_DATA)


class SupporterCriteriaSubmissionSerializer(serializers.ModelSerializer):
    desired = serializers.JSONField(required=False, validators=[
        JSONSchemaSerializerValidator(schema=criteria_desired)])
    supporter = serializers.HiddenField(default=serializers.CreateOnlyDefault(None))

    ERROR_INVALID_ANSWERS = 'invalid_answers'
    ERROR_MISSING_RESPONSE = 'missing_response'

    default_error_messages = {
        ERROR_INVALID_ANSWERS: _("Invalid answers."),
        ERROR_MISSING_RESPONSE: _("Missing response.")
    }

    def to_internal_value(self, data):
        # Map desired value manually as DRF source attribute seems to be failing.
        if 'value' in data:
            data['desired'] = data.pop('value')

        return super().to_internal_value(data)

    def validate(self, attrs):
        """
        1 - Ensure that there's either a desired value or answers.
        2 - Check for all questions with answers, that every answer belongs in fact to that question.
        """
        attrs = super().validate(attrs)
        question = attrs.get('question', None)
        answers = attrs.get('answers', None)
        desired = attrs.get('desired', None)

        if not answers and not desired:
            self.fail(self.ERROR_MISSING_RESPONSE)

        if question and answers and any([answer.question.pk != question.pk for answer in answers]):
            self.fail(self.ERROR_INVALID_ANSWERS)

        return attrs

    def bulk_create(self, valid_criteria):
        # Bulk create does not support m2m so we need to store the answers on a separate variable
        criteria_with_answers = []
        for criteria in valid_criteria:
            if 'answers' in criteria:
                criteria_with_answers.append({
                    'question': criteria['question'].pk,
                    'answers': criteria.pop('answers')
                })

        # Create criteria
        criteria_to_create = [Criteria(**criteria) for criteria in valid_criteria]
        created_criteria = Criteria.objects.bulk_create(criteria_to_create)

        # Prepare all answers from the criteria to add them all in bulk
        through_models = []
        ThroughModel = Criteria.answers.through
        for criteria in created_criteria:
            criteria_answers = next((criterion['answers'] for criterion in criteria_with_answers
                                     if criterion['question'] == criteria.question.pk),
                                    None)
            if criteria_answers:
                for answer in criteria_answers:
                    through_models.append(ThroughModel(criteria=criteria, answer=answer))
        # Bulk create all selections of answers of every criteria
        ThroughModel.objects.bulk_create(through_models)

        return created_criteria

    class Meta:
        model = Criteria
        fields = ('question', 'answers', 'desired', 'supporter')


class PendingSupporterQuestionarySerializer(UpdateProfileFieldsSerializerMixin, PendingRegistrationSerializer):
    criteria = SupporterCriteriaSubmissionSerializer(required=False, many=True)

    ERROR_INVALID_QUESTIONS = 'invalid_questions'

    default_error_messages = {
        ERROR_INVALID_QUESTIONS: _("Invalid questions.")
    }

    @property
    def has_criteria(self):
        return self._has_request_field('criteria')

    def _validate_criteria(self, criteria):
        """
        Check that every question in each criteria
        belongs in fact to the Affiliate question bundles.
        """
        affiliate = self.pending_registration.affiliate
        affiliate_questions_pks = affiliate.question_bundles.all().values_list('questions__pk', flat=True)

        if any([criterion['question'].pk not in affiliate_questions_pks for criterion in criteria]):
            self.fail(self.ERROR_INVALID_QUESTIONS)

    def _build_criteria_for_bulk(self, valid_criteria, supporter):
        criteria_for_bulk = []

        # Set a temporary criteria weight default
        default_criteria_weight = CriteriaWeight.objects.order_by('value').first()

        # Build criteria
        for criteria in valid_criteria:
            criteria_name = '%s - %s' % (supporter.name, criteria['question'].slug)

            criteria_for_bulk.append({
                **criteria,
                'criteria_weight': default_criteria_weight,
                'name': criteria_name,
                'supporter': supporter,
            })

        return criteria_for_bulk

    def _delete_previously_existing_criteria(self, supporter, affiliate):
        previous_question_pks = AffiliateProgramSupporterSubmission.objects.filter(
            affiliate=affiliate, supporter=supporter).values_list('criteria__question__pk', flat=True)
        Criteria.objects.filter(
            supporter=supporter,
            question__in=previous_question_pks).delete()

    def _create_or_update_submission_with_criteria(self, supporter, affiliate, criteria):
        submission, created = AffiliateProgramSupporterSubmission.objects.get_or_create(
            affiliate=affiliate, supporter=supporter)
        submission.criteria.set(criteria)
        return submission

    def update(self, validated_data):
        super().update(validated_data)

        if self.has_criteria and self._is_existing_supporter():
            supporter = self._get_supporter()
            affiliate = self.pending_registration.affiliate

            # Validate criteria
            self._validate_criteria(validated_data.get('criteria'))

            # Delete any previously submitted criteria
            self._delete_previously_existing_criteria(supporter, affiliate)

            # Create/Update Criteria
            serialized_criteria = validated_data.get('criteria')
            criteria_for_bulk = self._build_criteria_for_bulk(serialized_criteria, supporter)
            criteria = SupporterCriteriaSubmissionSerializer.bulk_create(
                SupporterCriteriaSubmissionSerializer(context={'supporter': supporter}),
                criteria_for_bulk)

            # Create/Update Affiliate Submission
            self._create_or_update_submission_with_criteria(supporter, affiliate, criteria)

            # Update Profile Fields
            if supporter.user_profile:
                self._update_profile_fields(supporter.user_profile, criteria=criteria)


class PendingSupporterAdditionalCriteriaSerializer(PendingRegistrationSerializer):
    """
    Additional criteria is in fact just loose Criteria
    that does't come from a specific Question Bundle.
    """
    additional_criteria = SupporterCriteriaSubmissionSerializer(required=False, many=True)

    @property
    def has_additional_criteria(self):
        return self._has_request_field('additional_criteria')

    def _build_criteria_for_bulk(self, valid_criteria, supporter):
        criteria_for_bulk = []

        # Set a temporary criteria weight default
        default_criteria_weight = CriteriaWeight.objects.order_by('value').first()

        # Build criteria
        for criteria in valid_criteria:
            criteria_name = '%s - %s' % (supporter.name, criteria['question'].slug)

            criteria_for_bulk.append({
                **criteria,
                'criteria_weight': default_criteria_weight,
                'name': criteria_name,
                'supporter': supporter,
            })

        return criteria_for_bulk

    def _delete_previously_existing_additional_criteria(self, supporter, affiliate):
        previous_question_pks = AffiliateProgramSupporterSubmission.objects.filter(
            affiliate=affiliate, supporter=supporter).values_list('additional_criteria__question__pk', flat=True)
        Criteria.objects.filter(
            supporter=supporter,
            question__in=previous_question_pks).delete()

    def _create_or_update_submission_with_additional_criteria(self, supporter, affiliate, additional_criteria):
        submission, created = AffiliateProgramSupporterSubmission.objects.get_or_create(
            affiliate=affiliate, supporter=supporter)
        submission.additional_criteria.set(additional_criteria)
        return submission

    def update(self, validated_data):
        super().update(validated_data)

        if self.has_additional_criteria and self._is_existing_supporter():
            supporter = self._get_supporter()
            affiliate = self.pending_registration.affiliate

            # Delete any previously submitted criteria
            self._delete_previously_existing_additional_criteria(supporter, affiliate)

            # Create/Update Criteria from Additional Criteria
            serialized_criteria = validated_data.get('additional_criteria')
            criteria_for_bulk = self._build_criteria_for_bulk(serialized_criteria, supporter)
            additional_criteria = SupporterCriteriaSubmissionSerializer.bulk_create(
                SupporterCriteriaSubmissionSerializer(context={'supporter': supporter}),
                criteria_for_bulk)

            # Update Submission with Additional Criteria
            self._create_or_update_submission_with_additional_criteria(supporter, affiliate, additional_criteria)


class SupporterQuestionsWeightSubmissionSerializer(serializers.Serializer):
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    criteria_weight = serializers.PrimaryKeyRelatedField(queryset=CriteriaWeight.objects.all())


class SupporterImportancesSubmissionSerializer(serializers.Serializer):
    level_weight = serializers.PrimaryKeyRelatedField(queryset=CriteriaWeight.objects.all())
    locations_weight = serializers.PrimaryKeyRelatedField(queryset=CriteriaWeight.objects.all())
    sectors_weight = serializers.PrimaryKeyRelatedField(queryset=CriteriaWeight.objects.all())

    questions = SupporterQuestionsWeightSubmissionSerializer(many=True)

    ERROR_MISSING_CRITERIA = 'missing_criteria'

    default_error_messages = {
        ERROR_MISSING_CRITERIA: _("Missing criteria.")
    }

    def _set_criteria_weights(self, supporter, questions_criteria):
        questions_pks = [question_criteria['question'].pk for question_criteria in questions_criteria]
        criterias_to_update = Criteria.objects.filter(supporter=supporter, question__in=questions_pks)

        if not criterias_to_update.exists():
            self.fail(self.ERROR_MISSING_CRITERIA)

        # Add new criteria weights to update
        for criteria in criterias_to_update:
            new_criteria_weight = next(
                (new_criteria['criteria_weight'] for new_criteria in questions_criteria
                 if new_criteria['question'].id == criteria.question.pk),
                None)
            criteria.criteria_weight = new_criteria_weight

        # Update new criteria weights
        Criteria.objects.bulk_update(criterias_to_update, ['criteria_weight'])

    def set_weights(self, validated_data):
        supporter = self.context['supporter']

        # Bulk set criteria questions' weights
        questions_weights = validated_data.pop('questions')
        self._set_criteria_weights(supporter, questions_weights)

        # Update Supporter criteria weights
        supporter.level_weight = validated_data.get('level_weight')
        supporter.locations_weight = validated_data.get('locations_weight')
        supporter.sectors_weight = validated_data.get('sectors_weight')
        supporter.save()


class PendingSupporterCriteriaImportancesSerializer(PendingRegistrationSerializer):
    importances = SupporterImportancesSubmissionSerializer(required=False)

    @property
    def has_importances(self):
        return self._has_request_field('importances')

    def update(self, validated_data):
        super().update(validated_data)

        if self.has_importances and self._is_existing_supporter():
            supporter = self._get_supporter()

            # Set Criteria Weights
            SupporterImportancesSubmissionSerializer.set_weights(
                SupporterImportancesSubmissionSerializer(context={'supporter': supporter}),
                validated_data.get('importances'))

class PendingSupporterTeamMembersSerializer(PendingRegistrationSerializer):
    team_members = serializers.JSONField(required=False)

    @property
    def has_team_members(self):
        return self._has_request_field('team_members')
    
    def update(self, validated_data):
        super().update(validated_data)

        if self.has_team_members and self._is_existing_supporter():
            supporter = self._get_supporter()
            affiliate = self.pending_registration.affiliate            
            submission = AffiliateProgramSupporterSubmission.objects.get(affiliate=affiliate, supporter=supporter)
            if submission:
                submission.team_members = validated_data.get('team_members')
                submission.save()

class RegisterPendingSupporterSerializer(
        AffiliateWebhookMixin, PendingSupporterEmailSerializer, PendingSupporterPasswordSerializer,
        PendingSupporterDataSerializer, PendingSupporterQuestionarySerializer,
        PendingSupporterAdditionalCriteriaSerializer, PendingSupporterCriteriaImportancesSerializer,
        PendingSupporterTeamMembersSerializer):
    """
    Serializer class that gathers all steps
    and manages the status of the pending registration.
    """
    affiliate = serializers.PrimaryKeyRelatedField(required=False, queryset=Affiliate.objects.filter(
        flow_target=Company.SUPPORTER))

    ERROR_MISSING_DEFAULT_AFFILIATE = 'missing_default_affiliate'

    default_error_messages = {
        ERROR_MISSING_DEFAULT_AFFILIATE: _("Missing default affiliate."),
    }

    @property
    def _has_complete_submission(self):
        supporter = self._get_supporter()
        affiliate = self.pending_registration.affiliate

        if not affiliate or not supporter:
            return False

        return AffiliateProgramSupporterSubmission.objects.filter(
            supporter=supporter, affiliate=affiliate,
            supporter__level_weight__isnull=False,
            supporter__locations_weight__isnull=False, supporter__sectors_weight__isnull=False,
            investing_level_range__isnull=False, criteria__isnull=False).exists()

    @property
    def _is_supporter_complete(self):
        user_profile = self._get_user_profile()

        if not user_profile:
            return False

        return all([
            user_profile.user.has_usable_password(),
            self._has_complete_submission
        ])

    def _get_default_affiliate(self):
        if not hasattr(self, 'default_affiliate') or not self.default_affiliate:
            try:
                self.default_affiliate = Affiliate.objects.get(flow_target=Company.SUPPORTER, default_flow=True)
            except Affiliate.DoesNotExist:
                self.fail(self.ERROR_MISSING_DEFAULT_AFFILIATE)

        return self.default_affiliate

    def _is_detached_submission(self):
        """
        A detached submission enables a visitor to submit
        an Affiliate flow without completing registration.
        """
        return self.pending_registration.affiliate and self.pending_registration.affiliate.default_flow is False

    def _get_user_profile(self):
        if not hasattr(self, 'user_profile') or not self.user_profile:
            try:
                self.user_profile = UserProfile.objects.select_related(
                    'user').get(user=self.pending_registration.user)
            except (UserProfile.DoesNotExist):
                self.user_profile = None

        return self.user_profile

    def _create_user_profile(self, user_instance, company_instance):
        self.user_profile = UserProfile.objects.create(
            source=self.pending_registration.affiliate, user=user_instance, company=company_instance)
        return self.user_profile

    def _is_existing_supporter(self, with_user_profile=False):
        if not hasattr(self, 'is_existing_supporter') or not self.is_existing_supporter or with_user_profile:
            by_profile_or_email = {
                'user_profile__user': self.pending_registration.user
            } if with_user_profile else {
                'email': self.pending_registration.user.email
            }
            self.is_existing_supporter = Supporter.all_supporters.filter(**by_profile_or_email).exists()

        return self.is_existing_supporter

    def _get_supporter(self):
        if self._is_existing_supporter(with_user_profile=True):
            user_profile = self._get_user_profile()
            return user_profile.supporter.first()

        try:
            return Supporter.all_supporters.get(
                user_profile__isnull=True, email=self.pending_registration.user.email)
        except Supporter.DoesNotExist:
            return None

    def update(self, validated_data):
        super().update(validated_data)

        # Call Affiliate webhooks once submission is completed.
        if self._has_complete_submission:
            supporter = self._get_supporter()
            submission = AffiliateProgramSupporterSubmission.objects.get(supporter=supporter)
            self.send_submission_to_affiliate_webhooks(submission)

        # Update Pending Registration complete status.
        complete_status_changed = self.pending_registration.is_complete != self._is_supporter_complete
        if self._is_existing_supporter(with_user_profile=True) and complete_status_changed:
            self.pending_registration.is_complete = self._is_supporter_complete
            self.pending_registration.save()


class FinishedPendingSupporterSerializer(PendingRegistrationSerializer):
    """
    Authenticate user if registration is completed.
    """
    ERROR_INCOMPLETE_REGISTRATION = 'incomplete_registration'

    default_error_messages = {
        ERROR_INCOMPLETE_REGISTRATION: _("Incomplete registration.")
    }

    def finish(self, validated_data):
        if not self._has_request_field('token'):
            self.fail(self.ERROR_MISSING_DATA)

        token = validated_data.get('token')
        pending_registration = PendingRegistration.objects.select_related(
            'user').prefetch_related('user__emailaddress_set').get(uid=token)

        if not pending_registration.is_complete:
            self.fail(self.ERROR_INCOMPLETE_REGISTRATION)

        # Ask for account verification
        account_email = pending_registration.user.emailaddress_set.first()
        account_email.send_confirmation(self.context['request'])

        # Delete pending registration
        pending_registration.delete()

        return pending_registration.user


class AffiliateSupporterProgramSerializer(serializers.ModelSerializer):
    affiliate = AffiliateSerializer()
    supporter = SupporterSerializer()
    investing_level_range = SupporterInvestingLevelRangeField()
    criteria = serializers.SerializerMethodField()
    additional_criteria = SupporterCriteriaSerializer(many=True)

    def __init__(self, *args, **kwargs):
        super(AffiliateSupporterProgramSerializer, self).__init__(*args, **kwargs)
        user = self.context['request'].user
        if user and self.instance.supporter.user_profile.user == user:
            self.fields['team_members'] = serializers.SerializerMethodField()

    def get_criteria(self, instance):
        """
        Order criteria by question's order on its corresponding question bundle

        TODO: Check if there's a way to order criteria only through a queryset to improve performance
        """
        ordered_criteria_by_questions = []

        # Grab ordered questions bundles with its questions
        affiliate_question_bundles = instance.affiliate.question_bundles.prefetch_related(
            'questions').filter(has_team_member_questions=False)

        # Collect criteria following the question bundle order
        for question_bundle in affiliate_question_bundles:
            ordered_questions = question_bundle.questions.filter(is_team_member_question=False)

            for question in ordered_questions:
                question_response = next(
                    (criteria for criteria in instance.criteria.all() if criteria.question == question), None)

                if question_response:
                    ordered_criteria_by_questions.append(question_response)

        return SupporterCriteriaSerializer(ordered_criteria_by_questions, many=True).data

    def get_team_members(self, instance):
        team_members = instance.team_members or []
        for team_member in team_members:
            responses = []
            for response in team_member.get('responses', []):
                response = Response.objects.get(id=response)
                serializer = AffiliateSupporterProgramSubmissionTeamMemberResponseSerializer(response)
                responses.append(serializer.data)
            team_member['responses'] = responses
        return team_members

    class Meta:
        model = AffiliateProgramSupporterSubmission
        exclude = ('id','team_members')


class AffiliateSupporterProgramSubmissionTeamMemberResponseSerializer(serializers.ModelSerializer):
    question = QuestionSerializer()

    class Meta:
        model = Response
        fields = ('id', 'value', 'answers', 'question')


class AffiliateSupporterProgramSubmissionSerializer(AffiliateWebhookMixin, serializers.Serializer):
    """
    Serializer class that creates an Affiliate Supporter submission for authenticated users.
    """
    affiliate = serializers.PrimaryKeyRelatedField(queryset=Affiliate.objects.filter(flow_target=Company.SUPPORTER))
    supporter = SupporterSubmissionSerializer()
    criteria = SupporterCriteriaSubmissionSerializer(many=True)
    additional_criteria = SupporterCriteriaSubmissionSerializer(required=False, many=True)
    importances = SupporterImportancesSubmissionSerializer()
    team_members = serializers.JSONField(required=False)

    ERROR_INVALID_USER = 'invalid_user'

    default_error_messages = {
        ERROR_INVALID_USER: _("Invalid user.")
    }

    def _get_user_profile(self, owner):
        try:
            return UserProfile.objects.get(user=owner)
        except UserProfile.DoesNotExist:
            self.fail(self.ERROR_INVALID_USER)

    def _update_supporter(self, instance, supporter_data):
        return SupporterSubmissionSerializer.update(SupporterSubmissionSerializer(), instance, supporter_data)

    def _create_supporter_criteria(self, supporter, criteria_data):
        criteria_for_bulk = []

        # Set a temporary criteria weight default
        default_criteria_weight = CriteriaWeight.objects.order_by('value').first()

        # Build criteria
        for criteria in criteria_data:
            criteria_name = '%s - %s' % (supporter.name, criteria['question'].slug)

            criteria_for_bulk.append({
                **criteria,
                'criteria_weight': default_criteria_weight,
                'name': criteria_name,
                'supporter': supporter,
            })

        return SupporterCriteriaSubmissionSerializer.bulk_create(
            SupporterCriteriaSubmissionSerializer(context={'supporter': supporter}),
            criteria_for_bulk)

    def _disable_removed_criteria(self, supporter, current_criteria):
        # Disable active Criteria with short name that was removed from submitted criteria:
        questions_to_exclude = [criteria['question'].pk for criteria in current_criteria]
        additional_criteria_question_types = [QuestionType.MULTI_SELECT,
                                              QuestionType.SINGLE_SELECT, QuestionType.NUMERIC, QuestionType.RANGE]

        Criteria.objects.filter(
            supporter=supporter, question__question_type__type__in=additional_criteria_question_types,
            question__short_name__isnull=False, is_active=True).exclude(
            question__in=questions_to_exclude).update(
            is_active=False)

    def _disable_previous_criteria(self, supporter, current_criteria):
        # Disable previous Criteria in Question Bundle:
        criteria_pks = [criteria.pk for criteria in current_criteria]
        question_pks = [criteria.question.pk for criteria in current_criteria]

        Criteria.objects.filter(
            supporter=supporter, question__in=question_pks, is_active=True).exclude(
            pk__in=criteria_pks).update(is_active=False)

    def _set_criteria_weights(self, supporter, importances):
        SupporterImportancesSubmissionSerializer.set_weights(
            SupporterImportancesSubmissionSerializer(context={'supporter': supporter}),
            importances)

    def _create_affiliate_supporter_submission(
            self, affiliate, supporter, criteria, additional_criteria=None, team_members=None):
        supporter_sectors = SupporterSectorsOfInterestSerializer(supporter)
        supporter_locations = SupporterLocationsOfInterestSerializer(supporter)

        submission = AffiliateProgramSupporterSubmission.objects.create(
            affiliate=affiliate, supporter=supporter, investing_level_range=supporter.investing_level_range,
            sectors_of_interest=supporter_sectors.data, locations_of_interest=supporter_locations.data,
            team_members=team_members)
        submission.criteria.set(criteria)
        if additional_criteria:
            submission.additional_criteria.set(additional_criteria)
        return submission

    def create(self, validated_data):
        affiliate = validated_data.get('affiliate')
        team_members = validated_data.get('team_members')
        user_profile = self._get_user_profile(validated_data.get('owner'))

        # 1. Update Supporter
        supporter = user_profile.supporter.first()
        updated_supporter = self._update_supporter(supporter, validated_data.get('supporter'))

        new_criteria = validated_data.get('criteria')
        new_additional_criteria = validated_data.get('additional_criteria', [])

        # 2. Disable removed Criteria from payload
        criteria_to_exclude = new_criteria + new_additional_criteria
        self._disable_removed_criteria(supporter, criteria_to_exclude)

        # 3. Create Supporter Criteria (from responses & additional criteria)
        criteria = self._create_supporter_criteria(updated_supporter, new_criteria)
        additional_criteria = self._create_supporter_criteria(
            updated_supporter, new_additional_criteria) if len(new_additional_criteria) else None

        # 4. Disable previous Criteria in favor of new ones
        current_criteria = criteria + additional_criteria if additional_criteria else criteria
        self._disable_previous_criteria(supporter, current_criteria)

        # 5. Create Supporter Criteria Weights (from importances)
        self._set_criteria_weights(supporter, validated_data.get('importances'))

        # 6. Create Submission
        submission = self._create_affiliate_supporter_submission(
            affiliate, updated_supporter, criteria, additional_criteria, team_members)

        # 5. Call Affiliate webhooks
        self.send_submission_to_affiliate_webhooks(submission)

        return AffiliateSupporterProgramSerializer(submission, context=self.context).data


class MatchingScoresImpactSerializer(serializers.Serializer):
    score = serializers.SerializerMethodField()
    details = serializers.SerializerMethodField()

    def _get_active_algorithm(self):
        with connection.cursor() as cursor:
            cursor.execute('''
                SELECT
                    ma.name,
                    ma.level_weight_id,
                    level_mcw.value AS level_score,
                    ma.location_weight_id,
                    location_mcw.value AS location_score,
                    ma.sector_weight_id,
                    sector_mcw.value AS sector_score,
                    ma.response_weight_id,
                    response_mcw.value AS response_score,
                    ma.unanswered_factor,
                    ma.high_unanswered_factor,
                    ma.wrong_factor,
                    ma.high_wrong_factor
                FROM matching.algorithm AS ma
                LEFT JOIN matching_criteriaweight AS level_mcw ON level_mcw.id = ma.level_weight_id
                LEFT JOIN matching_criteriaweight AS location_mcw ON location_mcw.id = ma.location_weight_id
                LEFT JOIN matching_criteriaweight AS sector_mcw ON sector_mcw.id = ma.sector_weight_id
                LEFT JOIN matching_criteriaweight AS response_mcw ON response_mcw.id = ma.response_weight_id
                WHERE ma.active = TRUE;
            ''')
            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, cursor.fetchone()))

    def _get_responses_by_impact(self, max_total_score, entrepreneur, supporter):
        algorithm = self._get_active_algorithm()

        with connection.cursor() as cursor:
            cursor.execute(f'''
                SELECT DISTINCT ON (qc.question_id)
                    mc.name AS criteria,
                    qc.question_id,
                    mq.resource_question AS supporter_question,
                    coalesce(sa.answers, to_json(mc.desired)) AS supporter_answers,
                    mq.entrepreneur_question AS entrepreneur_question,
                    coalesce(ea.answers, to_json(ea.value)) AS entrepreneur_answers,
                    am.is_correct AS is_match,
                    (CASE
                        WHEN am.is_correct
                            THEN coalesce(am.default_score, {algorithm['response_score']})
                        WHEN coalesce(am.weight_id, {algorithm['response_weight_id']}) = 5 AND am.company_id IS NULL
                            THEN -coalesce(
                                am.default_score, {algorithm['response_score']}
                            ) * {algorithm['high_unanswered_factor']}
                        WHEN am.company_id IS NULL
                            THEN -coalesce(
                                am.default_score, {algorithm['response_score']}
                            ) * {algorithm['unanswered_factor']}
                        WHEN coalesce(am.weight_id, {algorithm['response_weight_id']}) = 5
                            THEN -coalesce(
                                am.default_score, {algorithm['response_score']}
                            ) * {algorithm['high_wrong_factor']}
                        ELSE -coalesce(am.default_score, {algorithm['response_score']}) * {algorithm['wrong_factor']}
                    END)::numeric::integer AS score
                FROM matching.entrepreneur_supporter_view AS esv
                LEFT JOIN matching.question_criteria_view AS qc
                    ON qc.supporter_id = esv.supporter_id
                LEFT JOIN matching.match_response_view AS am
                    ON am.supporter_id = esv.supporter_id
                        AND am.company_id = esv.company_id
                        AND qc.question_id = am.question_id
                LEFT JOIN matching_question AS mq
                    ON mq.id = qc.question_id
                LEFT JOIN matching_criteria AS mc
                    ON mc.id = qc.criteria_id
                LEFT JOIN (
                    SELECT mca.criteria_id, json_agg(ma.value) AS answers
                    FROM matching_criteria_answers AS mca
                    LEFT JOIN matching_answer AS ma
                        ON ma.id = mca.answer_id
                    GROUP BY mca.criteria_id
                ) AS sa
                    ON sa.criteria_id = qc.criteria_id
                LEFT JOIN (
                    (
                        SELECT mr.question_id, mr.value, json_agg(ma.value) filter (WHERE ma.value IS NOT NULL) AS answers
                        FROM viral_userprofile AS vup
                        LEFT JOIN (
                            SELECT DISTINCT ON(question_id, user_profile_id) *
                            FROM matching_response AS mr
                            ORDER BY question_id, user_profile_id, created_at DESC
                        ) AS mr
                            ON mr.user_profile_id = vup.id
                        LEFT JOIN matching_response_answers AS mra
                            ON mra.response_id = mr.id
                        LEFT JOIN matching_answer AS ma
                            ON ma.id = mra.answer_id
                        LEFT JOIN matching_question AS mq
                            ON mq.id = mr.question_id
                        LEFT JOIN matching_questiontype AS qt
                            ON qt.id = mq.question_type_id
                        WHERE vup.company_id = {entrepreneur.pk} AND qt.type != 'single-select'
                        GROUP BY mr.question_id, mr.value
                    ) UNION ALL (
                        SELECT DISTINCT ON (mr.question_id) mr.question_id, mr.value, json_agg(ma.value) AS answers
                        FROM viral_userprofile AS vup
                        LEFT JOIN matching_response AS mr
                            ON mr.user_profile_id = vup.id
                        LEFT JOIN matching_response_answers AS mra
                            ON mra.response_id = mr.id
                        LEFT JOIN matching_answer AS ma
                            ON ma.id = mra.answer_id
                        LEFT JOIN matching_question AS mq
                            ON mq.id = mr.question_id
                        LEFT JOIN matching_questiontype AS qt
                            ON qt.id = mq.question_type_id
                        WHERE vup.company_id = {entrepreneur.pk} AND qt.type = 'single-select'
                        GROUP BY mr.question_id, mr.created_at, mr.value
                        ORDER BY mr.question_id, mr.created_at DESC
                    )
                ) AS ea
                    ON ea.question_id = qc.question_id
                WHERE qc.question_id IS NOT NULL AND (
                    ({entrepreneur.pk} = -1 AND {supporter.pk} = -1)
                    OR ({entrepreneur.pk} > -1
                        AND {supporter.pk} > -1
                        AND esv.company_id = {entrepreneur.pk}
                        AND esv.supporter_id = {supporter.pk}
                    )
                    OR ({supporter.pk} = -1 AND esv.company_id = {entrepreneur.pk})
                    OR ({entrepreneur.pk} = -1 AND esv.supporter_id = {supporter.pk})
                );
            ''')
            columns = [col[0] for col in cursor.description]
            responses = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return [
                dict(item, impact=(round((item['score'] / max_total_score) * 100, 2) if max_total_score else 0))
                for item in responses
            ]

    def get_score(self, criteria_by_impact):
        return criteria_by_impact['score'] if criteria_by_impact['score'] < 100 else 99

    def get_details(self, criteria_by_impact):
        assert all(['entrepreneur' in self.context, 'supporter' in self.context, 'auth_company_type' in self.context])

        auth_company_type = self.context['auth_company_type']
        entrepreneur = self.context['entrepreneur']
        supporter = self.context['supporter']

        matching_caller = supporter if auth_company_type == Company.SUPPORTER else entrepreneur
        matching_callee = entrepreneur if auth_company_type != Company.ENTREPRENEUR else supporter

        formatted_entrepreneur_level = f"{_('Level')} {entrepreneur.level[0]} - {entrepreneur.level[1]}"

        criteria_scores_impact = [
            {'criteria': _('Location'),
             'my_answer': matching_caller.locations.values_list('formatted_address', flat=True).all()
             if matching_caller.locations.exists() else None,
             'matched_answer': matching_callee.locations.values_list('formatted_address', flat=True).all()
             if matching_callee.locations.exists() else None, 'match': criteria_by_impact['location_match'],
             'impact': criteria_by_impact['location_impact']},
            {'criteria': _('Sector'),
             'my_answer': matching_caller.sectors.values_list('name', flat=True).all()
             if matching_caller.sectors.exists() else None, 'matched_answer': matching_callee.sectors.values_list(
                 'name', flat=True).all() if matching_callee.sectors.exists() else None,
             'match': criteria_by_impact['sector_match'],
             'impact': criteria_by_impact['sector_impact']},
            {'criteria': _('Venture Investment Level')
             if auth_company_type == Company.ENTREPRENEUR else _('Investment Level Range'),
             'my_answer': supporter.formatted_level_range
             if auth_company_type == Company.SUPPORTER else formatted_entrepreneur_level,
             'matched_answer': formatted_entrepreneur_level
             if auth_company_type == Company.SUPPORTER else supporter.formatted_level_range,
             'match': criteria_by_impact['level_match'],
             'impact': criteria_by_impact['level_impact'], },
            *
            [{'criteria': response['entrepreneur_question']
              if auth_company_type == Company.ENTREPRENEUR else response['supporter_question'],
              'my_answer': response['supporter_answers']
              if auth_company_type == Company.SUPPORTER else response['entrepreneur_answers'],
              'matched_answer': response['entrepreneur_answers']
              if auth_company_type == Company.SUPPORTER else response['supporter_answers'],
              'match': bool(response['is_match']),
              'impact': response['impact'] if not response['impact'] == 0 else 0, }
             for response in self._get_responses_by_impact(
                 criteria_by_impact['max_total_score'],
                 entrepreneur, supporter)]]

        # Sort the results by descending impact
        return sorted(
            criteria_scores_impact,
            key=lambda criterion: (
                abs(criterion['impact']),
                bool(criterion['match']),
                bool(criterion['my_answer']) and bool(criterion['matched_answer'])
            ),
            reverse=True
        )


class AlgorithmCalculatorSearchCompaniesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ('id', 'name')


class AlgorithmCalculatorMatchingCriteriaSerializer(serializers.Serializer):
    criteria = serializers.SerializerMethodField()

    def _get_level(self, entrepreneur, supporter):
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
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

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

    def get_criteria(self, data):
        return {
            'level': self._get_level(self.context['entrepreneur'], self.context['supporter']),
            'responses': self._get_responses(self.context['entrepreneur'], self.context['supporter']),
        }
