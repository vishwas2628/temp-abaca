import uuid
from unittest import mock

from allauth.account.models import EmailAddress
from allauth.utils import get_user_model
from django.urls import reverse
from matching.models import SupporterType
from rest_framework import status
from shared.utils import AbacaAPITestCase
from viral.models import (Affiliate, Group, Location, LocationGroup,
                          Network, Sector)


class TestSupporterRegistration(AbacaAPITestCase):
    """
    Test supporter registration:
    * 1 - Without an email
    * 2 - With a invalid email
    * 3 - With a existing email
    * 4 - Without password
    * 5 - Without a company
    * 6 - With invalid company data
    * 7 - Without an affiliate
    * 8 - With a unexisting affiliate
    * 9 - Without a supporter
    * 10 - With invalid supporter data
    * 11 - Without supporter optional fields:
    * (sectors, grouped_sectors, locations, places, otherType)
    * 12 - With all supporter fields
    """

    ENDPOINT = reverse('register_supporters')
    EXISTING_EMAIL = 'existing@supporter.com'

    def setUp(self):
        super().setUp()
        self._create_affiliate()

    def _create_affiliate(self):
        affiliate = {
            'name': 'Testing Affiliate',
            'shortcode': 'testaf',
            'email': 'testaf@mail.com',
            'website': 'http://affiliate.com',
            'logo': 'http://affiliate.com/logo.png'
        }

        self.affiliate = Affiliate.objects.create(**affiliate)

    def _create_network(self):
        network = {
            'name': 'Testing Network',
            'slug': 'testingn',
            'email': 'testn@mail.com',
            'website': 'http://network.com',
            'logo': 'http://network.com/logo.png'
        }

        self.network = Network.objects.create(**network)

    def _create_existing_user(self):
        user = ['existing_user', self.EXISTING_EMAIL]
        self.existing_user = get_user_model().objects.create_user(*user)
        EmailAddress.objects.create(
            user=self.existing_user,
            email=self.EXISTING_EMAIL, primary=True,
            verified=True)

    def _create_supporter_type(self):
        self.supporter_type = SupporterType.objects.create(name='Investor')

    def _create_sector(self):
        self.sector = Sector.objects.create(name='Finance', uuid=uuid.uuid1())

    def _create_grouped_sector(self):
        self.group = Group.objects.create(name='Healthcare')
        self.grouped_sector = Sector.objects.create(name='Biopharma', uuid=uuid.uuid1())
        self.grouped_sector.groups.set([self.group.id])

    def _create_grouped_location(self):
        self.location_group = LocationGroup.objects.create(name='Europe')
        self.location = Location.objects.create(
            continent='Europe',
            country='Portugal',
            formatted_address='Portugal',
            latitude=0.0,
            longitude=0.0,
        )
        self.location.groups.set([self.location_group.id])

    def _get_company_payload(self, valid=True):
        self._create_network()

        return {
            'name': 'User Company',
            'website': 'https://user-company.com',
            'networks': [self.network.id],
            'location': {
                'formatted_address': 'Neverland',
                'latitude': 0.0,
                'longitude': 0.0
            }
        } if valid else {
            'name': ['invalid-name'],
            'website': 'invalid-website',
            'location': 'invalid-location',
            'networks': 'invalid-networks',
        }

    def _get_supporter_payload(self, valid=True, optional=True):
        if not valid:
            return {
                'name': ['invalid-name'],
                'types': [0, 'invalid-types', False],
                'otherType': '',
                'sectors': [0, 'invalid-sectors', False],
                'grouped_sectors': ['invalid-grouped-sectors', 0, {'group': 0, 'sectors': [0]}],
                'locations': ['invalid-locations', 0, {'group': 0, 'locations': [0]}],
                'places': [{'invalid': True}, None],
                'investing_level_range': 0,
            }

        self._create_supporter_type()
        self._create_sector()
        self._create_grouped_sector()
        self._create_grouped_location()

        supporter = {
            'name': 'User Supporter',
            'types': [self.supporter_type.id],
            'investing_level_range': [3, 6],
        }

        if optional:
            supporter['otherType'] = None
            supporter['sectors'] = [self.sector.id]
            supporter['grouped_sectors'] = [{
                'group': self.group.id,
                'sectors': [self.grouped_sector.id]
            }]
            supporter['locations'] = [{
                'group': self.location_group.id,
                'locations': [self.location.id]
            }]
            supporter['places'] = ['foo_id', 'bar_id']

        return supporter

    def _get_payload(self, with_email=True, valid_email=True, existing_email=False, with_password=True,
                     with_company=True, valid_company=True, with_affiliate=True, valid_affiliate=True,
                     with_supporter=True, valid_supporter=True, with_optional_fields=True):
        payload = {}

        if with_email:
            if existing_email:
                self._create_existing_user()
                payload['email'] = self.EXISTING_EMAIL
            else:
                payload['email'] = 'user@supporter.com' if valid_email else 'invalid-email'

        if with_password:
            payload['password1'] = '12345678'
            payload['password2'] = '12345678'

        if with_company:
            payload['company'] = self._get_company_payload(valid=valid_company)

        if with_affiliate:
            payload['affiliate'] = self.affiliate.id if valid_affiliate else 0

        if with_supporter:
            payload['supporter'] = self._get_supporter_payload(valid=valid_supporter, optional=with_optional_fields)

        return payload

    def _get_mocked_google_location(self, place_id):
        return [{
            'formatted_address': 'Portugal',
            'address_components': [{
                'long_name': 'Portugal',
                'short_name': 'PT',
                'types': ['country']
            }],
            'geometry': {
                'location': {'lat': 0.0, 'lng': 0.0}
            }
        }]

    def test_registering_without_an_email(self):
        # 1 - Test registering without an email
        payload = self._get_payload(with_email=False)
        response = self.client.post(
            self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']
        is_missing_email = 'email' in errors and errors['email'][0]['code'] == 'required'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(is_missing_email)

    def test_registering_with_a_invalid_email(self):
        # 2 - Test registering with a invalid email
        payload = self._get_payload(valid_email=False)
        response = self.client.post(
            self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']
        has_invalid_email = 'email' in errors and errors['email'][0]['code'] == 'invalid'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(has_invalid_email)

    def test_registering_with_a_existing_email(self):
        # 3 - Test registering with a existing email
        payload = self._get_payload(existing_email=True)
        response = self.client.post(self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']
        email_already_exists = 'email' in errors and errors['email'][0]['code'] == 'unique'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(email_already_exists)

    def test_registering_without_password(self):
        # 4 - Test registering without a password
        payload = self._get_payload(with_password=False)
        response = self.client.post(self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']
        is_missing_password = 'password1' in errors and errors['password1'][0]['code'] == 'required'
        is_missing_password_confirmation = 'password2' in errors and errors['password2'][0]['code'] == 'required'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(is_missing_password)
        self.assertTrue(is_missing_password_confirmation)

    def test_registering_without_a_company(self):
        # 5 - Test registering without a company
        payload = self._get_payload(with_company=False)
        response = self.client.post(self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']
        is_missing_company = 'company' in errors and errors['company'][0]['code'] == 'required'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(is_missing_company)

    def test_registering_with_invalid_company_data(self):
        # 6 - Test registering with invalid company data
        payload = self._get_payload(valid_company=False)
        response = self.client.post(self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']
        has_invalid_location = 'company' in errors and errors['company']['location']['non_field_errors'][0]['code'] == 'invalid'
        has_invalid_name = 'company' in errors and errors['company']['name'][0]['code'] == 'invalid'
        has_invalid_website = 'company' in errors and errors['company']['website'][0]['code'] == 'invalid'
        has_invalid_networks = 'company' in errors and errors['company']['networks'][0]['code'] == 'not_a_list'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(has_invalid_location)
        self.assertTrue(has_invalid_name)
        self.assertTrue(has_invalid_website)
        self.assertTrue(has_invalid_networks)

    def test_registering_without_an_affiliate(self):
        # 7 - Test registering without an affiliate
        payload = self._get_payload(with_affiliate=False)
        response = self.client.post(self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']
        is_missing_affiliate = 'affiliate' in errors and errors['affiliate'][0]['code'] == 'required'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(is_missing_affiliate)

    def test_registering_with_a_unexisting_affiliate(self):
        # 8 - Test registering with a unexisting affiliate
        payload = self._get_payload(valid_affiliate=False)
        response = self.client.post(self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']
        is_invalid_affiliate = 'affiliate' in errors and errors['affiliate'][0]['code'] == 'does_not_exist'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(is_invalid_affiliate)

    def test_registering_without_a_supporter(self):
        # 9 - Test registering without a supporter
        payload = self._get_payload(with_supporter=False)
        response = self.client.post(self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']
        is_missing_supporter = 'supporter' in errors and errors['supporter'][0]['code'] == 'required'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(is_missing_supporter)

    def test_registering_with_invalid_supporter_data(self):
        # 10 - Test registering with invalid supporter data
        payload = self._get_payload(valid_supporter=False)
        response = self.client.post(self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']

        # TODO: Add helper method to loop all response errors and check if contains error codes (invalid, required, etc)
        has_invalid_name = errors['supporter']['name'][0]['code'] == 'invalid'
        types_do_not_exist = errors['supporter']['types'][0]['code'] == 'does_not_exist'
        missing_other_type_value = errors['supporter']['otherType'][0]['code'] == 'blank'
        has_invalid_investing_range = errors['supporter']['investing_level_range'][0]['code'] == 'invalid'
        has_invalid_places = errors['supporter']['places']['0'][0]['code'] == 'invalid'
        has_null_places = errors['supporter']['places']['1'][0]['code'] == 'null'

        has_invalid_locations = errors['supporter']['locations'][0]['non_field_errors'][0]['code'] == 'invalid'
        locations_do_not_exist = errors['supporter']['locations'][2]['locations'][0]['code'] == 'does_not_exist'
        locations_group_doesnt_exist = errors['supporter']['locations'][2]['group'][0]['code'] == 'does_not_exist'

        sectors_do_not_exist = errors['supporter']['sectors'][0]['code'] == 'does_not_exist'
        has_invalid_grouped_sectors = errors['supporter']['grouped_sectors'][0]['non_field_errors'][0]['code'] == 'invalid'
        grouped_sectors_do_not_exist = errors['supporter']['grouped_sectors'][2]['sectors'][0]['code'] == 'does_not_exist'
        sectors_group_doesnt_exist = errors['supporter']['grouped_sectors'][2]['group'][0]['code'] == 'does_not_exist'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(has_invalid_name)
        self.assertTrue(types_do_not_exist)
        self.assertTrue(missing_other_type_value)
        self.assertTrue(has_invalid_investing_range)

        self.assertTrue(has_invalid_places)
        self.assertTrue(has_null_places)

        self.assertTrue(has_invalid_locations)
        self.assertTrue(locations_do_not_exist)
        self.assertTrue(locations_group_doesnt_exist)

        self.assertTrue(sectors_do_not_exist)
        self.assertTrue(has_invalid_grouped_sectors)
        self.assertTrue(grouped_sectors_do_not_exist)
        self.assertTrue(sectors_group_doesnt_exist)

    def test_registering_without_optional_fields(self):
        # 11 - Test registering without supporter optional fields
        payload = self._get_payload(with_optional_fields=False)
        response = self.client.post(self.ENDPOINT, payload, format='json')

        has_company_id = 'company' in response.data and type(response.data['company']) == int
        has_supporter_id = 'supporter' in response.data and type(response.data['supporter']) == int
        has_token = 'key' in response.data and type(response.data['key']) == str

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertTrue(has_company_id)
        self.assertTrue(has_supporter_id)
        self.assertTrue(has_token)

    @mock.patch('matching.serializers.fetch_google_location')
    def test_registering_with_all_fields(self, location_mock):
        # 12 - Test registering with all fields
        location_mock.side_effect = self._get_mocked_google_location
        payload = self._get_payload()
        response = self.client.post(self.ENDPOINT, payload, format='json')

        has_company_id = 'company' in response.data and type(response.data['company']) == int
        has_supporter_id = 'supporter' in response.data and type(response.data['supporter']) == int
        has_token = 'key' in response.data and type(response.data['key']) == str

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertTrue(has_company_id)
        self.assertTrue(has_supporter_id)
        self.assertTrue(has_token)
