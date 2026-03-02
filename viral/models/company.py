import os
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from viral.validators import NoSchemeURLValidator
from shared.models import SanitizedModel, TimestampedModel, UniqueUID
from uuid import uuid4
from os.path import splitext
from grid.models import Assessment


def validate_file_extension(value):
    ext = splitext(value.name)[1]
    valid_extensions = ['.png', '.jpg', '.jpeg']
    if not ext.lower() in valid_extensions:
        raise ValidationError("Unsuported file extension",
                              code="unsuported_file_extension")


def uuid_upload(instance, filename):
    ext = filename.split('.')[-1]
    return 'company_logos/{}.{}'.format(uuid4(), ext)


def uuid_cover_upload(instance, filename):
    ext = filename.split('.')[-1]
    return 'company_covers/{}.{}'.format(uuid4(), ext)


def unique_company_access_hash():
    """
    Generate unique company access hash
    """
    unique_access_hash = os.urandom(5).hex()
    existing_hashes = Company.objects.values_list('access_hash', flat=True)

    while unique_access_hash in existing_hashes:
        unique_access_hash = os.urandom(5).hex()

    return unique_access_hash


class Company(SanitizedModel, TimestampedModel, UniqueUID):
    ENTREPRENEUR = 0
    SUPPORTER = 1
    PARTNER = 2
    USER_TYPE = (
        (ENTREPRENEUR, "Entrepreneur"),
        (SUPPORTER, "Supporter"),
        (PARTNER, "Partner"),
    )
    type = models.SmallIntegerField(choices=USER_TYPE)
    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=150, unique=True,
                            null=True, default=None)
    logo = models.FileField(null=True, upload_to=uuid_upload, validators=[
                            validate_file_extension])
    cover = models.FileField(null=True, upload_to=uuid_cover_upload, validators=[
        validate_file_extension])
    about = models.TextField(null=True)
    website = models.CharField(max_length=200, null=True, validators=[
                               NoSchemeURLValidator()])
    email = models.EmailField(null=True)
    founded_date = models.DateField(null=True)
    sectors = models.ManyToManyField('Sector', blank=True)
    locations = models.ManyToManyField('Location')
    crunchbase_id = models.CharField(null=True, max_length=500)
    access_hash = models.CharField(
        max_length=10, null=True, unique=True, default=unique_company_access_hash)

    networks = models.ManyToManyField('Network', blank=True)

    def set_slug_from_name(self):
        self.slug = slugify(self.name.lower())

        # Grab the amount of existing slugs that match the current one.
        existing_slugs = Company.objects.exclude(id=self.id).filter(
            Q(slug=self.slug) | Q(slug__regex=r'{0}-\d+$'.format(self.slug))).values_list('slug', flat=True)

        # Append unique number if it's a duplicated slug
        if len(existing_slugs) and self.slug in existing_slugs:
            unique_slug = self.slug
            count = 1
            while unique_slug in existing_slugs:
                unique_slug = '%s-%d' % (self.slug, count)
                count += 1
            self.slug = unique_slug

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        # Build slug from name
        self.set_slug_from_name()

        # Ensure existance of access hash (mostly for existing companies without it)
        if not bool(self.access_hash):
            self.access_hash = unique_company_access_hash()

        super().save(*args, **kwargs)

    def latest_assessment(self):
        """
        Get the latest assessment for the company.
        """
        try:
            return Assessment.objects.filter(
                evaluated=self.id).order_by('-created_at')[0:1].get()
        except Assessment.DoesNotExist:
            return None

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "companies"
        permissions = [
            ("edit_any_company", "Can edit any company"),
        ]
