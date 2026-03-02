from django.core.management.base import BaseCommand
from viral.models import Company
from matching.algorithm import getMatches


class Command(BaseCommand):
    help = 'Script to test matching'

    def handle(self, *args, **options):
        company = Company.objects.get(id=1)
        result = getMatches(company)
        print(result)
