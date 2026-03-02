from django.db import models

from shared.models import TimestampedModel
from itertools import count


class Network(TimestampedModel):
    name = models.CharField(max_length=128)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    logo = models.URLField(blank=True)
    slug = models.SlugField(max_length=80, null=True, unique=True)

    locations = models.ManyToManyField('viral.Location', blank=True)

    def __str__(self):
        return self.name
