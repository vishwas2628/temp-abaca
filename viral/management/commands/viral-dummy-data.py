from django.core.management.base import BaseCommand

from django.contrib.auth.models import User
from viral.models.sector import Sector
from viral.models.location import Location
from viral.models.company import Company
from viral.models.user_profile import UserProfile
from viral.models.relationship import Relationship
from viral.models.affiliate import Affiliate
from datetime import date


class Command(BaseCommand):
    help = 'Seed Viral Database with dummy data'

    def handle(self, *args, **options):
        # Clear database
        Relationship.objects.all().delete()
        UserProfile.objects.all().delete()
        Company.objects.all().delete()
        User.objects.all().delete()
        Sector.objects.all().delete()
        Location.objects.all().delete()

        # Companies
        companyPks = Company.objects.bulk_create([
            Company(
                name="Company 0", logo="https://www.company_0.com/logo.png",
                description="Company 0", website="https://www.company_0.com",
                email="company_0@mail.com", founded_date=date.today(),
                investing_level_range="[2,4)"),
            Company(
                name="Company 1", logo="https://www.company_1.com/logo.png",
                description="Company 1", website="https://www.company_1.com",
                email="company_1@mail.com", founded_date=date.today(),
                investing_level_range="(6,8)"), ])

        # Sectors and Locations
        for index, company in enumerate(Company.objects.all(), 0):
            sector = Sector.objects.create(
                name="Sector " + str(index), uuid="123e4567-e89b-12d3-a456-42665544000" + str(index))
            company.sectors.add(sector)
            location = Location.objects.create(
                formatted_address="Location " + str(index), latitude=0.0, longitude=0.0)
            company.locations.add(location)

        # Affiliate
        affiliate = Affiliate.objects.create(
            name="Affiliate", shortcode="Afil", email="affiliate@mail.com", website="http://www.affiliate.com",
            logo="http://www.affiliate.com/photo.png", spreadsheet="http://www.affiliate.com/spreadsheet")

        # User Profiles
        for index in range(2):
            user = User.objects.create(
                username="user_profile_" + str(index),
                email="user_profile_" + str(index) + "@mail.com",
                password=str(index))
            UserProfile.objects.create(
                user=user, company=companyPks[index],
                source=affiliate, type=index, photo="https://www.user_profile.com/photo.png")

        # Relationships
        userProfiles = UserProfile.objects.all()
        Relationship.objects.create(
            investor=userProfiles[0], entrepreneur=userProfiles[1], creator=userProfiles[1], match=True)

        self.stdout.write(self.style.SUCCESS(
            'Successfully seeded Viral Database with dummy data'))
