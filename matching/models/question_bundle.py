from django.db import models
from shared.models import TimestampedModel
from sortedm2m.fields import SortedManyToManyField


class QuestionBundle(TimestampedModel):
    name = models.CharField(max_length=128)
    supporter = models.ForeignKey('Supporter', on_delete=models.CASCADE)
    has_team_member_questions = models.BooleanField(
        default=False, help_text='Set question bundle as targeted for Team Members')
    capital_explorer = models.BooleanField(
        default=False, help_text='Include this question bundle in the Capital Explorer')
    questions = SortedManyToManyField('Question')

    # Used for listing questions for a Category:
    category = models.ForeignKey('grid.Category', null=True,
                                 blank=True, on_delete=models.SET_NULL)

    # Used for listing questions for a CategoryLevel:
    category_level = models.ForeignKey('grid.CategoryLevel', null=True,
                                       blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.supporter.name + ' - ' + self.name
