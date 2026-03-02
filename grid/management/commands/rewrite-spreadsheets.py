from django.core.management.base import BaseCommand
from viral.models import Affiliate
from grid.models import Category
from viral.utils import rewrite_affiliate_spreadsheet
import time


class Command(BaseCommand):
    help = 'Rewrite the information written on the spreadsheets.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-a', type=str, help='Select affiliate by its slug',)

    def create_spreadsheet(self, client, affiliate):
        title = 'Abaca Assessments for ' + affiliate.name
        spreadsheet = client.create(title)

        # Update affiliate
        affiliate.spreadsheet = 'https://docs.google.com/spreadsheets/d/' + spreadsheet.id
        affiliate.save()

        return spreadsheet

    def handle(self, *args, **options):
        specific_affiliate_slug = options['a']

        if specific_affiliate_slug is not None:
            affiliate_list = Affiliate.objects.filter(
                slug=specific_affiliate_slug)
        else:
            affiliate_list = Affiliate.objects.all()

        for affiliate_index, affiliate in enumerate(affiliate_list):
            rewrite_affiliate_spreadsheet(affiliate)

            if (affiliate_index + 1 != len(affiliate_list)):
                print("Google API Restrictions: Waiting 30 seconds for next spreadsheet")
                time.sleep(30)
