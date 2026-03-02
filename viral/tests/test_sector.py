from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.urls import reverse
from viral.models import Sector, Group
from viral.serializers import SectorWithGroupsSerializer


class TestSector(APITestCase):
    """Test module for sectors API"""

    SECTOR = {
        'name': 'Sector A',
        'uuid': '9795a225-fca0-4cc0-8895-a8548a0015b4'
    }

    def setUp(self):
        group = Group.objects.create(name="Group A")
        sector = Sector.objects.create(**self.SECTOR)
        sector.groups.add(group)

    def test_get_sectors(self):
        response = self.client.get(reverse('get_sectors'), {
                                   'filter': self.SECTOR['name']})
        sector = Sector.objects.get(uuid=self.SECTOR['uuid'])
        serializer = SectorWithGroupsSerializer(sector)
        self.assertEqual(response.data[0], serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
