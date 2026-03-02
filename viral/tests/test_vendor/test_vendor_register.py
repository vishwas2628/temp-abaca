import json
from os import getenv
from random import randint
from unittest import mock
from urllib.parse import quote_plus, urlparse, parse_qs

from allauth.utils import get_user_model
from django.urls import reverse
from rest_framework import status

from shared.utils import AbacaAPITestCase, get_uri_scheme
from viral.models import (Affiliate, Company, Location, UserProfile,
                          UserVendor, Vendor)


class TestVendorRegister(AbacaAPITestCase):
    """
    Test registering a vendor's user:
    * 1 - With a unexisting vendor
    * 2 - With a registered vendor user
    * 2.1 - Not containing a usable password
    * 2.2 - Containing a usable password
    * 3 - With a registered user on Abaca
    * 3.1 - Containing an existing email
    * 3.2 - Containing an existing vendor user but with a different vendor
    * 4 - With a unregistered vendor user
    * 4.1 - Containing a logo to upload
    * 4.1.1 - Using a valid URL
    * 4.1.2 - Using an invalid URL
    * 4.2 - Containing an address to fetch via Google Places
    * 4.2.1 - Using a valid address
    * 4.2.2 - Using an invalid address
    """

    ENDPOINT = reverse('vendor_assessment')
    VENDOR_USER_ID = '1ab2c3'
    NEW_VENDOR_USER_ID = '4d5f6g'
    REDIRECT_BASE = f"{get_uri_scheme()}{getenv('APP_BASE_URL')}"
    LOGO_PATH = 'logo.png'
    LOGO_INVALID_PATH = 'invalid-logo.png'
    VALID_ADDRESS = 'Porto, Portugal'
    INVALID_ADDRESS = 'Paradise Avenue'
    SAFE_FILESIZE_IN_BYTES = 2097152  # 2MB
    DANGEROUS_FILESIZE_IN_BYTES = 6291456  # 6MB

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

    def _create_vendor(self):
        vendor = {
            'name': 'Vendor',
            'endpoint': 'https://vendor.com',
            'cors_origins': ['localhost'],
            'uuid': randint(100, 999)
        }

        self.vendor = Vendor.objects.create(**vendor)

    def _create_abaca_user(self):
        user = ['user', 'user@mail.com']
        self.user = get_user_model().objects.create_user(*user)

        location = {
            'formatted_address': 'Neverland',
            'latitude': 0.0,
            'longitude': 0.0
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

        user_profile = {
            'user': self.user,
            'company': self.company,
            'source': self.affiliate
        }
        self.user_profile = UserProfile.objects.create(**user_profile)

    def _create_vendor_user(self, new_vendor_user=False):
        user_vendor = {
            'user_vendor': self.vendor,
            'user_profile': self.user_profile
        }
        user_vendor['user_id'] = self.NEW_VENDOR_USER_ID if new_vendor_user else self.VENDOR_USER_ID
        self.user_vendor = UserVendor.objects.create(**user_vendor)

    def _get_payload(self, with_valid_vendor=True, with_logo=False, valid_logo=True, with_address=False,
                     valid_address=True, new_email=True):
        payload = {
            'company': {
                'name': 'User Company',
                'about': 'A cool company',
                'website': 'https://company.com'
            },
            'vendor_user_id': self.VENDOR_USER_ID,
            'affiliate': self.affiliate.id,
        }

        payload['vendor_uuid'] = self.vendor.uuid if with_valid_vendor else 0
        payload['email'] = 'user@vendor.com' if new_email else self.user.email

        if with_logo:
            payload['logo'] = 'https://company.com/'
            payload['logo'] += self.LOGO_PATH if valid_logo else self.LOGO_INVALID_PATH

        if with_address:
            payload['address'] = self.VALID_ADDRESS if valid_address else self.INVALID_ADDRESS

        return payload

    def _get_assessment_route(self, affiliate_id, company_token):
        target = self.REDIRECT_BASE + '/entrepreneurs'
        query_params = '?a={affiliate_id}&token={company_token}&l={skip_landing}'.format(
            affiliate_id=affiliate_id, company_token=company_token, skip_landing=1)
        return target + query_params

    def _get_login_route(self, email):
        target = self.REDIRECT_BASE + '/auth/login'
        safe_uri_email = quote_plus(email)
        return target + '?email={email}'.format(email=safe_uri_email)

    def _mocked_logo_response(self, *args, **kwargs):
        # Get logo URL by checking if it contains the path substring
        logo = args[0] if len(args) and self.LOGO_PATH in args[0] else None

        if logo:
            has_valid_logo = self.LOGO_INVALID_PATH not in logo
            logo_response_code = status.HTTP_200_OK if has_valid_logo else status.HTTP_404_NOT_FOUND
            mocked_response = mock.Mock()
            mocked_response.status_code = logo_response_code
            mocked_response.headers = {
                'content-length': self.SAFE_FILESIZE_IN_BYTES if has_valid_logo else self.DANGEROUS_FILESIZE_IN_BYTES,
                'content-type': 'image/jpeg' if has_valid_logo else 'video/mp4'
            }
            mocked_response.iter_content.return_value = []
            return mocked_response
        else:
            self.fail("Missing logo url")

    def _mocked_location_response(self, *args, **kwargs):
        address = args[0] if len(args) else None

        if address:
            has_valid_address = self.INVALID_ADDRESS not in address
            location_response_code = status.HTTP_200_OK if has_valid_address else status.HTTP_404_NOT_FOUND
            return [{
                'formatted_address': self.VALID_ADDRESS,
                'geometry': {
                    'location': {'lat': 0.0, 'lng': 0.0}
                }
            }] if has_valid_address else []
        else:
            self.fail("Missing address")

    def test_registering_with_unexisting_vendor(self):
        # 1 - Test registering with an unexisting vendor
        payload = self._get_payload(with_valid_vendor=False)
        response = self.client.post(self.ENDPOINT, payload, format='json', HTTP_ORIGIN='localhost')
        self.assertEquals(response.status_code, 403)

    def test_registering_with_registered_vendor_user(self):
        # 2 - Test registering with a registered vendor user
        self._create_vendor()
        self._create_abaca_user()
        self._create_vendor_user()
        payload = self._get_payload()

        # 2.1 - Not containing a usable password
        response = self.client.post(self.ENDPOINT, payload, format='json', HTTP_ORIGIN='localhost')
        assessment_url = self._get_assessment_route(
            self.affiliate.id, self.company.access_hash)
        self.assertRedirects(response, assessment_url,
                             status_code=302, fetch_redirect_response=False)

        # 2.2 - Containing a usable password
        self.user.set_password('secret')
        self.user.save()
        response = self.client.post(self.ENDPOINT, payload, format='json', HTTP_ORIGIN='localhost')
        login_url = self._get_login_route(self.user.email)
        self.assertRedirects(response, login_url,
                             status_code=302, fetch_redirect_response=False)

    def test_registering_with_abaca_user(self):
        # 3 - Test registering with a registered user on Abaca
        self._create_vendor()
        self._create_abaca_user()
        payload = self._get_payload(new_email=False)

        # 3.1 - Containing an existing email
        response = self.client.post(self.ENDPOINT, payload, format='json', HTTP_ORIGIN='localhost')
        self.assertEquals(response.status_code, 400)
        self.assertTrue(
            any(error['code'] == 'unique' for error in response.data['errors']['email']))

        # 3.2 - Containing an existing vendor user but with a different vendor
        self._create_vendor()
        self._create_vendor_user(new_vendor_user=True)
        payload['vendor_user_id'] = self.NEW_VENDOR_USER_ID
        response = self.client.post(self.ENDPOINT, payload, format='json', HTTP_ORIGIN='localhost')
        login_route = self._get_login_route(self.user.email)
        self.assertRedirects(response, login_route,
                             status_code=302, fetch_redirect_response=False)

    def _register_new_vendor_user(self, options):
        self._create_vendor()
        payload = self._get_payload(**options)
        response = self.client.post(self.ENDPOINT, data=json.dumps(payload),
                                    content_type='application/json', HTTP_ORIGIN='localhost')
        url_parsed = urlparse(response.url)
        company_token = parse_qs(url_parsed.query)['token'][0]
        company = Company.objects.get(access_hash=company_token)
        assessment_route = self._get_assessment_route(
            self.affiliate.id, company_token)
        self.assertRedirects(response, assessment_route,
                             status_code=302, fetch_redirect_response=False)
        return company

    @mock.patch('viral.serializers.requests.head')
    @mock.patch('viral.serializers.requests.get')
    def test_registering_containing_valid_logo(self, logo_info_mock, logo_file_mock):
        logo_info_mock.side_effect = logo_file_mock.side_effect = self._mocked_logo_response

        # 4.1.1 - Containing a valid logo to upload
        company = self._register_new_vendor_user(
            {'with_logo': True, 'valid_logo': True})
        self.assertTrue(bool(company.logo))

    @mock.patch('viral.serializers.requests.head')
    @mock.patch('viral.serializers.requests.get')
    def test_registering_containing_invalid_logo(self, logo_info_mock, logo_file_mock):
        logo_info_mock.side_effect = logo_file_mock.side_effect = self._mocked_logo_response

        # 4.1.2 - Containing an invalid logo to upload
        self._create_vendor()
        payload = self._get_payload(with_logo=True, valid_logo=False)
        response = self.client.post(self.ENDPOINT, data=json.dumps(payload),
                                    content_type='application/json', HTTP_ORIGIN='localhost')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.json()['errors']
        self.assertTrue(errors[0]['code'] == 'invalid_logo')

    @mock.patch('viral.serializers.fetch_google_location')
    def test_registering_containing_valid_address(self, location_mock):
        location_mock.side_effect = self._mocked_location_response

        # 4.2.1 - Containing a valid address
        company = self._register_new_vendor_user(
            {'with_address': True, 'valid_address': True})
        self.assertTrue(company.locations.exists())

    @mock.patch('viral.serializers.fetch_google_location')
    def test_registering_containing_invalid_address(self, location_mock):
        location_mock.side_effect = self._mocked_location_response

        # 4.2.2 - Containing an invalid address
        company = self._register_new_vendor_user(
            {'with_address': True, 'valid_address': False})
        self.assertFalse(company.locations.exists())
