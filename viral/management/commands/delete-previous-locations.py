from django.core.management.base import BaseCommand
from viral.models.company import Company


class Command(BaseCommand):
    help = 'Script to delete previous selected locations on companies'

    def handle(self, *args, **options):
        companies = Company.objects.all()

        for company in companies:
            company_locations = company.locations.order_by(
                '-created_at')[1:]

            for location in company_locations:
                location.delete()
