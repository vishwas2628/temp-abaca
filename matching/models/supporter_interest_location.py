from django.db import models


class SupporterInterestLocation(models.Model):
    supporter = models.ForeignKey(
        'matching.Supporter', on_delete=models.CASCADE, related_name='locations_of_interest')
    location = models.ForeignKey('viral.Location', on_delete=models.CASCADE)
    group = models.ForeignKey(
        'viral.LocationGroup', on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return '%s > %s' % (self.group.name.capitalize(), self.location.formatted_address.capitalize()) if self.group else self.location.formatted_address.capitalize()

    class Meta:
        db_table = 'matching_supporter_locations'
        unique_together = (('supporter', 'location'),)
        verbose_name_plural = 'Locations Of Interest'
