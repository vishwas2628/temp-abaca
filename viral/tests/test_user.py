from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.urls import reverse
from unittest import mock

from allauth.utils import get_user_model
from django.contrib.auth.models import User
from allauth.account.models import EmailAddress, EmailConfirmationHMAC

from viral.models import Sector, Group, Affiliate
from grid.models import Category, Level, CategoryGroup, LevelGroup

from shared.utils import AbacaAPITestCase


class TestUser(AbacaAPITestCase):
    """
    Test module for users API:
    * 1 - Updating existing user's email
    * 2 - Updating existing user's password
    * 3 - Requesting a password reset
    * 3.1 - With invalid email
    * 3.2 - With valid email (case-sensitive)
    * 3.3 - With valid email (case-insensitive)
    * 4 - Creating an assessment for an existing user
    """

    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_user(
            username="user",
            email="user@mail.com",
            password="password"
        )
        self.user.save()
        EmailAddress.objects.create(
            user=self.user,
            email=self.user.email,
            verified=True,
            primary=True)
        self.client.force_authenticate(user=self.user)

    def test_update_email(self):
        # 1 - Updating existing user's email
        response = self.client.post(reverse('update_email'), {
            "email": "new_email@mail.com",
            "password": "password"
        }, format='json')
        self.assertEquals(response.status_code, 200)

    def test_change_password(self):
        # 2 - Updating existing user's password
        response = self.client.post(reverse('change_password'), {
            "old_password": "password",
            "new_password1": "password2",
            "new_password2": "password2"
        }, format='json')
        self.assertEquals(response.status_code, 200)

    @mock.patch("viral.serializers.sendForgotPasswordEmail")
    def test_reset_password_with_invalid_email(self, mocked_email_callback):
        # 3.1 - Requesting a password reset with invalid email
        response = self.client.post(reverse('send_reset_password'), {
            "email": "invalid@mail.com"
        }, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertFalse(mocked_email_callback.called)

    @mock.patch("viral.serializers.sendForgotPasswordEmail")
    def test_reset_password_with_valid_email_case_sensitive(self, mocked_email_callback):
        # 3.2 - Requesting a password reset with valid email (case-sensitive)
        response = self.client.post(reverse('send_reset_password'), {
            "email": "user@mail.com"
        }, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertTrue(mocked_email_callback.called)

    @mock.patch("viral.serializers.sendForgotPasswordEmail")
    def test_reset_password_with_valid_email_case_insensitive(self, mocked_email_callback):
        # 3.3 - Requesting a password reset with valid email (case-insensitive)
        response = self.client.post(reverse('send_reset_password'), {
            "email": "USER@MAIL.com"
        }, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertTrue(mocked_email_callback.called)

    def test_self_assessment_creation(self):
        # 4 - Creating an assessment for an existing user
        category_group, created = CategoryGroup.objects.get_or_create(
            slug="entrepreneurs")

        level_group, created = LevelGroup.objects.get_or_create(
            slug="entrepreneurs")

        new_category = {
            'name': 'Category 1',
            'requirements_title': 'tip_title',
            'color': '#fff',
            'abbreviation': 'cat1',
            'order': 1,
            'group': category_group
        }

        new_level = {
            'title': 'Level 1',
            'description': 'level description',
            'value': 1,
            'group': level_group
        }

        new_affiliate = {
            'name': 'New Affiliate',
            'shortcode': 'newaf',
            'email': 'email@mail.com',
            'website': 'http://website.com',
            'logo': 'http://logo.com'
        }

        self.category = Category.objects.create(**new_category)
        self.level = Level.objects.create(**new_level)
        self.affiliate = Affiliate.objects.create(**new_affiliate)

        first_sector = Sector.objects.first()

        payload = {
            "email": "jondoe@mail.com",
            "company": {
                "name": "Company",
                "location": {
                    "formatted_address": "example address",
                    "latitude": 0.0,
                    "longitude": 0.0
                },
                "sectors": [first_sector.id],
                "website": "company.com",
            },
            "levels": [
                {
                    "category": self.category.id,
                    "level": self.level.value
                }
            ],
            "affiliate": self.affiliate.id,
            "group": level_group.id,
        }
        response = self.client.post(
            reverse('self_assessment'), payload, format='json')
        self.assertEquals(response.status_code, 201)
