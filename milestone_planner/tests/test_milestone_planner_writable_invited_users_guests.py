from django.urls import reverse
from shared.utils import AbacaAPITestCase
from viral.tests.factories import UserGuestFactory, UserProfileFactory


class TestMilestonePlannerWritableInvitedUsersGuests(AbacaAPITestCase):
    fixtures = ['levels']

    def setUp(self):
        super().setUp()
        self.entrepreneur = UserProfileFactory()
        self.milestone_planner = self.entrepreneur.company.milestone_planners.first()
        self.client.force_authenticate(user=self.entrepreneur.user)

    def test_update_invited_users(self):
        self.assertEquals(self.milestone_planner.invited_users.count(), 0)
        self._patch_milestone_planner({'invited_users': [UserProfileFactory().uid]})
        self.assertEquals(self.milestone_planner.invited_users.count(), 1)
        self._patch_milestone_planner({'invited_users': []})
        self.assertEquals(self.milestone_planner.invited_users.count(), 0)
        pass

    def test_update_invited_guests(self):
        self.assertEquals(self.milestone_planner.invited_guests.count(), 0)
        self._patch_milestone_planner({'invited_guests': [UserGuestFactory().uid]})
        self.assertEquals(self.milestone_planner.invited_guests.count(), 1)
        self._patch_milestone_planner({'invited_guests': []})
        self.assertEquals(self.milestone_planner.invited_guests.count(), 0)

    def _patch_milestone_planner(self, data):
        self.client.patch(
            reverse('retrieve_or_update_milestone_planner', kwargs={'uid': self.milestone_planner.uid}),
            data=data,
            format='json',
        )
