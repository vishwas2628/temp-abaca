import math
from datetime import date, datetime, timedelta
from os import urandom

from allauth.utils import get_user_model
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from jsonschema import validate
from rest_framework import status

from shared.utils import AbacaAPITestCase
from viral.models import Affiliate, Company, Location, UserProfile
from viral.tests.schemas.vendor_entrepreneurs_schema import LIST_SCHEMA


class TestVendorEntrepreneursList(AbacaAPITestCase):
    """
    Test listing entrepreneurs:
    * 1 - Without admin token
    * 2 - Without filters (and validating schema)
    * 3 - With date filters
    * 3.1 - created_since todays date
    * 3.2 - created_since tomorrows date
    * 3.3 - created_until todays date
    * 3.4 - created_until yesterdays date
    * 4 - With location filters
    * 4.1 - Containing a shared country
    * 4.2 - Containing a unique country
    * 4.3 - Containing a unique city
    * 4.4 - Containing a unique region
    * 4.5 - Containing an unexisting location
    * 5 - Pagination
    * 5.1 - Access first page (without page query)
    * 5.2 - Access last page
    * 5.3 - Access unexisting page
    """
    ENDPOINT = reverse('vendor_list_entrepreneurs')
    PAGINATION_SIZE = 50

    SHARED_COUNTRY = 'Portugal'
    UNIQUE_COUNTRY = 'United States'
    UNIQUE_CITY = 'Porto'
    UNIQUE_REGION = 'Bonfim'

    ENTREPRENEURS = [
        {
            'created_at': date.today(),
            'location': {
                'country': SHARED_COUNTRY,
                'city': UNIQUE_CITY,
                'region': UNIQUE_REGION
            }
        },
        {
            'created_at': date.today() + timedelta(days=1),
            'location': {
                'country': SHARED_COUNTRY,
                'city': 'Gondomar',
                'region': 'Valbom'
            }
        },
        {
            'created_at': date.today() - timedelta(days=1),
            'location': {
                'country': UNIQUE_COUNTRY,
                'city': 'New York',
                'region': 'Brooklyn'
            }
        }
    ]

    def setUp(self):
        super().setUp()
        self._create_super_user()

        for entrepreneur in self.ENTREPRENEURS:
            self._create_abaca_user(entrepreneur)

    def _create_affiliate(self):
        affiliate = {
            'name': 'Testing Affiliate',
            'shortcode': 'testaf',
            'email': 'testaf@mail.com',
            'website': 'http://affiliate.com',
            'logo': 'http://affiliate.com/logo.png'
        }

        self.affiliate = Affiliate.objects.create(**affiliate)

    def _create_abaca_user(self, entrepreneur):
        self._create_affiliate()

        user_uid = urandom(5).hex()
        user = ['user_{0}'.format(
            user_uid), 'user_{0}@mail.com'.format(user_uid)]
        self.user = get_user_model().objects.create_user(*user)

        location = {
            'formatted_address': 'Neverland',
            'latitude': 0.0,
            'longitude': 0.0,
            **entrepreneur['location']
        }
        self.location = Location.objects.create(**location)

        company = {
            'name': 'User Company',
            'about': 'A cool company',
            'website': 'https://user-company.com',
            'type': Company.ENTREPRENEUR
        }
        self.company = Company.objects.create(**company)
        self.company.locations.set([self.location])
        self.company.created_at = entrepreneur['created_at']
        self.company.save()

        user_profile = {
            'user': self.user,
            'company': self.company,
            'source': self.affiliate
        }
        self.user_profile = UserProfile.objects.create(**user_profile)

    def test_listing_without_admin_token(self):
        # 1 - Without admin token
        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_listing_without_filters(self):
        # 2 - Without filters
        self.client.force_authenticate(self.super_user)

        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(bool(response.data['results']))
        validate(instance=response.data['results'], schema=LIST_SCHEMA)

    def _fetch_entrepreneurs(self, options):
        self.client.force_authenticate(self.super_user)
        response = self.client.get(self.ENDPOINT, options)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response

    def test_created_since_todays_date(self):
        # 3.1 - created_since todays date
        today = date.today().strftime("%Y-%m-%d")
        response = self._fetch_entrepreneurs({'created_since': today})

        current_date = date.today().strftime("%Y-%m-%d %H:%M:%S")
        all_entrepreneurs_since_today = all(
            parse_datetime(entrepreneur['created_at']) >= parse_datetime(current_date) for entrepreneur in response.data['results'])
        self.assertTrue(all_entrepreneurs_since_today)

    def test_created_since_tomorrows_date(self):
        # 3.2 - created_since tomorrows date
        tomorrow = date.today() + timedelta(days=1)
        response = self._fetch_entrepreneurs({'created_since': tomorrow})

        upcoming_date = tomorrow.strftime("%Y-%m-%d %H:%M:%S")
        all_entrepreneurs_since_tomorrow = all(
            parse_datetime(entrepreneur['created_at']) >= parse_datetime(upcoming_date) for entrepreneur in response.data['results'])
        self.assertTrue(all_entrepreneurs_since_tomorrow)

    def test_created_until_todays_date(self):
        # 3.3 - created_until todays date
        today = date.today().strftime("%Y-%m-%d")
        response = self._fetch_entrepreneurs({'created_until': today})

        current_date = date.today().strftime("%Y-%m-%d %H:%M:%S")
        all_entrepreneurs_until_today = all(
            parse_datetime(entrepreneur['created_at']) <= parse_datetime(current_date) for entrepreneur in response.data['results'])
        self.assertTrue(all_entrepreneurs_until_today)

    def test_created_until_yesterdays_date(self):
        # 3.4 - created_until yesterdays date
        yesterday = date.today() - timedelta(days=1)
        response = self._fetch_entrepreneurs({'created_until': yesterday})

        past_date = yesterday.strftime("%Y-%m-%d %H:%M:%S")
        all_entrepreneurs_until_yesterday = all(
            parse_datetime(entrepreneur['created_at']) <= parse_datetime(past_date) for entrepreneur in response.data['results'])
        self.assertTrue(all_entrepreneurs_until_yesterday)

    def test_location_with_shared_country(self):
        # 4.1 - Containing a shared country
        response = self._fetch_entrepreneurs({'country': self.SHARED_COUNTRY})

        entrepreneurs_with_shared_country = all(
            entrepreneur['location']['country'] == self.SHARED_COUNTRY for entrepreneur in response.data['results'])
        self.assertTrue(entrepreneurs_with_shared_country)
        self.assertTrue(len(response.data['results']) > 1)

    def test_location_with_unique_country(self):
        # 4.2 - Containing a unique country
        response = self._fetch_entrepreneurs({'country': self.UNIQUE_COUNTRY})

        entrepreneur_with_unique_country = all(
            entrepreneur['location']['country'] == self.UNIQUE_COUNTRY for entrepreneur in response.data['results'])
        self.assertTrue(entrepreneur_with_unique_country)
        self.assertTrue(len(response.data['results']) == 1)

    def test_location_with_unique_city(self):
        # 4.3 - Containing a unique city
        response = self._fetch_entrepreneurs({'city': self.UNIQUE_CITY})

        entrepreneur_with_unique_city = all(
            entrepreneur['location']['city'] == self.UNIQUE_CITY for entrepreneur in response.data['results'])
        self.assertTrue(entrepreneur_with_unique_city)
        self.assertTrue(len(response.data['results']) == 1)

    def test_location_with_unique_region(self):
        # 4.4 - Containing a unique region
        response = self._fetch_entrepreneurs({'region': self.UNIQUE_REGION})

        entrepreneur_with_unique_region = all(
            entrepreneur['location']['region'] == self.UNIQUE_REGION for entrepreneur in response.data['results'])
        self.assertTrue(entrepreneur_with_unique_region)
        self.assertTrue(len(response.data['results']) == 1)

    def test_location_with_unexisting(self):
        # 4.5 - Empty results with unexisting location
        response = self._fetch_entrepreneurs({'country': 'Unexisting'})
        self.assertFalse(bool(response.data['results']))

    def test_pagination(self):
        self.client.force_authenticate(self.super_user)

        # Global variables reused across pagination tests
        self.results_count = 0
        self.total_pages = 0
        self.has_multiple_pages = False

        # 5.1 - Access first page
        self._test_pagination_first_page()

        # 5.2 - Access last page
        self._test_pagination_last_page()

        # 5.3 - Access unexisting page
        self._test_pagination_unexisting_page()

    def _test_pagination_first_page(self):
        response = self.client.get(self.ENDPOINT)
        results = response.data['results']

        self.results_count = response.data['count']
        self.total_pages = math.ceil(
            float(self.results_count) / self.PAGINATION_SIZE)
        self.has_multiple_pages = len(results) < self.results_count

        expected_results_length = self.PAGINATION_SIZE if self.has_multiple_pages else self.results_count

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(results), expected_results_length)
        self.assertEqual(response.data['previous'], None)
        if self.has_multiple_pages:
            self.assertNotEqual(response.data['next'], None)

    def _test_pagination_last_page(self):
        # Only makes sense testing the last page, if there are multiple pages
        if (self.has_multiple_pages):
            last_page_url = self.ENDPOINT + '?page=' + self.total_pages
            response = self.client.get(last_page_url)

            expected_results_length = self.results_count % self.PAGINATION_SIZE

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(results), expected_results_length)
            self.assertNotEqual(response.data['previous'], None)
            self.assertEqual(response.data['next'], None)

    def _test_pagination_unexisting_page(self):
        unexisting_page_url = self.ENDPOINT + \
            '?page=' + str(self.total_pages + 1)
        response = self.client.get(unexisting_page_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
