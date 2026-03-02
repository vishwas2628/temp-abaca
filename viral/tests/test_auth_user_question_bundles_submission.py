from django.urls.base import reverse
from django.contrib.auth import get_user_model
from rest_framework import status

from viral.models import Affiliate, Company, UserProfile
from shared.utils import AbacaAPITestCase
from grid.tests.factories import AssessmentFactory
from company_lists.tests.factories import CompanyListFactory


class TestAuthUserQuestionBundlesSubmission(AbacaAPITestCase):
    """
    Test auth user (entrepreneur) submission of a question bundle.

    # TODO: Add remaining test cases
    - Validate if submission fails with Affiliate of type Assessment
    - Validate if submission fails with unexisting responses
    """
    fixtures = ['users', 'email_addresses', 'networks', 'location_groups', 'locations', 'companies',
                'affiliates', 'level_groups', 'category_groups', 'levels', 'categories', 'category_levels']

    ENDPOINT = reverse('program_auth_user')

    def setUp(self):
        super().setUp()
        # Build submission
        self.submitted_assessement = AssessmentFactory(with_user_profile=True)
        self.auth_company = Company.objects.get(pk=self.submitted_assessement.evaluated)
        self.auth_user = get_user_model().objects.get(id=self.submitted_assessement.user)
        self.auth_user_profile = UserProfile.objects.get(user=self.auth_user, company=self.auth_company)

        # Grab one Affiliate and link a CompanyList
        self.program_affiliate = Affiliate.objects.get(pk=2)
        self.company_list = CompanyListFactory(owner__company__type=Company.SUPPORTER)
        self.program_affiliate.company_lists.add(self.company_list)

    def _get_payload(self):
        return {
            "affiliate": self.program_affiliate.pk,
            "responses": []
        }

    def test_auth_user_submission_with_invalid_user(self):
        """Test with unauthenticated user"""
        payload = self._get_payload()
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        errors = response.json()['errors']
        is_unathenticated = errors['code'] == 'not_authenticated'
        self.assertTrue(is_unathenticated)

    def test_auth_user_submission_populating_company_lists(self):
        """Test that company submitted was added to the Affiliate's company lists"""
        # Store initial size for later comparison
        initial_company_list_size = self.company_list.companies.count()

        # Submit Affiliate
        self.client.force_authenticate(user=self.auth_user)
        payload = self._get_payload()
        response = self.client.post(self.ENDPOINT, payload, format='json')

        # Check if submission was successfully created
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check if submitted company was added to linked CompanyList
        self.company_list.refresh_from_db()
        current_company_list_size = self.company_list.companies.count()
        has_populated_with_submitted_company = self.company_list.companies.filter(pk=self.auth_company.pk).exists()

        self.assertNotEqual(initial_company_list_size, current_company_list_size)
        self.assertTrue(has_populated_with_submitted_company)
