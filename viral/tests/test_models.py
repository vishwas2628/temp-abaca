from django.test import TestCase

from viral.tests.factories import UserGuestFactory


class UserGuestTestCase(TestCase):
    def test_str(self):
        """Test for string representation"""
        user = UserGuestFactory()
        self.assertEqual(str(user), user.name)
