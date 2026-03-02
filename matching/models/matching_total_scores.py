from django.db import models


class MatchingTotalScores(models.Model):
    company_id = models.IntegerField(primary_key=True)
    supporter_id = models.IntegerField()
    max_score_percentil = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'matching\".\"total_score'
