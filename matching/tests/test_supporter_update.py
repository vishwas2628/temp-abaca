import uuid
from unittest import mock

from allauth.account.models import EmailAddress
from allauth.utils import get_user_model
from django.urls import reverse
from matching.models import Supporter, SupporterType
from psycopg2.extras import NumericRange
from rest_framework import status
from shared.utils import AbacaAPITestCase
from viral.models import (Company, Group, Location, LocationGroup, Sector,
                          UserProfile)


class TestSupporterUpdate(AbacaAPITestCase):
    """
    Test supporter update:
    * 1 - Without being authenticated
    * 2 - Without ownership
    * 3 - With unexisting supporter
    * 4 - With invalid data
    * 5 - Without individual sectors
    * 6 - With individual sectors
    * 7 - Without grouped sectors
    * 8 - With grouped sectors
    * 9 - Without locations
    * 10 - With locations (grouped)
    * 11 - With places (individual)
    """

    ENDPOINT = reverse('retrieve_or_update_supporter')

    SECTORS = ['Tourism', 'Education']
    SECTOR_GROUP_1 = 'Financial Services'
    SECTOR_GROUP_2 = 'Information Technology'
    GROUPED_SECTORS = {
        SECTOR_GROUP_1: ['Payments', 'Virtual Currency'],
        SECTOR_GROUP_2: ['Blockchain', 'Information Services'],
    }

    LOCATIONS = [
        {
            "region": "Ohio",
            "city": "North Canton",
            "longitude": -81.407049000000001,
            "country": "United States",
            "continent": "North America",
            "latitude": 40.883512199999998,
            "region_abbreviation": "OH",
            "formatted_address": "419 7th St NW, North Canton, OH 44720, USA"
        },
        {
            "region": "Virginia",
            "city": "Virginia Beach",
            "longitude": -76.147541000000004,
            "country": "United States",
            "continent": "North America",
            "latitude": 36.838299300000003,
            "region_abbreviation": "VA",
            "formatted_address": "Euclid Rd, Virginia Beach, VA 23462, USA"
        }
    ]
    LOCATION_GROUP_1 = 'Europe'
    LOCATION_GROUP_2 = 'European Union'
    GROUPED_LOCATIONS = {
        LOCATION_GROUP_1: [
            {
                "longitude": -3.4359730000000002,
                "country": "United Kingdom",
                "continent": "Europe",
                "latitude": 55.378050999999999,
                "formatted_address": "United Kingdom"
            },
            {
                "longitude": -8.2244539999999997,
                "country": "Portugal",
                "continent": "Europe",
                "latitude": 39.399872000000002,
                "formatted_address": "Portugal"
            }
        ],
        LOCATION_GROUP_2: [
            {
                "longitude": -8.2244539999999997,
                "country": "Portugal",
                "continent": "Europe",
                "latitude": 39.399872000000002,
                "formatted_address": "Portugal"
            },
            {
                "longitude": -3.7492200000000002,
                "country": "Spain",
                "continent": "Europe",
                "latitude": 40.463667000000001,
                "formatted_address": "Spain"
            }
        ]
    }

    def setUp(self):
        super().setUp()
        self._create_supporter_account()

    def _create_user(self):
        user = ['user', 'user@mail.com']
        self.user = get_user_model().objects.create_user(*user)

    def _create_company(self):
        company = {
            'name': 'User Company',
            'about': 'A cool company',
            'website': 'https://user-company.com',
            'type': Company.SUPPORTER,
            'access_hash': '1ab2c3'
        }
        self.company = Company.objects.create(**company)

    def _create_user_profile(self):
        user_profile = {
            'user': self.user,
            'company': self.company
        }
        self.user_profile = UserProfile.objects.create(**user_profile)

    def _create_supporter_type(self, name):
        return SupporterType.objects.create(name=name)

    def _create_sectors(self):
        for sector in self.SECTORS:
            Sector.objects.create(name=sector, uuid=uuid.uuid1())

        for group, sectors in self.GROUPED_SECTORS.items():
            created_group = Group.objects.create(name=group)

            for sector in sectors:
                new_sector = Sector.objects.create(name=sector, uuid=uuid.uuid1())
                new_sector.groups.set([created_group])

    def _create_locations(self):
        for location in self.LOCATIONS:
            Location.objects.create(**location)

        for group, locations in self.GROUPED_LOCATIONS.items():
            created_group = LocationGroup.objects.create(name=group)

            for location in locations:
                new_location = Location.objects.create(**location)
                new_location.groups.set([created_group])

    def _create_supporter_account(self):
        self._create_user()
        self._create_company()
        self._create_user_profile()

        self.supporter_type = self._create_supporter_type('Investor')
        self._create_sectors()
        self._create_locations()

        supporter = {
            'name': 'Testing Supporter',
            'about': 'A cool Supporter',
            'email': 'test@mail.com',
            'investing_level_range': [1, 4],
            'user_profile': self.user_profile
        }

        self.supporter = Supporter.objects.create(**supporter)
        self.supporter.types.set([self.supporter_type])

    def _create_other_supporter(self):
        other_user = get_user_model().objects.create_user('other_user', 'other_user@mail.com')
        other_company = Company.objects.create(name='Other', type=Company.SUPPORTER)
        other_user_profile = UserProfile.objects.create(user=other_user, company=other_company)
        other_supporter = {
            'name': 'Other Supporter',
            'about': 'Another Supporter',
            'email': 'test@mail.com',
            'investing_level_range': [1, 4],
            'user_profile': other_user_profile
        }

        self.other_supporter = Supporter.objects.create(**other_supporter)

    def _get_payload(self, valid_data=True, optional_data=True):
        if not valid_data:
            return {
                'name': ['invalid-name'],
                'types': [0, 'invalid-types', False],
                'otherType': '',
                'sectors': [0, 'invalid-sectors', False],
                'grouped_sectors': ['invalid-grouped-sectors', 0, {'group': 0, 'sectors': [0]}],
                'locations': ['invalid-locations', 0, {'group': 0, 'locations': [0]}],
                'locations_weight': 0,
                'places': [{'invalid': True}, None],
                'investing_level_range': 0,
            }

        self.new_supporter_type = self._create_supporter_type('Mentor')
        self.other_supporter_type_value = 'Lender'
        supporter = {
            'name': 'Testing Renamed Supporter',
            'types': [self.new_supporter_type.id],
            'investing_level_range': [3, 6],
        }

        if optional_data:
            supporter['otherType'] = self.other_supporter_type_value

            ungrouped_sector = Sector.objects.filter(groups__isnull=True).first()
            supporter['sectors'] = [ungrouped_sector.id]

            grouped_sector = Sector.objects.filter(groups__isnull=False).first()
            grouped_sector_group = grouped_sector.groups.first()
            supporter['grouped_sectors'] = [{
                'group': grouped_sector_group.id,
                'sectors': [grouped_sector.id]
            }]

            grouped_location = Location.objects.filter(groups__isnull=False).first()
            grouped_location_group = grouped_location.groups.first()
            supporter['locations'] = [{
                'group': grouped_location_group.id,
                'locations': [grouped_location.id]
            }]
            supporter['places'] = ['foo_id', 'bar_id']

        return supporter

    def test_update_without_being_authenticated(self):
        # 1 - Test update without being authenticated
        payload = self._get_payload()
        response = self.client.patch(self.ENDPOINT, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_without_ownership(self):
        # 2 - Test update without ownership
        self._create_other_supporter()
        self.client.force_authenticate(user=self.user)

        payload = self._get_payload()
        other_supporter_url = self.ENDPOINT + '/%s' % self.other_supporter.id
        response = self.client.patch(other_supporter_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_with_unexisting_supporter(self):
        # 3 - Test with unexisting supporter
        self.client.force_authenticate(user=self.user)
        payload = self._get_payload()
        unexisting_supporter_url = self.ENDPOINT + '/999'
        response = self.client.patch(unexisting_supporter_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_with_invalid_data(self):
        # 4 - Test with invalid data
        self.client.force_authenticate(user=self.user)
        payload = self._get_payload(valid_data=False)
        response = self.client.patch(self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']

        # TODO: Add remaning invalid checks
        has_invalid_name = errors['name'][0]['code'] == 'invalid'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(has_invalid_name)

    def test_without_individual_sectors(self):
        # 5 - Test without individual sectors
        # TODO: Add test
        pass

    def test_with_individual_sectors(self):
        # 6 - Test with individual sectors
        # TODO: Add test
        pass

    def test_without_grouped_sectors(self):
        # 7 - Test without grouped sectors
        # TODO: Add test
        pass

    def test_with_grouped_sectors(self):
        # 8 - Test with grouped sectors
        # TODO: Add test
        pass

    def test_without_locations(self):
        # 9 - Test without locations
        # TODO: Add test
        pass

    def test_with_locations(self):
        # 10 - Test with locations (grouped)
        # TODO: Add test
        pass

    def test_with_places(self):
        # 11 - Test with places (individual)
        # TODO: Add test
        pass
