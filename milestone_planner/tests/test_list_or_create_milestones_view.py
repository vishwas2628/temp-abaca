import random

from datetime import date
from django.contrib.auth import get_user_model
from django.urls.base import reverse
from jsonschema.validators import validate
from rest_framework import status

from shared.utils import AbacaAPITestCase
from grid.models import CategoryLevel
from grid.tests.factories import AssessmentFactory
from matching.models import Question, QuestionType
from milestone_planner.models import Milestone
from milestone_planner.schemas import MILESTONE_LIST_SCHEMA
from viral.models.company import Company
from viral.models.user_profile import UserProfile


class TestListOrCreateMilestonesView(AbacaAPITestCase):
    """
    Test listing owned milestones:
    * 1 - Without being authenticated
    * 2 - While being authenticated
    * 2.1 - As an Entrepreneur
    * 2.2 - As a Supporter

    Test creating a milestone:
    * 3 - Without being authenticated
    * 4 - While being authenticated
    * 4.1 - As an Entrepreneur
    * 4.1.1 - Without payload
    * 4.1.2 - With already existing category level
    * 4.1.3 - With invalid fields for to-be-planned milestone
    * 4.1.4 - With invalid fields to complete without evidence
    * 4.1.5 - With missing fields to publish plan
    * 4.1.6 - With missing fields to complete with evidence
    * 4.1.7 - With fields to add a plan in draft mode
    * 4.1.8 - With fields to add evidence in draft mode
    * 4.1.9 - With fields to publish a plan
    * 4.1.10 - With fields to complete with evidence
    * 4.1.11 - With currency field at zero
    * 4.2 - As a Supporter
    """
    ENDPOINT = reverse('list_or_create_milestones')

    fixtures = ['level_groups', 'category_groups', 'levels', 'categories',
                'category_levels', 'profile_id_fields', 'question_types', 'question_categories', 'questions', 'answers']

    def setUp(self):
        super().setUp()
        self.new_assessment = AssessmentFactory(with_user_profile=True)
        self.new_company = Company.objects.get(pk=self.new_assessment.evaluated)
        self.new_user = get_user_model().objects.get(id=self.new_assessment.user)
        self.new_user_profile = UserProfile.objects.get(user=self.new_user, company=self.new_company)
        self.created_milestones = Milestone.objects.filter(user_profile=self.new_user_profile)

    def _payload_with_category_level(self, payload, existing=False):
        if existing:
            random_milestone = random.choice(self.created_milestones)
            payload['category_level'] = random_milestone.category_level.pk
        else:
            milestones_category_level_pks = [milestone.category_level.pk for milestone in self.created_milestones]
            unexisting_milestone_category_level = CategoryLevel.objects.filter(category__group=2).exclude(
                pk__in=milestones_category_level_pks).first()
            payload['category_level'] = unexisting_milestone_category_level.pk
        return payload

    def _payload_with_target_date(self, payload, valid=True):
        return {
            **payload,
            'target_date': date.today().strftime("%Y-%m-%d") if valid else None
        }

    def _payload_with_plan(self, payload):
        return {
            **payload,
            "strategy": self.faker.text(),
            "outcomes": self.faker.text(),
            "resources": self.faker.text(),
            "finances_needed": random.randrange(1000, 9000),
        }

    def _payload_with_date_of_completion(self, payload, valid=True):
        return {
            **payload,
            'date_of_completion': date.today().strftime("%Y-%m-%d") if valid else None
        }

    def _payload_with_evidence(self, payload):
        single_select_questions = Question.objects.prefetch_related(
            'answer_set').filter(question_type__type=QuestionType.SINGLE_SELECT)
        random_single_select_question = random.choice(single_select_questions)
        random_answer = random.choice([answer.pk for answer in random_single_select_question.answer_set.all()])

        payload['evidence'] = [{
            'question': random_single_select_question.pk,
            'answers': [random_answer]
        }]
        return payload

    def test_list_milestones_without_being_authenticated(self):
        """1 - Test listing owned milestones without being authenticated"""
        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_milestones_while_being_authenticated_as_entrepreneur(self):
        """2.1 - Test listing owned milestones while being authenticated as entrepreneur"""
        self.client.force_authenticate(user=self.new_user)
        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        validate(instance=response.data, schema=MILESTONE_LIST_SCHEMA)

    def test_list_milestones_while_being_authenticated_as_supporter(self):
        """2.2 - Test listing owned milestones while being authenticated as supporter"""
        # TODO: Add factory for Supporter
        pass

    def test_create_milestone_without_being_authenticated(self):
        """3 - Test creating a milestone without being authenticated"""
        response = self.client.post(self.ENDPOINT)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_milestone_as_entrepreneur_without_payload(self):
        """4.1.1 - Test creating a milestone as entrepreneur without payload"""
        self.client.force_authenticate(user=self.new_user)
        response = self.client.post(self.ENDPOINT)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.json()['errors']

        is_missing_category_level = 'category_level' in errors and errors['category_level'][0]['code'] == 'required'
        self.assertTrue(is_missing_category_level)

    def test_create_milestone_as_entrepreneur_with_existing_category_level(self):
        """4.1.2 - Test creating a milestone as entrepreneur with existing category level"""
        self.client.force_authenticate(user=self.new_user)
        payload = self.get_payload({
            'with_category_level': {'existing': True},
            'with_target_date': True
        })
        response = self.client.post(self.ENDPOINT, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.json()['errors']

        is_duplicated_category_level = errors['non_field_errors'][0]['code'] == 'unique'
        self.assertTrue(is_duplicated_category_level)

    def test_create_milestone_as_entrepreneur_with_invalid_fields_for_to_be_planned(self):
        """4.1.3 - Test creating a milestone as entrepreneur with invalid fields for to-be-planned milestone"""
        self.client.force_authenticate(user=self.new_user)
        payload = self.get_payload({
            'with_category_level': True,
            'with_target_date': {'valid': False}
        })
        response = self.client.post(self.ENDPOINT, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.json()['errors']

        has_invalid_milestone = errors['non_field_errors'][0]['code'] == 'invalid_milestone'
        self.assertTrue(has_invalid_milestone)

    def test_create_milestone_as_entrepreneur_with_invalid_fields_to_complete_without_evidence(self):
        """4.1.4 - Test creating a milestone as entrepreneur with invalid fields to complete without evidence"""
        self.client.force_authenticate(user=self.new_user)
        payload = self.get_payload({
            'with_category_level': True,
            'with_date_of_completion': {'valid': False}
        })
        response = self.client.post(self.ENDPOINT, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.json()['errors']

        has_invalid_milestone = errors['non_field_errors'][0]['code'] == 'invalid_milestone'
        self.assertTrue(has_invalid_milestone)

    def test_create_milestone_as_entrepreneur_with_missing_fields_to_publish_plan(self):
        """4.1.5 - Test creating a milestone as entrepreneur with missing fields to publish plan"""
        self.client.force_authenticate(user=self.new_user)
        payload = self.get_payload({
            'with_category_level': True,
            'with_target_date': True,
        })
        payload['plan_published'] = True
        response = self.client.post(self.ENDPOINT, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.json()['errors']

        has_incomplete_plan = errors['non_field_errors'][0]['code'] == 'incomplete_plan'
        self.assertTrue(has_incomplete_plan)

    def test_create_milestone_as_entrepreneur_with_missing_fields_to_complete_with_evidence(self):
        """4.1.6 - Test creating a milestone as entrepreneur with missing fields to complete with evidence"""
        self.client.force_authenticate(user=self.new_user)
        payload = self.get_payload({
            'with_category_level': True
        })
        payload['evidence_published'] = True
        response = self.client.post(self.ENDPOINT, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.json()['errors']

        is_missing_date_of_completion = 'date_of_completion' in errors and errors[
            'date_of_completion'][0]['code'] == 'required'
        self.assertTrue(is_missing_date_of_completion)

    def test_create_milestone_as_entrepreneur_with_fields_for_draft_plan(self):
        """4.1.7 - Test creating a milestone as entrepreneur with fields to add a plan in draft mode"""
        self.client.force_authenticate(user=self.new_user)
        payload = self.get_payload({
            'with_category_level': True,
            'with_target_date': True,
        })
        category_level_pk = payload['category_level']
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        has_created_milestone_with_draft_plan = Milestone.objects.filter(
            category_level=category_level_pk, user_profile=self.new_user_profile,
            state=Milestone.TO_BE_PLANNED_STATE).exists()
        self.assertTrue(has_created_milestone_with_draft_plan)

    def test_create_milestone_as_entrepreneur_with_fields_for_draft_evidence(self):
        """4.1.8 - Test creating a milestone as entrepreneur with fields to add evidence in draft mode"""
        self.client.force_authenticate(user=self.new_user)
        payload = self.get_payload({
            'with_category_level': True,
            'with_evidence': True,
        })
        category_level_pk = payload['category_level']
        response = self.client.post(self.ENDPOINT, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        has_created_milestone_with_draft_evidence = Milestone.objects.filter(
            category_level=category_level_pk, user_profile=self.new_user_profile,
            state=Milestone.IN_PROGRESS_STATE).exclude(evidence=None).exists()
        self.assertTrue(has_created_milestone_with_draft_evidence)

    def test_create_milestone_as_entrepreneur_with_fields_to_publish_plan(self):
        """4.1.9 - Test creating a milestone as entrepreneur with fields to publish plan"""
        self.client.force_authenticate(user=self.new_user)
        payload = self.get_payload({
            'with_category_level': True,
            'with_target_date': True,
            'with_plan': True
        })
        payload['plan_published'] = True
        response = self.client.post(self.ENDPOINT, payload, format='json')
        category_level_pk = payload['category_level']

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        has_created_milestone_with_published_plan = Milestone.objects.filter(
            category_level=category_level_pk, user_profile=self.new_user_profile,
            state=Milestone.PLANNED_STATE).exists()
        self.assertTrue(has_created_milestone_with_published_plan)

    def test_create_milestone_as_entrepreneur_with_fields_to_complete_with_evidence(self):
        """4.1.10 - Test creating a milestone as entrepreneur with fields to complete with evidence"""
        self.client.force_authenticate(user=self.new_user)
        payload = self.get_payload({
            'with_category_level': True,
            'with_date_of_completion': True,
            'with_evidence': True
        })
        payload['evidence_published'] = True
        response = self.client.post(self.ENDPOINT, payload, format='json')
        category_level_pk = payload['category_level']

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        has_created_completed_milestone_with_evidence = Milestone.objects.filter(
            category_level=category_level_pk, user_profile=self.new_user_profile,
            state=Milestone.COMPLETED_STATE).exclude(evidence=None).exists()
        self.assertTrue(has_created_completed_milestone_with_evidence)

    def test_create_milestone_as_entrepreneur_with_currency_field_at_zero(self):
        """4.1.11 - Test creating a milestone as entrepreneur with currency field at zero"""
        self.client.force_authenticate(user=self.new_user)
        payload = self.get_payload({'with_category_level': True})
        payload['finances_needed'] = 0
        category_level_pk = payload['category_level']
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        has_created_milestone_with_currency_at_zero = Milestone.objects.filter(
            category_level=category_level_pk, user_profile=self.new_user_profile,
            state=Milestone.TO_BE_PLANNED_STATE, finances_needed=0).exists()
        self.assertTrue(has_created_milestone_with_currency_at_zero)

    def test_create_milestone_as_supporter(self):
        """4.2 - Test creating a milestone as a supporter"""
        # TODO: Add factory for Supporter
        pass
