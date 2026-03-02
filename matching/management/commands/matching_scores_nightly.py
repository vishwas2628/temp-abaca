from django.core.management.base import BaseCommand
from django.core.management import CommandError
from django.db import connection


class Command(BaseCommand):
    help = 'Script to run nightly command to compute matching scores'
    valid_scopes = ['level', 'sector', 'location', 'response', 'total']

    def add_arguments(self, parser):
        parser.add_argument('-s', '--scope', type=str, help=f'One of the following: {", ".join(self.valid_scopes)}')

    def handle(self, *args, **options):

        if options['scope'] and not options['scope'] in self.valid_scopes:
            raise CommandError(f'<scope> can only be one of the following: {", ".join(self.valid_scopes)}')

        if options['scope']:
            tasks = [f'perform matching.refresh_{options["scope"]}_score();']
        else:
            tasks = [
                'perform matching.refresh_level_score();',
                'perform matching.refresh_sector_score();',
                'perform matching.refresh_location_score();',
                'perform matching.refresh_response_score();',
                'perform matching.refresh_total_score();',
            ]

        sql_statement = f'do $$ begin {" ".join(tasks)} end $$;'

        with connection.cursor() as c:
            c.execute(sql_statement)
