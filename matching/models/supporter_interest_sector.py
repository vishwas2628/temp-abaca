from django.db import models


class SupporterInterestSector(models.Model):
    supporter = models.ForeignKey(
        'matching.Supporter', on_delete=models.CASCADE, related_name='sectors_of_interest')
    sector = models.ForeignKey('viral.Sector', on_delete=models.CASCADE)
    group = models.ForeignKey(
        'viral.Group', on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return '%s > %s' % (self.group.name.capitalize(), self.sector.name.capitalize()) if self.group else self.sector.name.capitalize()

    class Meta:
        db_table = 'matching_supporter_sectors'
        unique_together = (('supporter', 'sector'),)
        verbose_name_plural = 'Sectors Of Interest'
