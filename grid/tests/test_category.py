import sys

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from grid.models import Category, Level, CategoryLevel, CategoryGroup, LevelGroup
from grid.serializers import CategorySerializer, CategoryLevelSerializer


class GetCategories(APITestCase):
    """Test module for GET all categories API"""

    def setUp(self):
        category_group, created = CategoryGroup.objects.get_or_create(
            slug="supporters")
        self.category_group_id = category_group.id

        category = Category.objects.create(
            name="name", requirements_title="requirements_title", color="color", abbreviation="abbreviation",
            order=0, group=category_group, value_type="SINGLE")

        level_group = LevelGroup.objects.create(slug="supporters")
        self.level_value = 1

        level = Level.objects.create(
            value=self.level_value, title="title", description="description", group=level_group)

        CategoryLevel.objects.create(achievements="achievements",
                                     description="description",
                                     requirements="requirements",
                                     next_milestones_title="<p>test</p>",
                                     next_milestones_description="<p>test</p>",
                                     achieved_milestones_title="<p>test</p>",
                                     achieved_milestones_description="<p>test</p>",
                                     category=category,
                                     level=level)

    def test_get_categories(self):
        response = self.client.get(reverse('get_categories'), {
                                   'group': self.category_group_id})
        response_value = response.data[-1]['categoryDetails'][0]['level']['value']

        self.assertEquals(response_value, self.level_value)
