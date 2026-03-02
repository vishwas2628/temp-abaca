import csv

from django.core.management.base import BaseCommand
from allauth.utils import get_user_model

from viral.models import UserProfile, Company
from matching.models import Supporter


class Command(BaseCommand):
    help = "Fetch the database with supporters read from a CSV"

    def create_user(self, data):
        email = data["email"]
        user = get_user_model().objects.create_user(username=email, email=email)
        return user

    def create_company(self, data):
        supporter_type = 1
        company = Company.objects.create(
            name=data["name"], email=data["email"], about=data["about"], website=data["website"], crunchbase_id=data["crunchbase_id"], type=supporter_type)
        return company

    def create_user_profile(self, data, user, company):
        user_profile = UserProfile.objects.create(user=user, company=company)
        return user_profile

    def create_supporter(self, data, user_profile):
        str_types = data["types"].split(",")
        types = map(lambda x: int(x), str_types)
        investing_range_min = int(
            data["investing_range_min"]) if data["investing_range_min"].isdigit() else 1
        investing_range_max = int(
            data["investing_range_max"]) if data["investing_range_max"].isdigit() else 10
        supporter = Supporter.objects.create(name=data["name"], about=data["about"],
                                             email=data["email"], user_profile=user_profile, investing_level_range=[investing_range_min, investing_range_max])
        supporter.types.set(types)

    def create_entry(self, data):
        user = self.create_user(data)
        company = self.create_company(data)
        user_profile = self.create_user_profile(data, user, company)
        self.create_supporter(data, user_profile)

    def handle(self, *args, **options):
        # Header: name;email;about;types;website;crunchbase_id-,investing_range_min;investing_range_max
        with open("supporters.csv", mode="r") as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=";")

            for row in csv_reader:
                self.create_entry(row)
