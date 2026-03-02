from django.db import models
from shared.models import TimestampedModel
from adminsortable.models import SortableMixin
from .category_group import CategoryGroup


class Category(SortableMixin, TimestampedModel):
    VALUE_TYPES = (
        ('SINGLE', 'Single'),
        ('RANGE', 'Range'),
    )

    name = models.CharField(max_length=60)
    description = models.TextField(blank=True)
    requirements_title = models.TextField()
    color = models.CharField(max_length=6)
    abbreviation = models.CharField(max_length=20, unique=True)
    order = models.PositiveIntegerField(
        default=0, editable=False, db_index=True)
    group = models.ForeignKey(
        CategoryGroup, on_delete=models.CASCADE, null=True)
    value_type = models.CharField(
        max_length=6, choices=VALUE_TYPES, default='SINGLE')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['order']
        verbose_name_plural = 'Categories'
