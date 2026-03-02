from django.urls.base import reverse
from django.contrib.auth import get_user_model
from rest_framework import status

from viral.models import Affiliate, Company, UserProfile
from shared.utils import AbacaAPITestCase
from grid.tests.factories import AssessmentFactory
from company_lists.tests.factories import CompanyListFactory


class TestPendingUserQuestionBundlesSubmission(AbacaAPITestCase):
    """
    Test pending user (entrepreneur) submission of a question bundle.

    # TODO: Add remaining test cases
    - Validate if submission fails with Affiliate of type Assessment
    - Validate if submission fails with unexisting responses
    """
    fixtures = ['users', 'email_addresses', 'networks', 'location_groups', 'locations', 'companies',
                'affiliates', 'level_groups', 'category_groups', 'levels', 'categories', 'category_levels']

    ENDPOINT = reverse('program_pending_user_question_bundles')

    def setUp(self):
        super().setUp()
        # Build pending submission
        self.submitted_assessement = AssessmentFactory(user__password='!unusable_password')
        self.pending_company = Company.objects.get(pk=self.submitted_assessement.evaluated)
        self.pending_user = get_user_model().objects.get(id=self.submitted_assessement.user)
        self.pending_user_profile = UserProfile.objects.get(user=self.pending_user, company=self.pending_company)

        # Grab one existing User
        self.existing_user = get_user_model().objects.get(pk=2)

        # Grab one Affiliate and link a CompanyList
        self.program_affiliate = Affiliate.objects.get(pk=2)
        self.company_list = CompanyListFactory(owner__company__type=Company.SUPPORTER)
        self.program_affiliate.company_lists.add(self.company_list)

    def _get_payload(self, with_valid_pending_user=True):
        return {
            "email": self.pending_user.email if with_valid_pending_user else self.existing_user.email,
            "affiliate": self.program_affiliate.pk,
            "responses": []
        }

    def test_pending_user_submission_with_invalid_user(self):
        """Test with invalid user"""
        payload = self._get_payload(with_valid_pending_user=False)
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        errors = response.json()['errors']
        has_invalid_user = errors[0]['code'] == 'no_user'
        self.assertTrue(has_invalid_user)

    def test_pending_user_submission_populating_company_lists(self):
        """Test that company submitted was added to the Affiliate's company lists"""
        # Store initial size for later comparison
        initial_company_list_size = self.company_list.companies.count()

        # Submit Affiliate
        payload = self._get_payload()
        response = self.client.post(self.ENDPOINT, payload, format='json')

        # Check if submission was successfully created
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check if submitted company was added to linked CompanyList
        self.company_list.refresh_from_db()
        current_company_list_size = self.company_list.companies.count()
        has_populated_with_submitted_company = self.company_list.companies.filter(pk=self.pending_company.pk).exists()

        self.assertNotEqual(initial_company_list_size, current_company_list_size)
        self.assertTrue(has_populated_with_submitted_company)
