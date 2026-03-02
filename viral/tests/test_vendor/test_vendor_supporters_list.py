from datetime import date, datetime, timedelta
from os import urandom

from allauth.utils import get_user_model
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from jsonschema import validate
from rest_framework import status

from shared.utils import AbacaAPITestCase
from viral.models import Affiliate, Company, Location, UserProfile
from matching.models import Supporter

from viral.tests.schemas.vendor_supporters_schema import LIST_SCHEMA


class TestVendorSupportersList(AbacaAPITestCase):
    """
    Test listing supporters:
    * 1 - Without admin token
    * 2 - Without filters (and validating schema)
    * 3 - With date filters
    * 3.1 - created_since todays date
    * 3.2 - created_since tomorrows date
    * 3.3 - created_until todays date
    * 3.4 - created_until yesterdays date
    * 4 - With company location filters
    * 4.1 - Containing a shared country
    * 4.2 - Containing a unique country
    * 4.3 - Containing a unique city
    * 4.4 - Containing a unique region
    * 4.5 - Containing an unexisting location
    * 5 - With supporter location of interest filter
    * 5.1 - Containing a country of interest
    * 5.2 - Containing a city of interest
    * 5.3 - Containing a region of interest
    """

    ENDPOINT = reverse('vendor_list_supporters')

    SHARED_COUNTRY = 'Portugal'
    UNIQUE_COUNTRY = 'United States'
    UNIQUE_CITY = 'Porto'
    UNIQUE_REGION = 'Bonfim'

    SUPPORTERS = [
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

        for supporter in self.SUPPORTERS:
            self._create_abaca_user(supporter)

    def _create_affiliate(self):
        affiliate = {
            'name': 'Testing Affiliate',
            'shortcode': 'testaf',
            'email': 'testaf@mail.com',
            'website': 'http://affiliate.com',
            'logo': 'http://affiliate.com/logo.png'
        }

        self.affiliate = Affiliate.objects.create(**affiliate)

    def _create_abaca_user(self, supporter):
        self._create_affiliate()

        user_uid = urandom(5).hex()
        user = ['user_{0}'.format(
            user_uid), 'user_{0}@mail.com'.format(user_uid)]
        user = get_user_model().objects.create_user(*user)

        location = {
            'formatted_address': 'Neverland',
            'latitude': 0.0,
            'longitude': 0.0,
            **supporter['location']
        }
        location = Location.objects.create(**location)

        company = {
            'name': 'User Company',
            'about': 'A cool company',
            'website': 'https://user-company.com',
            'type': Company.SUPPORTER
        }
        company = Company.objects.create(**company)
        company.locations.set([location])
        company.created_at = supporter['created_at']
        company.save()

        user_profile = {
            'user': user,
            'company': company,
            'source': self.affiliate
        }
        user_profile = UserProfile.objects.create(**user_profile)

        supporter = {
            'name': 'User Supporter',
            'email': user.email,
            'investing_level_range': [1, 4],
            'user_profile': user_profile
        }
        supporter = Supporter.objects.create(**supporter)
        supporter.locations.set([location])

    def test_listing_without_admin_token(self):
        # 1 - Without admin token
        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_listing_without_filters(self):
        # 2 - Without filters (and validating schema)
        self.client.force_authenticate(self.super_user)

        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(bool(response.data))
        validate(instance=response.data, schema=LIST_SCHEMA)

    def _fetch_supporters(self, options):
        self.client.force_authenticate(self.super_user)
        response = self.client.get(self.ENDPOINT, options)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response

    def test_created_since_todays_date(self):
        # 3.1 - created_since todays date
        today = date.today().strftime("%Y-%m-%d")
        response = self._fetch_supporters({'created_since': today})

        current_date = date.today().strftime("%Y-%m-%d %H:%M:%S")
        all_supporters_since_today = all(
            parse_datetime(supporter['created_at']) >= parse_datetime(current_date) for supporter in response.data)
        self.assertTrue(all_supporters_since_today)

    def test_created_since_tomorrows_date(self):
        # 3.2 - created_since tomorrows date
        tomorrow = date.today() + timedelta(days=1)
        response = self._fetch_supporters({'created_since': tomorrow})

        upcoming_date = tomorrow.strftime("%Y-%m-%d %H:%M:%S")
        all_supporters_since_tomorrow = all(
            parse_datetime(supporter['created_at']) >= parse_datetime(upcoming_date) for supporter in response.data)
        self.assertTrue(all_supporters_since_tomorrow)

    def test_created_until_todays_date(self):
        # 3.3 - created_until todays date
        today = date.today().strftime("%Y-%m-%d")
        response = self._fetch_supporters({'created_until': today})

        current_date = date.today().strftime("%Y-%m-%d %H:%M:%S")
        all_supporters_until_today = all(
            parse_datetime(supporter['created_at']) <= parse_datetime(current_date) for supporter in response.data)
        self.assertTrue(all_supporters_until_today)

    def test_created_until_yesterdays_date(self):
        # 3.4 - created_until yesterdays date
        yesterday = date.today() - timedelta(days=1)
        response = self._fetch_supporters({'created_until': yesterday})

        past_date = yesterday.strftime("%Y-%m-%d %H:%M:%S")
        all_supporters_until_yesterday = all(
            parse_datetime(supporter['created_at']) <= parse_datetime(past_date) for supporter in response.data)
        self.assertTrue(all_supporters_until_yesterday)

    def test_location_with_shared_country(self):
        # 4.1 - Containing a shared country
        response = self._fetch_supporters({'country': self.SHARED_COUNTRY})

        supporters_with_shared_country = all(
            supporter['location']['country'] == self.SHARED_COUNTRY for supporter in response.data)
        self.assertTrue(supporters_with_shared_country)
        self.assertTrue(len(response.data) > 1)

    def test_location_with_unique_country(self):
        # 4.2 - Containing a unique country
        response = self._fetch_supporters({'country': self.UNIQUE_COUNTRY})

        supporter_with_unique_country = all(
            supporter['location']['country'] == self.UNIQUE_COUNTRY for supporter in response.data)
        self.assertTrue(supporter_with_unique_country)
        self.assertTrue(len(response.data) == 1)

    def test_location_with_unique_city(self):
        # 4.3 - Containing a unique city
        response = self._fetch_supporters({'city': self.UNIQUE_CITY})

        supporter_with_unique_city = all(
            supporter['location']['city'] == self.UNIQUE_CITY for supporter in response.data)
        self.assertTrue(supporter_with_unique_city)
        self.assertTrue(len(response.data) == 1)

    def test_location_with_unique_region(self):
        # 4.4 - Containing a unique region
        response = self._fetch_supporters({'region': self.UNIQUE_REGION})

        supporter_with_unique_region = all(
            supporter['location']['region'] == self.UNIQUE_REGION for supporter in response.data)
        self.assertTrue(supporter_with_unique_region)
        self.assertTrue(len(response.data) == 1)

    def test_location_with_unexisting(self):
        # 4.5 - Empty results with unexisting location
        response = self._fetch_supporters({'country': 'Unexisting'})
        self.assertFalse(bool(response.data))

    def test_location_of_interest_with_country(self):
        # 5.1 - Containing a country of interest
        response = self._fetch_supporters({'icountry': self.SHARED_COUNTRY})

        found_supporters_with_country_of_interest = False
        for result in response.data:
            locations_of_interest = result['supporter']['locations_of_interest']
            found_supporters_with_country_of_interest = any(
                location['country'] == self.SHARED_COUNTRY for location in locations_of_interest)
            if not found_supporters_with_country_of_interest:
                break

        self.assertTrue(found_supporters_with_country_of_interest)

    def test_location_of_interest_with_city(self):
        # 5.2 - Containing a city of interest
        response = self._fetch_supporters({'icity': self.UNIQUE_CITY})

        found_supporters_with_city_of_interest = False
        for result in response.data:
            locations_of_interest = result['supporter']['locations_of_interest']
            found_supporters_with_city_of_interest = any(
                location['city'] == self.UNIQUE_CITY for location in locations_of_interest)
            if not found_supporters_with_city_of_interest:
                break

        self.assertTrue(found_supporters_with_city_of_interest)

    def test_location_of_interest_with_region(self):
        # 5.3 - Containing a region of interest
        response = self._fetch_supporters({'iregion': self.UNIQUE_REGION})

        found_supporters_with_region_of_interest = False
        for result in response.data:
            locations_of_interest = result['supporter']['locations_of_interest']
            found_supporters_with_region_of_interest = any(
                location['region'] == self.UNIQUE_REGION for location in locations_of_interest)
            if not found_supporters_with_region_of_interest:
                break

        self.assertTrue(found_supporters_with_region_of_interest)
