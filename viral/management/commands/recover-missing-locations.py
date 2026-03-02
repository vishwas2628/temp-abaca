from django.db.models import Q
from django.core.management.base import BaseCommand

from viral.models import Company, Location, UserProfile
from shared.models import Logs

from viral.utils import fetch_google_location
from viral.data.geo_countries_continents import GEO_COUNTRIES_CONTINENTS


class Command(BaseCommand):
    """
    This command was built recover missing company locations that resulted from this bug:
    https://pixelmatters.atlassian.net/projects/VIR/issues/VIR-724

    To recover the missing locations, we'll grab the logs for the sent 
    'Verify Account' email that contains the formatted_address
    """
    help = 'Recover missing company locations'

    gmaps_url = 'https://maps.googleapis.com/maps/api/geocode/json?'
    gmaps_key = 'AIzaSyAq1HB__RCHgh2KHt4MfsYhUPDqqocgQzo'

    def _get_location_attr(self, components, meta, attr_value='long_name'):
        for value in components:
            if meta in value["types"]:
                return value[attr_value]

        return None

    def _populate_location_for(self, company, address):
        location_results = fetch_google_location(address)
        location_fields = ['formatted_address', 'latitude',
                           'longitude', 'city', 'region', 'country']

        if location_results:
            location_address = location_results[0]
            address_components = location_address['address_components']

            location_instance = {
                'formatted_address': location_address['formatted_address'],
                'latitude': location_address['geometry']['location']['lat'],
                'longitude': location_address['geometry']['location']['lng'],
                'country': self._get_location_attr(address_components, 'country'),
                'city': self._get_location_attr(address_components, 'locality'),
                'region': self._get_location_attr(address_components, 'administrative_area_level_1') or self._get_location_attr(address_components, 'administrative_area_level_2'),
                'region_abbreviation': self._get_location_attr(address_components, 'administrative_area_level_1', 'short_name') or self._get_location_attr(address_components, 'administrative_area_level_2', 'short_name'),
            }

            # Add continent
            country_short_name = self._get_location_attr(
                address_components, 'country', 'short_name')
            if country_short_name and country_short_name in GEO_COUNTRIES_CONTINENTS:
                location_instance['continent'] = GEO_COUNTRIES_CONTINENTS[country_short_name]

            location = Location.objects.create(**location_instance)
            company.locations.add(location)
            print("Added location.")
        else:
            print("Did not found location.")

    def handle(self, *args, **options):
        entrepreneurs = Company.objects.prefetch_related(
            'locations').filter(type=Company.ENTREPRENEUR)

        for company in entrepreneurs:
            if not company.locations.exists():
                print("\r")
                print("Adding location to: ", company.name)
                try:
                    user_profile = UserProfile.objects.get(company=company)

                    search_by_subject = Q(
                        log__contains='Verify Account') | Q(
                        log__contains='New Company Assessment')
                    search_by_email = Q(
                        log__contains='{email}'.format(email=user_profile.user.email))
                    registration_email = Logs.objects.filter(
                        Q(slug='mailjet') & search_by_subject & search_by_email).first()

                    if registration_email:
                        email_data = eval(registration_email.log)
                        subject = email_data['Messages'][0]['Subject']
                        location = email_data['Messages'][0]['Variables']['data']['company']['location']

                        print("Found email: ", subject)

                        self._populate_location_for(company, location)
                    else:
                        print("Could not find registration email.")

                except (UserProfile.DoesNotExist, Logs.DoesNotExist):
                    print("Missing profile or could not find logs.")
