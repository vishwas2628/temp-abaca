from django.db import models
from markdownx.models import MarkdownxField
from shared.models import TimestampedModel
from tinymce import HTMLField


class CategoryLevel(TimestampedModel):
    achievements = models.CharField(max_length=160)
    description = models.CharField(max_length=160)
    requirements = MarkdownxField(max_length=400)
    next_milestones_title = HTMLField()
    next_milestones_description = HTMLField()
    achieved_milestones_title = HTMLField()
    achieved_milestones_description = HTMLField()
    category = models.ForeignKey(
        'Category',
        on_delete=models.CASCADE,
    )
    level = models.ForeignKey(
        'Level',
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("category", "level")

    def __str__(self):
        return self.category.name + ' - ' + str(self.level.value)
