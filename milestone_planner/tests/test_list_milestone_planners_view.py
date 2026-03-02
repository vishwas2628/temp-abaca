from django.urls.base import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from jsonschema.validators import validate

from grid.tests.factories import AssessmentFactory
from matching.tests.factories import SupporterFactory
from milestone_planner.models import Milestone, MilestonePlanner
from milestone_planner.schemas import LIST_OWNED_MILESTONE_PLANNERS_SCHEMA
from shared.utils import AbacaAPITestCase
from viral.models import Company, UserProfile


class TestListMilestonePlannersView(AbacaAPITestCase):
    """
    Test listing owned milestones:
    * 1 - Without being authenticated
    * 2 - While being authenticated
    * 2.1 - As an Entrepreneur
    * 2.2 - As a Supporter
    """
    ENDPOINT = reverse('list_milestone_planners')

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
        self.supporter = SupporterFactory()

    def test_list_milestone_planners_without_being_authenticated(self):
        """1 - Test listing milestone planners without being authenticated"""
        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_milestone_planners_while_being_authenticated_as_entrepreneur(self):
        """2.1 - Test listing owned milestone planners while being authenticated as Entrepreneur"""
        self.client.force_authenticate(user=self.new_user)
        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        default_milestone_planner = response.data[0]
        self.assertEquals(default_milestone_planner['uid'], self.milestone_planner.uid)
        validate(instance=response.data, schema=LIST_OWNED_MILESTONE_PLANNERS_SCHEMA)

    def test_list_milestone_planners_while_being_authenticated_as_supporter(self):
        """2.2 - Test listing milestone planners while being authenticated as Supporter"""
        self.client.force_authenticate(user=self.supporter.user_profile.user)
        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(len(response.data))
