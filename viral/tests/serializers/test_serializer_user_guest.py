from django.test import TestCase

from viral.serializers import UserGuestSerializer
from viral.tests.factories import UserGuestFactory


class UserGuestSerializerTest(TestCase):
    def test_model_fields(self):
        """Serializer data matches the UserGuest object for each field."""
        model = UserGuestFactory()
        serializer = UserGuestSerializer(model)

        for field_name in ['id', 'name', 'email']:
            self.assertEqual(
                serializer.data[field_name],
                getattr(model, field_name)
            )
