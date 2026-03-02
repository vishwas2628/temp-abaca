from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.urls import reverse
from viral.models import Company, UserProfile
from allauth.utils import get_user_model

from shared.utils import AbacaAPITestCase


class TestCompanies(AbacaAPITestCase):
    """Test module for companies API"""

    def setUp(self):
        super().setUp()
        user = get_user_model().objects.create_user(
            username="Example", email="example@mail.com")
        self.company = Company.objects.create(
            name="Company", type=Company.ENTREPRENEUR)
        UserProfile.objects.create(user=user, company=self.company)
        self.client.force_authenticate(user=user)

    def test_update_company(self):
        pk = self.company.id
        response = self.client.patch(reverse('retrieve_company', args=[pk]), {
                                     "email": "new_email@mail.com"}, format='json')
        self.assertEquals(response.status_code, 200)
