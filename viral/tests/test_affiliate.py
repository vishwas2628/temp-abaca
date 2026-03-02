from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.urls import reverse
from viral.models import Affiliate
from viral.serializers import AffiliateSerializer


class TestAffiliate(APITestCase):
    """Test module for affiliates API"""

    def setUp(self):
        Affiliate.objects.create(
            name="name", shortcode="123", email="email@mail.com", website="http://website.com", logo="http://logo.com")

    def test_get_affiliate(self):
        response = self.client.get(reverse('get_affiliates'))
        affiliates = Affiliate.objects.all()
        serializer = AffiliateSerializer(affiliates, many=True)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
