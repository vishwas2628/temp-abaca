from django.apps import apps
from django.db import migrations
from shared.execute_raw_sql import ExecuteRawSQL

# Specify algorithm version and directory path containing SQL files
algorithm_version = '1.1'
algorithm_path = apps.get_app_config('matching').path + '/algorithm/' + algorithm_version

# Instantiate class that will execute SQL files through migration
algorithm = ExecuteRawSQL(algorithm_path)


class Migration(migrations.Migration):
    dependencies = [
        ('matching', '0056_fix_locations_comparion'),
    ]

    operations = [
        migrations.RunPython(algorithm.load_sql),
    ]
