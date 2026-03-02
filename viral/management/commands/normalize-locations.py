import requests

from django.core.management.base import BaseCommand

from viral.models import Location
from viral.data.geo_countries_continents import GEO_COUNTRIES_CONTINENTS


class Command(BaseCommand):
    """
    This command was built initially to normalize existing locations without continents:
    https://pixelmatters.atlassian.net/projects/VIR/issues/VIR-581
    """
    help = 'Normalize locations\' data'
    locations = Location.objects.all()

    gmaps_url = 'https://maps.googleapis.com/maps/api/geocode/json?'
    gmaps_key = 'AIzaSyAq1HB__RCHgh2KHt4MfsYhUPDqqocgQzo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--missing-continents',
            action='store_true',
            help='Populate missing continents',
        )

    def _get_location_attr(self, components, meta, attr_value='long_name'):
        for value in components:
            if value["types"].count(meta) > 0:
                return value[attr_value]

        return None

    def _search_gmaps(self, params):
        url = '{base}{params}'.format(
            base=self.gmaps_url, params=params)
        response = requests.get(url)
        return response.json()

    def _get_value_from(self, obj, keys):
        final_value = obj
        for key in keys:
            if isinstance(key, str) and key in final_value or isinstance(key, int) and len(final_value):
                final_value = final_value[key]
            else:
                break
        return final_value

    def populate_missing_continents(self):
        print("\r")
        print(">> Populating missing continents...")

        locations_without_continent = self.locations.filter(continent='')
        for location in locations_without_continent:
            if (location.latitude != 0 and location.latitude != 1 and location.latitude != 1111):
                params = 'latlng={lat},{lng}&sensor={sen}&key={key}'.format(
                    lat=location.latitude,
                    lng=location.longitude,
                    sen=False,
                    key=self.gmaps_key
                )
                response = self._search_gmaps(params)
                address_components = self._get_value_from(
                    response, ['results', 0, 'address_components'])

                country_short_name = self._get_location_attr(
                    address_components, "country", "short_name")

                if country_short_name and country_short_name in GEO_COUNTRIES_CONTINENTS:
                    print("\r")
                    print("Found continent: ",
                          GEO_COUNTRIES_CONTINENTS[country_short_name])
                    location.continent = GEO_COUNTRIES_CONTINENTS[country_short_name]
                    location.save()

        print(">> Finished")
        print("\r")

    def handle(self, *args, **options):
        is_missing_continents = options.get('missing_continents', False)

        if is_missing_continents:
            self.populate_missing_continents()
