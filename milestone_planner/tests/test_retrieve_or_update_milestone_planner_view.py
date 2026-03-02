from django.contrib.auth import get_user_model
from django.urls.base import reverse
from jsonschema.validators import validate
from rest_framework import status

from grid.tests.factories import AssessmentFactory
from matching.tests.factories import SupporterFactory
from milestone_planner.models import Milestone, MilestonePlanner
from milestone_planner.schemas import (MILESTONE_PLANNER_GUEST_SCHEMA,
                                       MILESTONE_PLANNER_OWNER_SCHEMA)
from shared.utils import AbacaAPITestCase
from viral.models import Company, UserGuest, UserProfile
from viral.tests.factories import UserProfileFactory


class TestRetrieveOrUpdateMilestonePlannerView(AbacaAPITestCase):
    """
    Test retrieving a milestone planner (without passcode):
    * 1 - As a Guest
    * 1.1 - Without email
    * 1.2 - With invalid email
    * 1.3 - With an unregistered email
    * 1.4 - With a registered email
    * 2 - As a Supporter
    * 3 - As an Entrepreneur
    * 3.1 - Being the Owner
    * 3.2 - Being a Visitor

    Test retrieving a milestone planner (with passcode):
    * 4 - As a Guest
    * 4.1 - Without passcode
    * 4.2 - With invalid passcode
    * 4.3 - With a valid passcode
    * 5 - As a Supporter
    * 5.1 - Without passcode
    * 5.2 - With invalid passcode
    * 5.3 - With a valid passcode
    * 6 - As an Entrepreneur (owner)

    Test updating a milestone planner:
    * 7 - As a Guest
    * 8 - As a Supporter
    * 9 - As an Entrepreneur
    * 9.1 - Without being owner
    * 9.2 - While being the owner:
    * 9.2.1 - Requesting a link reset
    * 9.2.2 - Requesting a passcode reset
    """
    fixtures = ['level_groups', 'category_groups', 'levels', 'categories',
                'category_levels', 'profile_id_fields', 'question_types', 'question_categories', 'questions', 'answers']

    def setUp(self):
        super().setUp()
        self.new_assessment = AssessmentFactory(with_user_profile=True)
        self.new_company = Company.objects.get(pk=self.new_assessment.evaluated)
        self.new_user = get_user_model().objects.get(id=self.new_assessment.user)
        self.new_user_profile = UserProfile.objects.get(user=self.new_user, company=self.new_company)
        self.created_milestones = Milestone.objects.filter(user_profile=self.new_user_profile)
        self.milestone_planner = MilestonePlanner.objects.filter(company=self.new_company).first()
        self.milestone_planner_with_passcode = MilestonePlanner.objects.create(company=self.new_company, passcode='123')
        self.supporter = SupporterFactory()

    def _get_endpoint(self, milestone_planner_uid):
        return reverse('retrieve_or_update_milestone_planner', kwargs={'uid': milestone_planner_uid})

    def test_retrieve_milestone_planner_without_passcode_as_guest_without_email(self):
        """1.1 - Test retrieving a milestone planner without passcode as guest without email"""
        response = self.client.get(self._get_endpoint(self.milestone_planner.uid))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.json()['errors']
        is_missing_email = errors[0]['code'] == 'invalid'
        self.assertTrue(is_missing_email)

    def test_retrieve_milestone_planner_without_passcode_as_guest_with_invalid_email(self):
        """1.2 - Test retrieving a milestone planner without passcode as guest with invalid email"""
        response = self.client.get(self._get_endpoint(self.milestone_planner.uid), {'email': 'invalid_@_email'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.json()['errors']
        has_invalid_email = errors[0]['code'] == 'invalid'
        self.assertTrue(has_invalid_email)

    def test_retrieve_milestone_planner_without_passcode_as_guest_with_unregistered_email(self):
        """1.3 - Test retrieving a milestone planner without passcode as guest with an uregistered email"""
        response = self.client.get(self._get_endpoint(self.milestone_planner.uid), {'email': 'unregistered@mail.com'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_milestone_planner_without_passcode_as_guest_with_registered_email(self):
        """1.4 - Test retrieving a milestone planner without passcode as guest with a registered email"""
        # Emulate a user guest previously registered:
        new_user_guest = UserGuest.objects.create(email='valid@mail.com', name='valid')

        # Retrieve milestone planner:
        response = self.client.get(self._get_endpoint(self.milestone_planner.uid), {'email': new_user_guest.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        validate(instance=response.data, schema=MILESTONE_PLANNER_GUEST_SCHEMA)

        # Check if added new guest to invited guests' list:
        self.milestone_planner.refresh_from_db()
        has_added_guest_to_invited = self.milestone_planner.invited_guests.filter(
            email__iexact=new_user_guest.email).exists()
        self.assertTrue(has_added_guest_to_invited)

    def test_retrieve_milestone_planner_without_passcode_as_supporter(self):
        """2 - Test retrieving a milestone planner without passcode as a Supporter"""
        # Login as Supporter:
        self.client.force_authenticate(self.supporter.user_profile.user)

        # Retrieve milestone planner:
        response = self.client.get(self._get_endpoint(self.milestone_planner.uid))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        validate(instance=response.data, schema=MILESTONE_PLANNER_GUEST_SCHEMA)

        # Check if added Supporter to invited users' list:
        self.milestone_planner.refresh_from_db()
        has_added_user_to_invited = self.milestone_planner.invited_users.filter(
            pk=self.supporter.user_profile.pk).exists()
        self.assertTrue(has_added_user_to_invited)

    def test_retrieve_milestone_planner_without_passcode_as_entrepreneur_owner(self):
        """3.1 - Test retrieving a milestone planner without passcode as an Entrepreneur owner"""
        # Login as Entrepreneur:
        self.client.force_authenticate(self.new_user)

        # Retrieve milestone planner:
        response = self.client.get(self._get_endpoint(self.milestone_planner.uid))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        validate(instance=response.data, schema=MILESTONE_PLANNER_OWNER_SCHEMA)

        # Check if not added himself to the invited users list:
        self.milestone_planner.refresh_from_db()
        has_invited_himself = self.milestone_planner.invited_users.filter(pk=self.new_user_profile.pk).exists()
        self.assertFalse(has_invited_himself)

    def test_retrieve_milestone_planner_without_passcode_as_entrepreneur_visitor(self):
        """3.2 - Test retrieving a milestone planner without passcode as an Entrepreneur visitor"""
        # Login as Entrepreneur:
        user_profile = UserProfileFactory()
        self.client.force_authenticate(user_profile.user)

        # Retrieve milestone planner:
        response = self.client.get(self._get_endpoint(self.milestone_planner.uid))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_milestone_planner_with_passcode_as_guest_without_passcode(self):
        """4.1 - Test retrieving a milestone planner with passcode as guest without passcode"""
        response = self.client.get(self._get_endpoint(self.milestone_planner_with_passcode.uid))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        errors = response.json()['errors']
        has_invalid_passcode = errors['code'] == 'invalid_passcode'
        self.assertTrue(has_invalid_passcode)

    def test_retrieve_milestone_planner_with_passcode_as_guest_with_invalid_passcode(self):
        """4.2 - Test retrieving a milestone planner with passcode as guest with invalid passcode"""
        response = self.client.get(
            self._get_endpoint(self.milestone_planner_with_passcode.uid),
            {'passcode': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        errors = response.json()['errors']
        has_invalid_passcode = errors['code'] == 'invalid_passcode'
        self.assertTrue(has_invalid_passcode)

    def test_retrieve_milestone_planner_with_passcode_as_guest_with_valid_passcode(self):
        """4.3 - Test retrieving a milestone planner with passcode as guest with a valid passcode"""
        # Emulate a user guest previously registered:
        new_user_guest = UserGuest.objects.create(email='valid@mail.com', name='valid')

        # Retrieve milestone planner:
        response = self.client.get(
            self._get_endpoint(self.milestone_planner_with_passcode.uid),
            {'passcode': '123', 'email': new_user_guest.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        validate(instance=response.data, schema=MILESTONE_PLANNER_GUEST_SCHEMA)

    def test_retrieve_milestone_planner_with_passcode_as_supporter_without_passcode(self):
        """5.1 - Test retrieving a milestone planner with passcode as Supporter without passcode"""
        # Login as Supporter:
        self.client.force_authenticate(self.supporter.user_profile.user)

        # Retrieve milestone planner:
        response = self.client.get(self._get_endpoint(self.milestone_planner_with_passcode.uid))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        errors = response.json()['errors']
        has_invalid_passcode = errors['code'] == 'invalid_passcode'
        self.assertTrue(has_invalid_passcode)

    def test_retrieve_milestone_planner_with_passcode_as_supporte_with_invalid_passcode(self):
        """5.2 - Test retrieving a milestone planner with passcode as Supporter with an invalid passcode"""
        # Login as Supporter:
        self.client.force_authenticate(self.supporter.user_profile.user)

        # Retrieve milestone planner:
        response = self.client.get(
            self._get_endpoint(self.milestone_planner_with_passcode.uid),
            {'passcode': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        errors = response.json()['errors']
        has_invalid_passcode = errors['code'] == 'invalid_passcode'
        self.assertTrue(has_invalid_passcode)

    def test_retrieve_milestone_planner_with_passcode_as_supporter_with_valid_passcode(self):
        """5.2 - Test retrieving a milestone planner with passcode as Supporter with a valid passcode"""
        # Login as Supporter:
        self.client.force_authenticate(self.supporter.user_profile.user)

        # Retrieve milestone planner:
        response = self.client.get(
            self._get_endpoint(self.milestone_planner_with_passcode.uid),
            {'passcode': '123'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        validate(instance=response.data, schema=MILESTONE_PLANNER_GUEST_SCHEMA)

    def test_retrieve_milestone_planner_with_passcode_as_entrepreneur_owner(self):
        """6 - Test retrieving a milestone planner with passcode as Supporter with a valid passcode"""
        # Login as Entrepreneur:
        self.client.force_authenticate(self.new_user)

        # Retrieve milestone planner:
        response = self.client.get(self._get_endpoint(self.milestone_planner_with_passcode.uid))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        validate(instance=response.data, schema=MILESTONE_PLANNER_OWNER_SCHEMA)

    def test_updating_milestone_planner_as_guest(self):
        """7 - Test updating a milestone planner as a Guest"""
        response = self.client.patch(self._get_endpoint(self.milestone_planner.uid))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_updating_milestone_planner_as_supporter(self):
        """8 - Test updating a milestone planner as a Supporter"""
        # Login as Supporter:
        self.client.force_authenticate(self.supporter.user_profile.user)

        # Update milestone planner:
        response = self.client.patch(self._get_endpoint(self.milestone_planner.uid))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_updating_milestone_planner_as_entrepreneur_without_being_owner(self):
        """9.1 - Test updating a milestone planner as an Entrepreneur without being the owner"""
        # Login as Entrepreneur:
        user_profile = UserProfileFactory()
        self.client.force_authenticate(user_profile.user)

        # Update milestone planner:
        response = self.client.patch(self._get_endpoint(self.milestone_planner.uid))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_updating_milestone_planner_as_entrepreneur_while_being_owner_requesting_link_reset(self):
        """9.2.1 - Test updating a milestone planner as an Entrepreneur (owner) requesting a link reset"""
        # Login as Entrepreneur:
        self.client.force_authenticate(self.new_user)

        # Invite users & guests to test link reset:
        new_guest = UserGuest.objects.create(name='test', email='test@mail.com')
        new_user = self.supporter.user_profile
        self.milestone_planner.invited_guests.add(new_guest)
        self.milestone_planner.invited_users.add(new_user)
        self.milestone_planner.save()

        # Update milestone planner:
        initial_uid = self.milestone_planner.uid
        endpoint_with_reset_query = f"{self._get_endpoint(self.milestone_planner.uid)}?reset=link"
        response = self.client.patch(endpoint_with_reset_query)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if changed milestone planner uid:
        self.milestone_planner.refresh_from_db()
        has_changed_uid = initial_uid != self.milestone_planner.uid
        self.assertTrue(has_changed_uid)

        # Check if cleared invited users & guests
        has_cleared_invited_users = self.milestone_planner.invited_users.count() == 0
        has_cleared_invited_guests = self.milestone_planner.invited_guests.count() == 0
        self.assertTrue(has_cleared_invited_users)
        self.assertTrue(has_cleared_invited_guests)

    def test_updating_milestone_planner_as_entrepreneur_while_being_owner_requesting_passcode_reset(self):
        """9.2.2 - Test updating a milestone planner as an Entrepreneur (owner) requesting a passcode reset"""
        # Login as Entrepreneur:
        self.client.force_authenticate(self.new_user)

        # Update milestone planner:
        initial_passcode = self.milestone_planner.passcode
        endpoint_with_reset_query = f"{self._get_endpoint(self.milestone_planner.uid)}?reset=passcode"
        response = self.client.patch(endpoint_with_reset_query)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if changed milestone planner uid:
        self.milestone_planner.refresh_from_db()
        has_changed_passcode = initial_passcode != self.milestone_planner.passcode
        has_stored_previous_passcode = initial_passcode == self.milestone_planner.previous_passcode
        self.assertTrue(has_changed_passcode)
        self.assertTrue(has_stored_previous_passcode)
