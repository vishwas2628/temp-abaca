from allauth.utils import get_user_model
from django.urls import reverse
from jsonschema import validate
from rest_framework import status

from grid.models import Assessment, Level, LevelGroup
from matching.models import QuestionBundle, Supporter
from shared.utils import AbacaAPITestCase
from viral.models import (Affiliate, AffiliateProgramEntry, Company, Location,
                          UserProfile)

from viral.tests.schemas.affiliate_submissions_schema import LIST_SCHEMA, DETAIL_SCHEMA


class TestVendorAffiliateSubmissions(AbacaAPITestCase):
    """
    Test affiliate submissions:
    * 1 - Without admin token
    * 2 - Listing affiliate submissions without none
    * 3 - Listing affiliate submissions
    * 4 - With affiliate id and submission id
    """

    def setUp(self):
        super().setUp()
        self._create_super_user()
        self._create_affiliate()
        self._create_abaca_user()
        self._create_assessment()
        self._create_supporter()
        self._create_question_bundle()

    def _get_endpoint(self, affiliate_id, submission_id=None):
        parameters = {'affiliate_id': affiliate_id}
        if submission_id:
            parameters['pk'] = submission_id
        return reverse('get_affiliates_submissions', kwargs=parameters)

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
            'type': Company.ENTREPRENEUR,
            'access_hash': '1ab2c3'
        }
        self.company = Company.objects.create(**company)
        self.company.locations.set([self.location])

        user_profile = {
            'user': self.user,
            'company': self.company,
            'source': self.affiliate
        }
        self.user_profile = UserProfile.objects.create(**user_profile)

    def _create_assessment_level(self):
        level_group, created = LevelGroup.objects.get_or_create(
            slug="entrepreneurs")
        level = {
            'value': 1,
            'title': 'Level 1',
            'group': level_group
        }
        self.level = Level.objects.create(**level)

    def _create_assessment(self):
        self._create_assessment_level()

        assessment = {
            'level': self.level,
            'user': self.user.id,
            'evaluated': self.company.id,
            'data': {},
        }

        self.assessment = Assessment.objects.create(**assessment)

    def _create_affiliate(self):
        affiliate = {
            'name': 'Testing Affiliate',
            'shortcode': 'testaf',
            'email': 'testaf@mail.com',
            'website': 'http://affiliate.com',
            'logo': 'http://affiliate.com/logo.png',
            'flow_type': Affiliate.PROGRAM
        }

        self.affiliate = Affiliate.objects.create(**affiliate)

    def _create_supporter(self):
        supporter = {
            'name': 'Testing Supporter',
            'email': 'test@mail.com',
            'investing_level_range': [1, 4],
            'user_profile': self.user_profile
        }

        self.supporter = Supporter.objects.create(**supporter)

    def _create_question_bundle(self):
        question_bundle = {
            'name': 'Testing Question Bundle',
            'supporter': self.supporter,
        }

        self.question_bundle = QuestionBundle.objects.create(**question_bundle)

    def _create_submission(self):
        program_entry = {
            'affiliate': self.affiliate,
            'user_profile': self.user_profile,
            'assessment': self.assessment
        }

        self.program_entry = AffiliateProgramEntry.objects.create(
            **program_entry)

    def test_listing_without_admin_token(self):
        # 1 - Without admin token
        endpoint = self._get_endpoint(affiliate_id=self.affiliate.id)
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_listing_affiliate_submissions_without_none(self):
        # 2 - Listing affiliate submissions without none
        self.client.force_authenticate(self.super_user)
        endpoint = self._get_endpoint(affiliate_id=self.affiliate.id)
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_listing_affiliate_submissions(self):
        # TODO: Create several Affiliate submissions using fixtures instead to make this test cover all cases
        # 3 - Listing affiliate submissions
        self._create_submission()
        self.client.force_authenticate(self.super_user)

        endpoint = self._get_endpoint(affiliate_id=self.affiliate.id)
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        validate(instance=response.data, schema=LIST_SCHEMA)

    def test_affiliate_submission_detail(self):
        # 4 - With affiliate id and submission id
        self._create_submission()
        self.client.force_authenticate(self.super_user)

        endpoint = self._get_endpoint(
            affiliate_id=self.affiliate.id, submission_id=self.program_entry.id)
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        validate(instance=response.data, schema=DETAIL_SCHEMA)
