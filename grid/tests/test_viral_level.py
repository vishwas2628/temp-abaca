from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.urls import reverse
from allauth.utils import get_user_model
from grid.models import Category, Level, CategoryGroup, LevelGroup


class GetViralLevel(APITestCase):
    """Test model for GET viral level"""

    def setUp(self):
        category_group1, created = CategoryGroup.objects.get_or_create(
            slug="supporters")
        category_group2, created = CategoryGroup.objects.get_or_create(
            slug="entrepreneurs")

        level_group, created = LevelGroup.objects.get_or_create(
            slug="entrepreneurs")

        self.categoryA = Category.objects.create(
            name="name", group=category_group1, requirements_title="requirements_title", color="color", abbreviation="abb1")
        self.categoryB = Category.objects.create(
            name="name", group=category_group2, requirements_title="requirements_title", color="color", abbreviation="abb2")
        self.level = Level.objects.create(
            value=1, group=level_group, title="title", description="description")
        self.payload = {
            'levels': [
                {
                    'category': self.categoryA.id,
                    'level': self.level.value
                },
                {
                    'category': self.categoryB.id,
                    'level': None
                }
            ],
            'group': level_group.id
        }

    def test_calculate_viral_level(self):
        response = self.client.post(
            reverse('calculate_viral_level'),
            self.payload,
            format='json'
        )
        self.assertEquals(response.status_code, 200)
