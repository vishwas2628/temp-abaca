import settings

from django.core.management import call_command
from django.core.management.base import BaseCommand

from viral.models import Affiliate


class Command(BaseCommand):
    help = 'Script to load database fixtures'

    """
    List of ordered fixtures to avoid breaking 
    fixtures that depend on each other.
    """
    fixtures = [
        'users',
        'email_addresses',
        'category_groups',
        'categories',
        'level_groups',
        'levels',
        'category_levels',
        'location_groups',
        'locations',
        'networks',
        'companies',
        'affiliate_webhooks',
        'affiliates',
        'user_guest',
        'user_profiles',
        'profile_id_fields',
        'criteria_weights',
        'question_types',
        'question_categories',
        'questions',
        'answers',
        'supporter_types',
        'supporters',
        'supporter_offering_categories',
        'supporter_offering_types',
        'supporter_offerings',
        'criteria',
        'question_bundles',
        'assessments',
        'connections',
        'responses',
        'milestones',
        'vendors'
    ]

    def add_arguments(self, parser):
        parser.add_argument('-o', '--only', nargs='+', help='Only load specified fixture(s).', choices=self.fixtures)
        parser.add_argument('-e', '--exclude', nargs='+',
                            help='Exclude fixture(s) from being loaded.', choices=self.fixtures)

    def load_fixtures(self, only=[], excluded=[]):
        fixtures_to_load = only if len(only) else self.fixtures

        for fixture in fixtures_to_load:
            print(fixture)
            if fixture in excluded:
                print("Fixture excluded.")
            else:
                call_command('loaddata', fixture, verbosity=1)
            print("\r")

    def update_fixtures(self):
        # Due to a circular dependency (Affiliate <=> Supporter <=> UserProfile)
        # this needs to be done after adding fixtures:
        # 1 - Set Question Bundle for Entrepreneur Affiliate:
        question_bundle_flow = Affiliate.objects.get(pk=2)
        question_bundle_flow.supporters.set([1])
        question_bundle_flow.question_bundles.set([1])
        question_bundle_flow.save()
        # 2 - Set Question Bundle for Supporter Affiliates:
        supporter_affiliates = Affiliate.objects.filter(pk__in=[3, 4])
        for affiliate in supporter_affiliates:
            affiliate.supporters.set([1])
            affiliate.question_bundles.set([3])

    def handle(self, *args, **options):
        requested_fixtures = options.get('only') or []
        excluded_fixtures = options.get('exclude') or []

        if settings.IS_LIVE_ENVIRONMENT and settings.IS_TEST_ENVIRONMENT:
            print("Cannot load fixtures in production.")
            return

        self.load_fixtures(only=requested_fixtures, excluded=excluded_fixtures)
        self.update_fixtures()
