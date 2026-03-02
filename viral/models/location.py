from django.db import models

from shared.models import TimestampedModel


class Location(TimestampedModel):
    formatted_address = models.CharField(max_length=512)
    latitude = models.FloatField()
    longitude = models.FloatField()

    city = models.CharField(max_length=200, blank=True, null=True)
    region = models.CharField(max_length=200, blank=True, null=True)
    region_abbreviation = models.CharField(max_length=40, blank=True, null=True)
    country = models.CharField(max_length=200, blank=True)
    continent = models.CharField(max_length=200, blank=True)
    country_code = models.CharField(max_length=200, blank=True, null=True)
    google_place_id = models.CharField(max_length=200, blank=True, null=True)

    groups = models.ManyToManyField('LocationGroup', related_name='locations', blank=True)

    def __str__(self):
        return self.formatted_address
