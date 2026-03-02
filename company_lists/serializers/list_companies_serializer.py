import os
from django.contrib.admin.utils import flatten
from django.db.models import Q
from rest_framework import serializers

from grid.models import Category

from matching.algorithm import getEntrepreneurMatchByCompany
from matching.algorithm_supporters import getSupporterMatchByCompany
from matching.models import InterestedCTA

from viral.models import AffiliateProgramEntry, Company
from viral.serializers import (AffiliateProgramEntrySerializer,
                               CompanySerializer)


class ListCompaniesCompactSerializer(serializers.ModelSerializer):
    """
    Compact version of Company listing due to performance reasons.
    """
    logo = serializers.ImageField(use_url=True, allow_null=True, read_only=True)

    class Meta:
        model = Company
        fields = ('uid', 'name', 'logo')


class ListCompaniesSerializer(serializers.Serializer):
    """
    Custom schema to match Matching Scores endpoint schema
    """
    supporter = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()
    affiliates = serializers.SerializerMethodField()
    interests = serializers.SerializerMethodField()
    milestone_planner = serializers.SerializerMethodField()

    def _get_request_supporter(self):
        if not hasattr(self, 'supporter'):
            self.supporter = self.context.get('supporter') or self.context['request'].user.userprofile.supporter.first()

        return self.supporter

    def _get_company_score(self, company):
        match_scores = self.context['scores'] or []

        if company.type == Company.SUPPORTER:
            return next((
                match for match in match_scores if (
                    'supporter' in match and
                    match['supporter'] and
                    match['supporter'].user_profile.pk == company.company_profile.pk
                )
            ), None)
        elif company.type == Company.ENTREPRENEUR:
            return next((
                match for match in match_scores if (
                    'company' in match and
                    match['company'] and
                    match['company'].pk == company.pk
                )
            ), None)

    def get_supporter(self, company):
        # TEMPORARY: To avoid circular dependency
        from matching.serializers import RetrieveSupporterSerializer

        if company.type == Company.SUPPORTER:
            match = self._get_company_score(company)
            supporter = match['supporter'] if match else None
            if supporter:
                return RetrieveSupporterSerializer(supporter).data
        return None

    def get_score(self, company):
        request_user = self.context['request'].user or None
        is_authenticated = bool(request_user) and request_user.is_authenticated

        if not is_authenticated:
            return None

        match = self._get_company_score(company)
        return match['score'] if bool(match) and bool(match['score']) else 0

    def get_company(self, company):
        if company.type == Company.ENTREPRENEUR:
            return CompanySerializer(company).data
        return None

    def get_level(self, company):
        if company.type == Company.ENTREPRENEUR:
            assessment = company.latest_assessment()
            return assessment.level.value if assessment else None
        return None

    def get_affiliates(self, company):
        request_user = self.context['request'].user or None
        is_authenticated = bool(request_user) and request_user.is_authenticated

        if not is_authenticated:
            return None

        if company.type == Company.ENTREPRENEUR:
            try:
                # Fetch all affiliate submissions associated to networks where this supporter is a member
                supporter = self._get_request_supporter()
                if not supporter:
                    return None
                supporter_networks = supporter.user_profile.company.networks.all()
                submissions = AffiliateProgramEntry.objects.prefetch_related('affiliate__networks__locations').filter(
                    user_profile__company=company.id).filter(Q(affiliate__networks__in=supporter_networks) |
                                                             Q(affiliate__supporters__pk__in=[supporter.pk])).order_by('-updated_at')
                return AffiliateProgramEntrySerializer(submissions, many=True).data
            except AffiliateProgramEntry.DoesNotExist:
                pass
        return None

    def get_interests(self, company):
        # TEMPORARY: To avoid circular dependency
        from matching.serializers import InterestedCTASerializer

        request_user = self.context['request'].user or None
        request_profile = request_user.userprofile if request_user and request_user.is_authenticated else None

        if not request_profile:
            return None

        supporter = company if company.type == Company.SUPPORTER else request_profile.company
        entrepreneur = company if company.type == Company.ENTREPRENEUR else request_profile.company

        try:
            connection = InterestedCTA.objects.get(supporter=supporter, entrepreneur=entrepreneur)
            return InterestedCTASerializer(connection).data
        except InterestedCTA.DoesNotExist:
            return None

    def get_milestone_planner(self, company):
        if milestone_planner := company.milestone_planners.first():
            if self.context['request'].user.is_authenticated:
                is_invited_user = milestone_planner.invited_users.filter(id=self.context['request'].user.userprofile.id).exists()
                return milestone_planner.uid if is_invited_user else None
        return None


class ListEntrepreneurCompaniesCSVSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField()
    profile_url = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    sectors = serializers.SerializerMethodField()
    sector_groups = serializers.SerializerMethodField()
    match_score = serializers.SerializerMethodField()
    connection_state = serializers.SerializerMethodField()
    viral_investment_level = serializers.SerializerMethodField()
    viral_category_levels = serializers.SerializerMethodField()

    def _get_request_supporter(self):
        if not hasattr(self, 'request_supporter'):
            self.request_supporter = self.context.get(
                'supporter') or self.context['request'].user.userprofile.supporter.first()

        return self.request_supporter

    def _get_request_profile(self):
        if not hasattr(self, 'profile'):
            self.profile = self.context['request'].user.userprofile

        return self.profile

    def get_email(self, company):
        request_profile = self._get_request_profile()
        supporter = company if company.type == Company.SUPPORTER else request_profile.company
        entrepreneur = company if company.type == Company.ENTREPRENEUR else request_profile.company

        companies_are_connected = InterestedCTA.objects.filter(
            supporter=supporter, entrepreneur=entrepreneur, state_of_interest=InterestedCTA.CONNECTED).exists()
        return company.email if companies_are_connected else ""

    def get_profile_url(self, company):
        return 'https://' + os.getenv('APP_BASE_URL', 'my.abaca.app') + '/profile/v/' + str(company.access_hash)

    def get_location(self, company):
        return company.locations.values(
            'formatted_address', 'city', 'region', 'region_abbreviation', 'country',
            'continent', 'groups__name').first()

    def get_sectors(self, company):
        return ' \n'.join(map(lambda sector: sector.name.capitalize(), company.sectors.all()))

    def get_sector_groups(self, company):
        sectors = company.sectors.all()
        sectors_groups = ""
        groups = [list(sector.groups.values_list('name', flat=True).distinct()) for sector in sectors]
        unique_groups = set(flatten(groups))

        for group in unique_groups:
            sectors_groups += group.capitalize()
            sectors_groups += ' \n'

        return sectors_groups

    def get_match_score(self, company):
        request_profile = self._get_request_profile()

        if not request_profile or not request_profile.company:
            return None

        if company.type == Company.ENTREPRENEUR:
            supporter = self._get_request_supporter()
            match = getSupporterMatchByCompany(supporter, company)
            return "{score}%".format(score=match['score']) if match else 0
        elif company.type == Company.SUPPORTER:
            match = getEntrepreneurMatchByCompany(request_profile, company.company_profile)
            return "{score}%".format(score=match['score']) if match else 0

    def get_connection_state(self, company):
        request_profile = self._get_request_profile()
        supporter = company if company.type == Company.SUPPORTER else request_profile.company
        entrepreneur = company if company.type == Company.ENTREPRENEUR else request_profile.company

        try:
            connection = InterestedCTA.objects.get(supporter=supporter, entrepreneur=entrepreneur)
            return dict(InterestedCTA.INTEREST_CHOICES)[connection.state_of_interest] or connection.state_of_interest
        except InterestedCTA.DoesNotExist:
            return "None"

    def get_viral_investment_level(self, company):
        latest_assessment = company.latest_assessment()
        return latest_assessment.level.value if latest_assessment else None

    def get_viral_category_levels(self, company):
        viral_category_levels = ""
        latest_assessment = company.latest_assessment()

        if not latest_assessment:
            return viral_category_levels

        for category_level in latest_assessment.data:
            try:
                category = Category.objects.get(pk=category_level['category'])
                viral_category_levels += "{category} - {level}\n".format(
                    category=category.name, level=category_level['level'])
            except Category.DoesNotExist:
                pass

        return viral_category_levels

    class Meta:
        model = Company
        fields = ('uid', 'name', 'founded_date', 'email', 'website', 'profile_url', 'about', 'location', 'sectors',
                  'sector_groups', 'match_score', 'connection_state', 'viral_investment_level', 'viral_category_levels')


class ListSupporterCompaniesCSVSerializer(ListEntrepreneurCompaniesCSVSerializer, serializers.ModelSerializer):
    investing_level_range = serializers.SerializerMethodField()
    supporter_types = serializers.SerializerMethodField()
    sectors_of_interest = serializers.SerializerMethodField()
    sector_groups_of_interest = serializers.SerializerMethodField()
    locations_of_interest = serializers.SerializerMethodField()
    location_groups_of_interest = serializers.SerializerMethodField()

    def _get_supporter(self, company):
        return company.company_profile.supporter.first() or None

    def get_investing_level_range(self, company):
        supporter = self._get_supporter(company)
        if not supporter:
            return None

        investing_range = [supporter.investing_level_range.lower]

        if supporter.investing_level_range.upper:
            # Add upper value:
            investing_range.append(supporter.investing_level_range.upper)
            # Include upper value in range:
            investing_range[1] += 1
            # Return a comma separated list of numbers from the range:
            return ', '.join(map(str, list(range(*investing_range))))

        return str(investing_range.pop())

    def get_supporter_types(self, company):
        supporter = self._get_supporter(company)
        if not supporter:
            return None

        # Return a comma separated list of supporter types:
        return ' \n'.join(map(lambda type: type.name.capitalize(), supporter.types.all()))

    def get_sectors_of_interest(self, company):
        supporter = self._get_supporter(company)
        if not supporter:
            return None

        return ' \n'.join(map(lambda sector: sector.name.capitalize(), supporter.sectors.all()))

    def get_sector_groups_of_interest(self, company):
        supporter = self._get_supporter(company)
        if not supporter:
            return None

        groups_of_interest = ""
        interest_sectors = supporter.sectors_of_interest.exclude(group=None)
        sector_groups = [interest_sector.group.name for interest_sector in interest_sectors]
        unique_groups = sorted(set(sector_groups))

        for group in unique_groups:
            groups_of_interest += group.capitalize()
            # Add extra space at the end between groups:
            groups_of_interest += ' \n'

        return groups_of_interest

    def get_locations_of_interest(self, company):
        supporter = self._get_supporter(company)
        if not supporter:
            return None

        return ' \n'.join(map(lambda location: location.formatted_address.capitalize(), supporter.locations.all()))

    def get_location_groups_of_interest(self, company):
        supporter = self._get_supporter(company)
        if not supporter:
            return None

        groups_of_interest = ""
        interest_locations = supporter.locations_of_interest.exclude(group=None)
        location_groups = [interest_location.group.name for interest_location in interest_locations]
        unique_groups = sorted(set(location_groups))

        for group in unique_groups:
            groups_of_interest += group.capitalize()
            # Add extra space at the end between groups:
            groups_of_interest += ' \n'

        return groups_of_interest

    class Meta:
        model = Company
        fields = ('uid', 'name', 'email', 'website', 'profile_url', 'about', 'location', 'sectors', 'supporter_types',
                  'sectors_of_interest', 'sector_groups_of_interest', 'locations_of_interest',
                  'location_groups_of_interest', 'investing_level_range', 'match_score', 'connection_state',)
