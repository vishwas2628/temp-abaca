import settings
import subprocess
from os import system, environ

from django.db import connection
from django.core.management import call_command
from django.core.management.base import BaseCommand

from shared.execute_sql_in_thread import ExecuteSQLInThread


class Command(BaseCommand):
    """
    Creates database savepoints by cloning schema

    Required arguments:
    * -a, --action

    Optional arguments
    * -m, --matching : Runs matching migrations
    """
    help = 'Script to store/restore a database savepoint'

    DROP_TABLES_AND_SCHEMAS_SQL = """
        DO
        $func$
        BEGIN
            IF EXISTS (
                SELECT FROM pg_catalog.pg_class c 
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                AND c.relkind = 'r'
            )
            THEN
                EXECUTE
                (SELECT 'DROP TABLE ' || string_agg(oid::regclass::text, ', ') || ' CASCADE'
                    FROM   pg_class
                    WHERE  relkind = 'r'  -- only tables
                    AND    relnamespace = 'public'::regnamespace
                );
            END IF;
            EXECUTE 'DROP SCHEMA IF EXISTS matching CASCADE';
        END
        $func$;
    """

    TRUNCATE_TABLES_SQL = """
        DO
        $func$
        BEGIN
            EXECUTE
            (SELECT 'TRUNCATE TABLE ' || string_agg(oid::regclass::text, ', ') || ' RESTART IDENTITY CASCADE'
                FROM   pg_class
                WHERE  relkind = 'r'  -- only tables
                AND    relnamespace = 'public'::regnamespace
            );
        END
        $func$;
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '-a', '--action', help='Savepoint action', choices=['setup', 'store', 'restore'])
        parser.add_argument(
            '-m', '--matching', help='Restore with matching', action='store_true')

    def handle(self, *args, **options):
        requested_action = options.get('action')
        requested_matching = options.get('matching')
        default_database_dsn = environ.get('DEFAULT_DATABASE_DSN', None)
        clone_database_dsn = environ.get('CLONE_DATABASE_DSN', None)

        if not default_database_dsn or not clone_database_dsn:
            print('Missing Database DSN environment variables.')
            return

        if settings.IS_LIVE_ENVIRONMENT or settings.IS_TEST_ENVIRONMENT:
            print('Setting up a database savepoint is not allowed on production.')
            return

        # Store and restore savepoints
        with connection.cursor() as cursor:
            try:
                if requested_action == 'setup':
                    # Dump existing tables
                    cursor.execute(self.DROP_TABLES_AND_SCHEMAS_SQL)
                    # Add fresh tables
                    call_command('migrate')
                    # Load fixtures
                    call_command('load_fixtures', '--exclude', 'milestones')
                    # Populate Milestones
                    call_command('migrate', 'milestone_planner', 'zero')
                    call_command('migrate', 'milestone_planner')
                    call_command('load_fixtures', '--only', 'milestones')
                    # Prefill translations
                    call_command('update_translation_fields')
                    # Populate watson search (used for sectors input)
                    call_command('installwatson')
                    call_command('migrate', 'watson', 'zero')
                    call_command('migrate', 'watson')
                    call_command('buildwatson')
                    # Populate matching scores
                    call_command('matching_scores_nightly')

                if requested_action == 'store':
                    system('pg_dump --no-owner --no-privileges --if-exists --clean -n public -n matching ' +
                           f'{default_database_dsn} | psql {clone_database_dsn}')

                if requested_action == 'restore':
                    with_matching = '-n matching' if requested_matching else ''

                    cursor.execute(self.TRUNCATE_TABLES_SQL)
                    system(
                        f'pg_dump -n public {with_matching} --data-only --no-owner --no-privileges {clone_database_dsn} | ' +
                        f'psql {default_database_dsn}')

            except Exception as e:
                print("\r")
                print(e)
                print("\r")
            finally:
                cursor.close()
