import random

from datetime import date
from django.urls.base import reverse
from django.contrib.auth import get_user_model
from itertools import groupby
from jsonschema.validators import validate
from rest_framework import status

from grid.tests.factories import AssessmentFactory
from matching.models import Question, Answer, QuestionType
from matching.tests.factories import ResponseFactory, SupporterFactory
from milestone_planner.models import Milestone
from milestone_planner.schemas import MILESTONE_SCHEMA
from shared.utils import AbacaAPITestCase
from viral.models.company import Company
from viral.models.user_profile import UserProfile
from viral.tests.factories import UserProfileFactory


class TestRetrieveUpdateOrDeleteMilestoneView(AbacaAPITestCase):
    """
    Test retrieving a milestone:
    * 1 - Without being authenticated
    * 2 - While being authenticated
    * 2.1 - As an Entrepreneur
    * 2.2 - As a Supporter

    Test updating a milestone:
    * 3 - Without being authenticated
    * 4 - While being authenticated
    * 4.1 - As an Entrepreneur
    * 4.1.1 - With cleared fields on both plan and evidence
    * 4.1.2 - With cleared evidence without publishing flag
    * 4.1.3 - With cleared plan without publishing flag
    * 4.1.4 - With invalid values for milestone plan
    * 4.1.5 - With missing fields for plan publication
    * 4.1.6 - With invalid values for milestone evidence
    * 4.1.7 - With missing fields for evidence publication
    * 4.1.8 - With fields to add a plan in draft mode
    * 4.1.9 - With fields to add evidence in draft mode
    * 4.1.10 - With fields to publish a plan
    * 4.1.11 - With fields to complete with evidence
    * 4.1.12 - With a existing plan while removing evidence
    * 4.2 - As a Supporter

    Test deleting a milestone:
    * 5 - Without being authenticated
    * 6 - While being authenticated
    * 6.1 - As an Entrepreneur
    * 6.1.1 - Without being the owner
    * 6.1.2 - While being the owner
    * 6.1.2.1 - With above milestones completed
    * 6.1.2.2 - With below milestones completed
    * 6.2 - As a Supporter
    """
    fixtures = ['level_groups', 'category_groups', 'levels', 'categories',
                'category_levels', 'profile_id_fields', 'question_types', 'question_categories', 'questions', 'answers']

    def setUp(self):
        super().setUp()
        self.new_assessment = AssessmentFactory(with_user_profile=True)
        self.new_company = Company.objects.get(pk=self.new_assessment.evaluated)
        self.new_user = get_user_model().objects.get(id=self.new_assessment.user)
        self.new_user_profile = UserProfile.objects.get(user=self.new_user, company=self.new_company)
        self.supporter = SupporterFactory()
        self.created_milestones = Milestone.objects.filter(user_profile=self.new_user_profile)

    def _get_endpoint(self, milestone_uid):
        return reverse('retrieve_update_or_delete_milestone', kwargs={'uid': milestone_uid})

    def _payload_with_cleared_fields(self, payload):
        return {
            **payload,
            'strategy': '',
            'outcomes': '',
            'resources': '',
            'finances_needed': None,
            'target_date': None,
            'evidence': [],
            'date_of_completion': None
        }

    def _payload_with_plan(self, payload, valid=True, complete=True, to_publish=False):
        if valid:
            payload = {
                **payload,
                'strategy': 'Lorem',
                'finances_needed': 5000,
                'target_date': '2021-01-01' if to_publish else None,
                'plan_published': to_publish
            }
            if complete:
                payload['resources'] = 'Ipsum'
                payload['outcomes'] = 'Dolor'
        else:
            payload = {
                **payload,
                'strategy': 123,
                'outcomes': ['abc'],
                'resources': True,
                'finances_needed': '-100.00',
                'target_date': '2021',
                'plan_published': to_publish
            }

        return payload

    def _payload_with_evidence(self, payload, valid=True, complete=True, to_publish=False):
        random_text_question = Question.objects.filter(question_type__type=QuestionType.FREE_RESPONSE).first()
        single_select_questions = Question.objects.prefetch_related(
            'answer_set').filter(question_type__type=QuestionType.SINGLE_SELECT)
        random_single_select_question = random.choice(single_select_questions)
        random_answer = random.choice([answer.pk for answer in random_single_select_question.answer_set.all()])
        invalid_answer = Answer.objects.exclude(question=random_single_select_question).first()

        if valid:
            payload = {
                **payload,
                'evidence_published': to_publish,
                'date_of_completion': None
            }
            if complete:
                payload['date_of_completion'] = '2021-01-01'
                payload['evidence'] = [{
                    'question': random_single_select_question.pk,
                    'answers': [random_answer]
                }]
        else:
            payload = {
                **payload,
                'evidence_published': to_publish,
                'evidence': [
                    {
                        'question': random_single_select_question.pk,
                        'answers': [invalid_answer.pk]
                    },
                    {
                        'question': random_text_question.pk,
                        'value': 'invalid'
                    }
                ],
                'date_of_completion': '2021'
            }

        return payload

    def test_retrieve_milestone_without_being_authenticated(self):
        """1 - Test retrieving a milestone without being authenticated"""
        random_milestone = random.choice(self.created_milestones)
        response = self.client.get(self._get_endpoint(random_milestone.uid))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_milestone_while_being_authenticated_as_entrepreneur(self):
        """2.1 - Test retrieving a milestone while being authenticated as Entrepreneur"""
        self.client.force_authenticate(user=self.new_user)
        random_milestone = random.choice(self.created_milestones)
        response = self.client.get(self._get_endpoint(random_milestone.uid))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        validate(instance=response.data, schema=MILESTONE_SCHEMA)

    def test_retrieve_milestone_while_being_authenticated_as_supporter(self):
        """2.2 - Test retrieving a milestone while being authenticated as Supporter"""
        self.client.force_authenticate(user=self.supporter.user_profile.user)
        random_milestone = random.choice(self.created_milestones)
        response = self.client.get(self._get_endpoint(random_milestone.uid))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        validate(instance=response.data, schema=MILESTONE_SCHEMA)

    def test_updating_milestone_without_being_authenticated(self):
        """3 - Test updating a milestone without being authenticated"""
        random_milestone = random.choice(self.created_milestones)
        response = self.client.patch(self._get_endpoint(random_milestone.uid), format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_updating_milestone_as_entrepreneur_with_cleared_fields(self):
        """4.1.1 - Test updating a milestone as Entrepreneur with cleared fields on both plan and evidence"""
        self.client.force_authenticate(user=self.new_user)
        random_milestone = random.choice(self.created_milestones)
        payload = self.get_payload({
            'with_cleared_fields': True
        })

        response = self.client.patch(self._get_endpoint(random_milestone.uid), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.json()['errors']
        is_invalid_milestone = errors['non_field_errors'][0]['code'] == 'invalid_milestone'
        self.assertTrue(is_invalid_milestone)

    def test_updating_milestone_as_entrepreneur_with_cleared_evidence_without_publishing_flag(self):
        """4.1.2 - Test updating a milestone as Entrepreneur with cleared evidence without publishing flag"""
        self.client.force_authenticate(user=self.new_user)
        random_milestone = random.choice(self.created_milestones)
        # Add plan field:
        random_milestone.target_date = date.today().strftime("%Y-%m-%d")
        random_milestone.save()
        payload = {
            'evidence': [],
            'date_of_completion': None
        }
        response = self.client.patch(self._get_endpoint(random_milestone.uid), payload, format='json')
        random_milestone.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(random_milestone.evidence_published, False)
        self.assertEqual(random_milestone.state, Milestone.TO_BE_PLANNED_STATE)

    def test_updating_milestone_as_entrepreneur_with_cleared_plan_without_publishing_flag(self):
        """4.1.3 - Test updating a milestone as Entrepreneur with cleared plan without publishing flag"""
        self.client.force_authenticate(user=self.new_user)
        random_milestone = random.choice(self.created_milestones)
        # 1 - Add published plan:
        complete_plan_payload = self.get_payload({
            'with_plan': {'to_publish': True}
        })
        response = self.client.patch(self._get_endpoint(random_milestone.uid), complete_plan_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        random_milestone.refresh_from_db()
        self.assertEqual(random_milestone.plan_published, True)

        # 2 - Clear plan fields:
        # 2.1 - Get payload with cleared fields:
        cleared_plan_payload = self.get_payload({
            'with_cleared_fields': True
        })
        # 2.2 - Exclude cleared evidence fields:
        del cleared_plan_payload['evidence']
        del cleared_plan_payload['date_of_completion']
        # 2.3 - Check milestone published state:
        response = self.client.patch(self._get_endpoint(random_milestone.uid), cleared_plan_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        random_milestone.refresh_from_db()
        self.assertEqual(random_milestone.plan_published, False)

    def test_updating_milestone_as_entrepreneur_with_invalid_values_for_plan(self):
        """4.1.4 - Test updating a milestone as Entrepreneur with invalid values for milestone plan"""
        self.client.force_authenticate(user=self.new_user)
        random_milestone = random.choice(self.created_milestones)
        payload = self.get_payload({
            'with_plan': {'valid': False},
        })
        response = self.client.patch(self._get_endpoint(random_milestone.uid), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        errors = response.json()['errors']
        has_invalid_target_date = errors['target_date'][0]['code'] == 'invalid'
        has_invalid_outcomes = errors['outcomes'][0]['code'] == 'invalid'
        has_invalid_resources = errors['resources'][0]['code'] == 'invalid'
        has_invalid_finances = errors['finances_needed'][0]['code'] == 'min_value'
        self.assertTrue(all([has_invalid_target_date, has_invalid_outcomes,
                             has_invalid_resources, has_invalid_finances]))

    def test_updating_milestone_as_entrepreneur_with_missing_fields_for_plan_publication(self):
        """4.1.5 - Test updating a milestone as Entrepreneur with missing fields for plan publication"""
        self.client.force_authenticate(user=self.new_user)
        milestone_without_plan = Milestone.objects.filter(
            user_profile=self.new_user_profile, resources__exact='').first()
        payload = self.get_payload({
            'with_plan': {'complete': False, 'to_publish': True},
        })
        response = self.client.patch(self._get_endpoint(milestone_without_plan.uid), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        errors = response.json()['errors']
        has_incomplete_plan = errors['non_field_errors'][0]['code'] == 'incomplete_plan'
        self.assertTrue(has_incomplete_plan)

    def test_updating_milestone_as_entrepreneur_with_invalid_values_for_evidence(self):
        """4.1.6 - Test updating a milestone as Entrepreneur with invalid values for milestone evidence"""
        self.client.force_authenticate(user=self.new_user)
        random_milestone = random.choice(self.created_milestones)
        payload = self.get_payload({
            'with_evidence': {'valid': False},
        })
        response = self.client.patch(self._get_endpoint(random_milestone.uid), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        errors = response.json()['errors']
        has_invalid_date_of_completion = errors['date_of_completion'][0]['code'] == 'invalid'
        has_invalid_evidence = all(error['code'] == 'invalid' for error in errors['evidence'][0]['answers'])
        self.assertTrue(all([has_invalid_date_of_completion, has_invalid_evidence]))

    def test_updating_milestone_as_entrepreneur_with_missing_fields_for_evidence_publication(self):
        """4.1.7 - Test updating a milestone as Entrepreneur with missing fields for evidence publication"""
        self.client.force_authenticate(user=self.new_user)
        milestone_without_evidence = Milestone.objects.filter(
            user_profile=self.new_user_profile, evidence=None).first()
        payload = self.get_payload({
            'with_evidence': {'complete': False, 'to_publish': True},
        })
        response = self.client.patch(self._get_endpoint(milestone_without_evidence.uid), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        errors = response.json()['errors']
        has_incomplete_evidence = errors['non_field_errors'][0]['code'] == 'incomplete_evidence'
        self.assertTrue(has_incomplete_evidence)

    def test_updating_milestone_as_entrepreneur_with_fields_for_plan_draft(self):
        """4.1.8 - Test updating a milestone as Entrepreneur with fields to add plan in draft mode"""
        self.client.force_authenticate(user=self.new_user)
        milestone_without_plan = Milestone.objects.filter(
            user_profile=self.new_user_profile, resources__exact='', plan_published=False).first()
        payload = self.get_payload({
            'with_plan': {'to_publish': False},
        })
        response = self.client.patch(self._get_endpoint(milestone_without_plan.uid), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Ensure milestone isn't complete:
        milestone_without_plan.refresh_from_db()
        milestone_without_plan.evidence_published = False
        milestone_without_plan.date_of_completion = None
        milestone_without_plan.save()

        self.assertTrue(milestone_without_plan.state == Milestone.TO_BE_PLANNED_STATE)

    def test_updating_milestone_as_entrepreneur_with_fields_for_evidence_draft(self):
        """4.1.9 - Test updating a milestone as Entrepreneur with fields to add evidence in draft mode"""
        self.client.force_authenticate(user=self.new_user)
        milestone_without_evidence = Milestone.objects.filter(
            user_profile=self.new_user_profile, evidence=None).first()
        payload = self.get_payload({
            'with_evidence': {'complete': True, 'to_publish': False},
        })
        response = self.client.patch(self._get_endpoint(milestone_without_evidence.uid), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        milestone_without_evidence.refresh_from_db()
        self.assertTrue(milestone_without_evidence.state == Milestone.IN_PROGRESS_STATE)

    def test_updating_milestone_as_entrepreneur_with_fields_to_publish_plan(self):
        """4.1.10 - Test updating a milestone as Entrepreneur with fields to publish a plan"""
        self.client.force_authenticate(user=self.new_user)
        milestone_without_plan_published = Milestone.objects.filter(
            user_profile=self.new_user_profile, plan_published=False).first()
        payload = self.get_payload({
            'with_plan': {'complete': True, 'to_publish': True},
        })
        response = self.client.patch(self._get_endpoint(milestone_without_plan_published.uid), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Ensure milestone isn't complete:
        milestone_without_plan_published.refresh_from_db()
        milestone_without_plan_published.evidence_published = False
        milestone_without_plan_published.date_of_completion = None
        milestone_without_plan_published.save()

        self.assertTrue(milestone_without_plan_published.state == Milestone.PLANNED_STATE)

    def test_updating_milestone_as_entrepreneur_with_fields_to_complete_with_evidence(self):
        """4.1.11 - Test updating a milestone as Entrepreneur with fields to complete with evidence"""
        self.client.force_authenticate(user=self.new_user)
        milestone_without_evidence = Milestone.objects.filter(
            user_profile=self.new_user_profile, evidence=None).first()
        payload = self.get_payload({
            'with_evidence': {'complete': True, 'to_publish': True},
        })
        response = self.client.patch(self._get_endpoint(milestone_without_evidence.uid), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        milestone_without_evidence.refresh_from_db()
        self.assertTrue(milestone_without_evidence.state == Milestone.COMPLETED_STATE)

    def test_updating_milestone_as_entrepreneur_with_plan_while_removing_evidence(self):
        """4.1.12 - Test updating a milestone as an Entrepreneur with a plan while removing evidence"""
        self.client.force_authenticate(user=self.new_user)
        milestone = self.created_milestones.filter(
            state=Milestone.COMPLETED_STATE).order_by('-category_level__level__value').first()
        response = ResponseFactory()
        # Change completed milestone to in-progress with a plan field:
        milestone.evidence.set([response])
        milestone.target_date = date.today().strftime("%Y-%m-%d")
        milestone.evidence_published = False
        milestone.save()
        # Ask for evidence removal:
        payload = {
            'evidence': [],
            'date_of_completion': None
        }
        response = self.client.patch(self._get_endpoint(milestone.uid), payload, format='json')
        milestone.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(milestone.state == Milestone.TO_BE_PLANNED_STATE)

    def test_updating_milestone_as_supporter(self):
        """4.2 - Test updating a milestone while being authenticated as Supporter"""
        self.client.force_authenticate(user=self.supporter.user_profile.user)
        random_milestone = random.choice(self.created_milestones)
        response = self.client.patch(self._get_endpoint(random_milestone.uid))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_deleting_milestone_without_being_authenticated(self):
        """5 - Test deleting a milestone without being authenticated"""
        random_milestone = random.choice(self.created_milestones)
        response = self.client.delete(self._get_endpoint(random_milestone.uid))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_deleting_milestone_as_entrepreneur_without_being_owner(self):
        """6.1.1 - Test deleting a milestone as an Entrepreneur without being the owner"""
        random_entrep_profile = UserProfileFactory()
        self.client.force_authenticate(user=random_entrep_profile.user)
        random_milestone = random.choice(self.created_milestones)
        response = self.client.delete(self._get_endpoint(random_milestone.uid))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_deleting_milestone_as_entrepreneur_while_being_owner_with_above_milestones_completed(self):
        """6.1.2.1 - Test deleting a milestone as an Entrepreneur while being the owner
        with above milestones completed"""
        self.client.force_authenticate(user=self.new_user)
        completed_milestones = self.created_milestones.filter(
            state=Milestone.COMPLETED_STATE).order_by('category_level__category__pk')
        lower_milestone = None
        milestones_by_category = groupby(completed_milestones,
                                         key=lambda milestone: milestone.category_level.category.pk)
        for _, grouped_milestones in milestones_by_category:
            category_milestones = list(grouped_milestones)
            if len(category_milestones) > 1:
                lower_milestone = category_milestones[0]
                break

        response = self.client.delete(self._get_endpoint(lower_milestone.uid))
        errors = response.json()['errors']
        has_above_milestones_completed = errors[0]['code'] == 'invalid'
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(has_above_milestones_completed)

    def test_deleting_milestone_as_entrepreneur_while_being_owner_with_below_milestones_completed(self):
        """6.1.2.2 - Test deleting a milestone as an Entrepreneur while being the owner
        with below milestones completed"""
        self.client.force_authenticate(user=self.new_user)
        highest_milestone = self.created_milestones.filter(
            state=Milestone.COMPLETED_STATE).order_by('-category_level__level__value').first()
        response = self.client.delete(self._get_endpoint(highest_milestone.uid))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_deleting_milestone_as_supporter(self):
        """6.2 - Test deleting a milestone while being authenticated as a Supporter"""
        self.client.force_authenticate(user=self.supporter.user_profile.user)
        random_milestone = random.choice(self.created_milestones)
        response = self.client.delete(self._get_endpoint(random_milestone.uid))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
