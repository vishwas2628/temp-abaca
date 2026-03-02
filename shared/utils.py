import re
from unittest.mock import patch

import settings

from django.apps import apps
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.db.models import signals
from django.test.runner import DiscoverRunner
from django.utils.encoding import smart_text
from django.utils.translation import gettext_lazy as _
from faker import Faker
from rest_framework import serializers
from rest_framework.test import APITestCase
from rest_framework.pagination import PageNumberPagination

from viral.signals import (created_or_updated_assessment,
                           created_or_updated_company,
                           created_or_updated_supporter,
                           created_updated_or_deleted_criteria,
                           created_updated_or_deleted_response)


class AbacaAPITestCase(APITestCase):
    """
    Adds utility to generate mock data
    Disables unwanted signals
    Mocks calls to third-party services (Mailjet, Google Spreadsheets)
    """
    faker = Faker()
    skip_signals = (
        ('post_save', created_or_updated_company, apps.get_model('viral', 'Company')),
        ('post_save', created_or_updated_assessment, apps.get_model('grid', 'Assessment')),
        ('post_save', created_or_updated_supporter, apps.get_model('matching', 'Supporter')),
        ('post_save', created_updated_or_deleted_criteria, apps.get_model('matching', 'Criteria')),
        ('post_delete', created_updated_or_deleted_criteria, apps.get_model('matching', 'Criteria')),
        ('post_save', created_updated_or_deleted_response, apps.get_model('matching', 'Response')),
        ('post_delete', created_updated_or_deleted_response, apps.get_model('matching', 'Response')),
    )

    def _prevent_signals(self):
        for skip in self.skip_signals:
            signal = getattr(signals, skip[0])
            signal.disconnect(skip[1], skip[2])

    def _create_super_user(self):
        self.super_user = User.objects.create_superuser(
            'superuser',
            'superuser@mail.com',
            'secret'
        )

    def get_payload(self, selected_options={}):
        """
        Helper method that builds the request payload by calling
        custom payload methods from each passed dictionary keys:

        Usage:
        * payload = self.get_payload({'with_token': True, 'with_user': {'id': 1}})
        It will look for and call these custom methods:
        * self._payload_with_token(payload)
        * self._payload_with_user(payload, {'id': 1})

        These custom methods must return the payload argument which will be shared
        with all the other custom payload methods to be in the end returned by this method.
        """
        payload = {}

        if len(selected_options):
            for selected_option, option_settings in selected_options.items():
                payload_method_name = '_payload_' + selected_option
                assert hasattr(
                    self, payload_method_name), f"Make sure you have created this method: {payload_method_name}"

                if hasattr(self, payload_method_name):
                    payload_method = getattr(self, payload_method_name)
                    payload = payload_method(
                        payload, **option_settings) if isinstance(option_settings, dict) else payload_method(payload)
                    assert isinstance(payload, dict), "Make sure you return the payload argument as a dictionary."

        return payload

    def setUp(self):
        patch('shared.mailjet.mailjet.Client').start()
        patch('viral.utils.gspread').start()

    def __init__(self, methodname):
        super().__init__(methodname)
        self._prevent_signals()


class DivioTestSuiteRunner(DiscoverRunner):
    """
    A custom test runner to run tests within Divio
    that accounts for the fact that we don't have 
    permissions to create separate databases.

    Usage:
    ./manage.py test --verbosity=3 --failfast --testrunner=shared.utils.DivioTestSuiteRunner
    """

    def setup_databases(self, **kwargs):
        # Disable creation of separate database and restore savepoint
        if settings.APP_ENV in ['dev', 'qa']:
            call_command('database_savepoint', action='restore', verbosity=1, matching=True)

    def teardown_databases(self, old_config, **kwargs):
        # No need for teardown since we're restoring on setup
        pass


class CurrentUserProfileDefault:
    """
    To be applied as a `default=...` value on a serializer field.
    Returns the current user profile.
    """

    def set_context(self, serializer_field):
        self.user_profile = serializer_field.context['request'].user.userprofile

    def __call__(self):
        return self.user_profile or None


class UIDRelatedFieldSerializer(serializers.RelatedField):
    """
    Allows:
    1 - Writing a related field using the UID field.
    2 - Reading a related field using a custom serializer.
    """

    default_error_messages = {
        'does_not_exist': _('Object with {field}={value} does not exist.'),
        'invalid': _('Invalid value.'),
    }

    def __init__(self, uid_field='uid', serializer=None, **kwargs):
        assert serializer is not None, 'The `serializer` argument is required.'
        self.serializer = serializer
        self.uid_field = uid_field
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        assert type(data) is str, self.fail('invalid')

        try:
            return self.get_queryset().get(**{self.uid_field: data})
        except ObjectDoesNotExist:
            self.fail('does_not_exist', field=self.uid_field, value=smart_text(data))
        except (TypeError, ValueError):
            self.fail('invalid')

    def to_representation(self, obj):
        serializer = self.serializer(obj, context=self.context)
        return serializer.data


def get_uri_scheme() -> str:
    return 'https://' if settings.STAGE != 'local' else 'http://'


class LargePageNumberPagination(PageNumberPagination):
    page_size = 1000


# Remove "For example" and everything after the Response value
def format_demographic_response_value(value):
    return re.split('[^A-Za-z]*For example', value, flags=re.IGNORECASE)[0].strip()