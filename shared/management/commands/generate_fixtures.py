import json

from django.core.management.base import BaseCommand

from shared.generators import (AssessmentsGenerator, EntrepreneursGenerator,
                               SupportersGenerator)


class Command(BaseCommand):
    """
    Generates mock data for E2E testing.

    Required arguments:
    * -f, --fixture : Selectable option from AVAILABLE_GENERATORS

    Optional arguments
    * -l, --length : Amount of fixtures to generate
    """
    AVAILABLE_GENERATORS = {
        'assessments': AssessmentsGenerator,
        'entrepreneurs': EntrepreneursGenerator,
        'supporters': SupportersGenerator
    }

    DEFAULT_FIXTURES_LENGTH = 30

    # File that will contain the generated fixtures
    FIXTURES_FILENAME = 'generated-fixtures'

    help = 'Script to generate database fixtures'

    def add_arguments(self, parser):
        parser.add_argument(
            '-f', '--fixture', help='Fixture to generate', choices=self.AVAILABLE_GENERATORS.keys())
        parser.add_argument(
            '-l', '--length', help='Length of fixtures to generate', type=int)

    def handle(self, *args, **options):
        requested_fixture = options.get('fixture')
        requested_fixtures_length = options.get(
            'length') or self.DEFAULT_FIXTURES_LENGTH

        if requested_fixture in self.AVAILABLE_GENERATORS:
            generator = self.AVAILABLE_GENERATORS[requested_fixture](
                amount=requested_fixtures_length)
            fixtures = generator.get_fixtures()

            with open('%s.json' % self.FIXTURES_FILENAME, 'w') as outfile:
                json.dump(fixtures, outfile)
