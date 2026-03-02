import os
import random

from faker import Faker
from slugify import slugify

from shared.models import random_uid


class BaseGenerator():
    """
    Base Generator class

    Contains all reusable helpers to generate mock data.
    """
    fixtures = []

    def __init__(self):
        self.fake = Faker()
        self.slugify = slugify
        self.random = random
        self.random_uid = random_uid

    def _get_random_hex_str(self, length):
        return os.urandom(length).hex()

    def get_fixtures(self):
        return [self.fixtures[fixture]['value']
                for fixture in self.fixtures if 'value' in self.fixtures[fixture]]
