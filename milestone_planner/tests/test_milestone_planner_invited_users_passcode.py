from django.urls import reverse
from rest_framework import status
from matching.tests.factories import SupporterFactory
from shared.utils import AbacaAPITestCase
from viral.tests.factories import UserProfileFactory


class TestMilestonePlannerInvitedUsersPasscode(AbacaAPITestCase):
    fixtures = ['levels']

    def setUp(self):
        super().setUp()
        self.entrepreneur = UserProfileFactory()
        self.milestone_planner = self.entrepreneur.company.milestone_planners.first()
        self.milestone_planner.passcode = '1234'
        self.milestone_planner.save()
        self.supporter = SupporterFactory()
        self.client.force_authenticate(user=self.supporter.user_profile.user)

    def _get_endpoint(self, milestone_planner_uid):
        return reverse('retrieve_or_update_milestone_planner', kwargs={'uid': milestone_planner_uid})

    def test_not_invited_user_needs_passcode(self):
        self.assertFalse(self.milestone_planner.invited_users.filter(id=self.supporter.user_profile_id).exists())
        response = self.client.get(self._get_endpoint(self.milestone_planner.uid))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invited_user_doesnt_need_passcode(self):
        self.milestone_planner.invited_users.add(self.supporter.user_profile)
        self.assertTrue(self.milestone_planner.invited_users.filter(id=self.supporter.user_profile_id).exists())
        response = self.client.get(self._get_endpoint(self.milestone_planner.uid))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
