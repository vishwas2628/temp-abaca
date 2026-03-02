from django.urls import reverse
from rest_framework import status
from company_lists.tests.factories import CompanyListFactory
from matching.tests.factories import SupporterFactory
from shared.utils import AbacaAPITestCase
from viral.tests.factories import EmailAddressFactory, UserProfileFactory


class TestCompanyListCompaniesMilestonePlanner(AbacaAPITestCase):
    def setUp(self):
        super().setUp()
        self.entrepreneur = UserProfileFactory()
        EmailAddressFactory(user_id=self.entrepreneur.user.id, email=self.entrepreneur.user.email)
        self.milestone_planner = self.entrepreneur.company.milestone_planners.first()
        self.supporter = SupporterFactory()
        self.company_list = CompanyListFactory(owner_id=self.supporter.user_profile.id)
        self.company_list.companies.add(self.entrepreneur.company)
        self.client.force_authenticate(user=self.supporter.user_profile.user)

    def _get_endpoint(self, company_list_uid):
        return reverse('list_company_list_companies', kwargs={'uid': company_list_uid})

    def test_not_invited_user_does_not_have_access_to_milestone_planner(self):
        response = self.client.get(self._get_endpoint(self.company_list.uid))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['milestone_planner'], None)

    def test_invited_user_has_access_to_milestone_planner(self):
        self.milestone_planner.invited_users.add(self.supporter.user_profile)
        response = self.client.get(self._get_endpoint(self.company_list.uid))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['milestone_planner'], self.milestone_planner.uid)
