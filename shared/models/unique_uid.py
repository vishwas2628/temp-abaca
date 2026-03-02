from django.db import models
from django.apps import apps

import string
import random


def random_uid(length=8):
    """
    Generate random alphanumeric string with custom length
    """
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(random.choices(alphabet, k=length))


def model_populate_uids(UIDModel):
    """
    Go through all existing instances of a model and
    populate the 'uid' field with a random uid 
    """
    instances = UIDModel.objects.all()

    for obj in instances:
        new_uid = random_uid()
        while UIDModel.objects.filter(uid=new_uid).exists():
            new_uid = random_uid()
        obj.uid = new_uid
        obj.save()


class UniqueUID(models.Model):
    """
    Abstract model to have unique and short identifiers
    Similar value like UUIDs hence the name UID

    NOTE: 
    When adding this class to existing models with database entries,
    after running the migration that adds the 'uid' field add a 
    data migration to populate those 'uuid's using the 
    'model_populate_uids' helper function

    Example: 0062_auto_20200326_0655.py
    """
    uid = models.CharField(unique=True, max_length=40, null=True)

    def save(self, *args, **kwargs):
        if not self.uid:
            new_uid = random_uid()
            while type(self).objects.filter(uid=new_uid).exists():
                new_uid = random_uid()
            self.uid = new_uid
        super().save(*args, **kwargs)

    class Meta:
        abstract = True
