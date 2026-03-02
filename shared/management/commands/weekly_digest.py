import os
import random

from datetime import date
from datetime import timedelta

from django.db.models import Q
from django.core.management.base import BaseCommand

from matching.algorithm import getMatches, getEntrepreneurInterestMatches
from matching.algorithm_supporters import getMatchesSupporter, getSupporterInterestMatches
from matching.models import Supporter, InterestedCTA
from shared.mailjet import sendWeeklyDigest
from viral.models import Company, UserProfile


class Command(BaseCommand):
    """
    Goes through all entrepreneurs and supporters and fetches their matches
    with a score higher than the SCORE_MINIMUM and also any connections
    that have occurred last week

    Optional arguments
    * -t, --test : Tests weekly digest to a specified email (e.g. -t test@mail.com)
    """
    help = 'Script to fetch matches and interests for weekly digest'

    WEEKLY_MATCHES_LIMIT = 16
    LIST_MAXIMUM = 8
    SCORE_MINIMUM = 60
    BACKGROUND_COLORS = ['#7bb7ff', '#72cc72', '#f6a34b']
    COUNTRIES_WITH_REGION = ['United States', 'Canada']

    MATCHING_SUGGESTIONS = 'matching_suggestions'
    REQUESTS_RECEIVED = 'requests_received'
    NEW_CONNECTIONS = 'new_connections'

    # For each user type
    SAMPLES_TO_SEND = 3

    def _get_formatted_location(self, location):
        formatted_location = ''

        if location:
            needs_region = location.country in self.COUNTRIES_WITH_REGION

            if location.city:
                formatted_location += '{0}, '.format(location.city)

            if location.region_abbreviation and needs_region:
                formatted_location += '{0}, '.format(
                    location.region_abbreviation)

            if location.country:
                formatted_location += location.country

        return formatted_location

    def _get_company_background_color(self, company_name):
        charcode = ord(company_name[:1])
        return self.BACKGROUND_COLORS[charcode % len(self.BACKGROUND_COLORS)]

    def _get_entrepreneur_weekly_matches_list(self, matches):
        weekly_list = []
        # Get random matches
        choices_length = len(matches) if len(
            matches) <= self.LIST_MAXIMUM else self.LIST_MAXIMUM
        selected_matches = random.sample(matches, k=choices_length)
        # Order matches by score descending
        selected_matches.sort(key=lambda item: item["score"], reverse=True)

        for key, item in enumerate(selected_matches):
            supporter = item['supporter']
            match_score = item['score'] if item['score'] < 100 else 99
            score_percentage = str(match_score) + '%'

            if not supporter.user_profile.company.access_hash:
                break

            supporter_name = supporter.name
            company_link = 'https://' + \
                os.getenv('APP_BASE_URL', 'my.abaca.app') + '/profile/v/' + \
                supporter.user_profile.company.access_hash
            company_logo = supporter.user_profile.company.logo.url if supporter.user_profile.company.logo else None
            company_location = supporter.user_profile.company.locations.first()
            supporter_location = self._get_formatted_location(company_location)
            supporter_types = ', '.join(
                [type.name for type in supporter.types.all()])
            background_color = self._get_company_background_color(
                supporter_name)

            weekly_list.append({
                'index': key,
                'logo': None,
                'background': background_color,
                'link': company_link,
                'title': supporter_name,
                'letter': supporter_name[:1],
                'subtitle': supporter_location,
                'description': supporter_types,
                'tag': score_percentage
            })

        return weekly_list

    def _add_entrepreneur_matching_suggestions(self, matches_listing, user_profile):
        match_exclusions = {'connections': True,
                            'score_minimum': self.SCORE_MINIMUM}
        available_matches = getMatches(
            user_profile, per_page=24, match_exclusions=match_exclusions)

        if available_matches:
            matches_listing[self.MATCHING_SUGGESTIONS] = self._get_entrepreneur_weekly_matches_list(
                available_matches)

    def _add_entrepreneur_requests_received(self, matches_listing, user_profile):
        today = date.today()
        last_week = today - timedelta(days=7)
        recent_received_requests = InterestedCTA.objects.filter(
            entrepreneur=user_profile.company, entrepreneur_is_interested=InterestedCTA.INITIAL_VALUE, created_at__gt=last_week, created_at__lt=today)

        if recent_received_requests:
            available_matches = getEntrepreneurInterestMatches(
                user_profile.company, recent_received_requests)
            matches_listing[self.REQUESTS_RECEIVED] = self._get_entrepreneur_weekly_matches_list(
                available_matches)

    def _add_entrepreneur_new_connections(self, matches_listing, user_profile):
        today = date.today()
        last_week = today - timedelta(days=7)
        recent_accepted_requests = InterestedCTA.objects.filter(
            entrepreneur=user_profile.company, state_of_interest=InterestedCTA.CONNECTED, updated_at__gte=last_week, updated_at__lt=today)

        if recent_accepted_requests:
            available_matches = getEntrepreneurInterestMatches(
                user_profile.company, recent_accepted_requests)
            # todo: add to weekly digest
            matches_listing[self.NEW_CONNECTIONS] = self._get_entrepreneur_weekly_matches_list(
                available_matches)

    def _check_weekly_limit(self, matches_listing):
        total_matches = sum([len(list) for list in matches_listing.values()])

        # Remove one item at a time from the longest list
        while total_matches > self.WEEKLY_MATCHES_LIMIT:
            longest_list = max(matches_listing.values(), key=len)
            longest_list.pop()
            total_matches -= 1

    def _notify_entrepreneurs(self):
        user_unsubscribed = Q(
            metadata__isnull=False, metadata__key='mailjet.exclusion', metadata__value='true')
        user_inactive = Q(user__last_login__isnull=True)
        entrepreneurs = UserProfile.objects.filter(
            company__type=Company.ENTREPRENEUR).exclude(user_unsubscribed | user_inactive)

        # For testing purposes
        samples_amount = self.SAMPLES_TO_SEND

        for user_profile in entrepreneurs:
            uid = user_profile.company.uid
            email = self.test_email or user_profile.user.email
            matches_listing = {}

            # New Matching Suggestions
            self._add_entrepreneur_matching_suggestions(
                matches_listing, user_profile)

            # New Requests Received
            self._add_entrepreneur_requests_received(
                matches_listing, user_profile)

            # New Connections
            self._add_entrepreneur_new_connections(
                matches_listing, user_profile)

            # Make sure we don't surpass limit
            self._check_weekly_limit(matches_listing)

            # Notify Entrepreneur
            if matches_listing:
                sendWeeklyDigest(email, uid, **matches_listing)

                if self.test_email:
                    samples_amount -= 1
                    print("\r")
                    print(user_profile.user.email)
                    print("\n")

            # When there are no more samples needed, stop execution
            if samples_amount == 0:
                break

    def _get_supporter_weekly_matches_list(self, matches):
        weekly_list = []
        # Get random matches
        choices_length = len(matches) if len(
            matches) <= self.LIST_MAXIMUM else self.LIST_MAXIMUM
        selected_matches = random.sample(matches, k=choices_length)
        # Order matches by score descending
        selected_matches.sort(key=lambda item: item["score"], reverse=True)

        for key, item in enumerate(selected_matches):
            entrepreneur = item['company']
            match_score = item['score'] if item['score'] < 100 else 99
            score_percentage = str(match_score) + '%'

            if not entrepreneur.access_hash:
                break

            company_name = entrepreneur.name
            company_link = 'https://' + \
                os.getenv('APP_BASE_URL', 'my.abaca.app') + '/profile/v/' + \
                entrepreneur.access_hash
            company_logo = entrepreneur.logo.url if entrepreneur.logo else None
            company_location = entrepreneur.locations.first()
            entrepreneur_location = self._get_formatted_location(
                company_location)
            entrepreneur_sectors = ', '.join(
                [sector.name.capitalize() for sector in entrepreneur.sectors.all()])
            background_color = self._get_company_background_color(
                company_name)

            weekly_list.append({
                'index': key,
                'logo': None,
                'background': background_color,
                'link': company_link,
                'title': company_name,
                'letter': company_name[:1],
                'subtitle': entrepreneur_location,
                'description': entrepreneur_sectors,
                'tag': score_percentage
            })

        return weekly_list

    def _add_supporter_matching_suggestions(self, matches_listing, supporter):
        match_exclusions = {'connections': True,
                            'score_minimum': self.SCORE_MINIMUM}
        available_matches = getMatchesSupporter(
            supporter, per_page=24, match_exclusions=match_exclusions)

        if available_matches:
            matches_listing[self.MATCHING_SUGGESTIONS] = self._get_supporter_weekly_matches_list(
                available_matches)

    def _add_supporter_requests_received(self, matches_listing, supporter):
        today = date.today()
        last_week = today - timedelta(days=7)
        recent_received_requests = InterestedCTA.objects.filter(
            supporter=supporter.user_profile.company, supporter_is_interested=InterestedCTA.INITIAL_VALUE, created_at__gt=last_week, created_at__lt=today)

        if recent_received_requests:
            available_matches = getSupporterInterestMatches(
                supporter, recent_received_requests)
            matches_listing[self.REQUESTS_RECEIVED] = self._get_supporter_weekly_matches_list(
                available_matches)

    def _add_supporter_new_connections(self, matches_listing, supporter):
        today = date.today()
        last_week = today - timedelta(days=7)
        recent_accepted_requests = InterestedCTA.objects.filter(
            supporter=supporter.user_profile.company, state_of_interest=InterestedCTA.CONNECTED, updated_at__gte=last_week, updated_at__lt=today)

        if recent_accepted_requests:
            available_matches = getSupporterInterestMatches(
                supporter, recent_accepted_requests)
            matches_listing[self.NEW_CONNECTIONS] = self._get_supporter_weekly_matches_list(
                available_matches)

    def _notify_supporters(self):
        user_unsubscribed = Q(user_profile__metadata__isnull=False,
                              user_profile__metadata__key='mailjet.exclusion', user_profile__metadata__value='true')
        user_inactive = Q(user_profile__user__last_login__isnull=True)
        supporters = Supporter.objects.exclude(
            user_unsubscribed | user_inactive)

        # For testing purposes
        samples_amount = self.SAMPLES_TO_SEND

        for index, supporter in enumerate(supporters):
            uid = supporter.user_profile.company.uid
            email = self.test_email or supporter.user_profile.user.email
            matches_listing = {}

            # New Matching Suggestions
            self._add_supporter_matching_suggestions(
                matches_listing, supporter)

            # New Requests Received
            self._add_supporter_requests_received(
                matches_listing, supporter)

            # New Connections
            self._add_supporter_new_connections(
                matches_listing, supporter)

            # Make sure we don't surpass limit
            self._check_weekly_limit(matches_listing)

            # Notify Supporter
            if matches_listing:
                sendWeeklyDigest(email, uid, **matches_listing)

                if self.test_email:
                    samples_amount -= 1
                    print("\r")
                    print(supporter.user_profile.user.email)
                    print("\n")

            # When there are no more samples needed, stop execution
            if samples_amount == 0:
                break

    def add_arguments(self, parser):
        parser.add_argument(
            '-t', '--test', help='Test weekly digest to specific email')

    def handle(self, *args, **options):
        """
        Divio currently does not support scheduling weekly
        cron jobs so we'll need to run this everyday and
        check if today is the defined day to trigger. 🤦‍♂️
        """
        self.test_email = options.get('test', None)

        in_test_mode = self.test_email is not None
        is_monday = date.today().weekday() == 0

        if in_test_mode or is_monday:
            self._notify_entrepreneurs()
            self._notify_supporters()
