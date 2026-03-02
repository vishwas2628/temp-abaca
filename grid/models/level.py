from django.db import models
from shared.models import TimestampedModel
from markdownx.models import MarkdownxField
from .level_group import LevelGroup


class Level(TimestampedModel):
    value = models.IntegerField()
    title = models.CharField(max_length=80)
    description = MarkdownxField()
    typical_funding = MarkdownxField(blank=True)
    group = models.ForeignKey(
        LevelGroup, on_delete=models.CASCADE, null=True)

    def __str__(self):
        level_str = 'Level {value}'.format(value=str(self.value))
        if self.group:
            return '{str} - {group}'.format(str=level_str, group=self.group.slug.capitalize())
        return level_str
