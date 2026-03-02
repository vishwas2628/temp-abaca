import random
from django.urls.base import reverse
from jsonschema.validators import validate
from rest_framework import status

from matching.models import Question
from matching.tests.factories import QuestionBundleFactory
from matching.tests.schemas.question_bundle_schema import PAGINATED_LIST_OF_QUESTION_BUNDLES_SCHEMA
from shared.utils import AbacaAPITestCase


class TestListQuestionBundlesView(AbacaAPITestCase):
    """
    Test listing Question Bundles:
    * 1 - Without filters
    * 2 - Filtered by Category
    * 3 - Filtered by Category Level
    """
    ENDPOINT = reverse('list_question_bundles')

    fixtures = ['level_groups', 'category_groups', 'levels', 'categories',
                'category_levels', 'profile_id_fields', 'question_types', 'question_categories', 'questions', 'answers']

    def setUp(self):
        super().setUp()
        all_questions = list(Question.objects.all())
        random_questions = random.sample(all_questions, 5)
        self.category_question_bundle = QuestionBundleFactory(questions=random_questions, with_category=True)
        self.category_level_question_bundle = QuestionBundleFactory(
            questions=random_questions, with_category_level=True)

    def test_list_question_bundles_without_filters(self):
        """1 - Test listing Question Bundles without filters"""
        response = self.client.get(self.ENDPOINT)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        validate(instance=response.data, schema=PAGINATED_LIST_OF_QUESTION_BUNDLES_SCHEMA)

    def test_list_question_bundles_filtered_by_category(self):
        """2 - Test listing Question Bundles filtered by Category"""
        endpoint_filtered_by_category = f'{self.ENDPOINT}?category={self.category_question_bundle.category.pk}'
        response = self.client.get(endpoint_filtered_by_category)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        validate(instance=response.data, schema=PAGINATED_LIST_OF_QUESTION_BUNDLES_SCHEMA)
        has_category_question_bundle = response.data['results'][0]['id'] == self.category_question_bundle.pk
        self.assertTrue(has_category_question_bundle)

    def test_list_question_bundles_filtered_by_category_level(self):
        """3 - Test listing Question Bundles filtered by Category Level"""
        endpoint_filtered_by_category_level = f'{self.ENDPOINT}?category_level={self.category_level_question_bundle.category_level.pk}'
        response = self.client.get(endpoint_filtered_by_category_level)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        validate(instance=response.data, schema=PAGINATED_LIST_OF_QUESTION_BUNDLES_SCHEMA)
        has_category_level_question_bundle = response.data['results'][0]['id'] == self.category_level_question_bundle.pk
        self.assertTrue(has_category_level_question_bundle)
