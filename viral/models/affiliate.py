from django.db import models
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.template.defaultfilters import default
from django_better_admin_arrayfield.models.fields import ArrayField
from django.utils.text import slugify
from django.db.models import Q
from tinymce import HTMLField

from viral.models import Company
from shared.models import TimestampedModel
from sortedm2m.fields import SortedManyToManyField


class Affiliate(TimestampedModel):
    SELF_ASSESSMENT = 0
    PROGRAM = 1
    SDG = 2

    AFFILIATE_FLOWS = (
        (SELF_ASSESSMENT, 'Self-Assessment flow'),
        (PROGRAM, 'Program (Question Bundles) flow'),
        (SDG, 'SDG (Sustainable Development Guide) flow'),
    )

    AFFILIATE_TARGETS = (
        (Company.ENTREPRENEUR, 'Entrepreneur'),
        (Company.SUPPORTER, 'Supporter'),
    )

    name = models.CharField(max_length=128)
    shortcode = models.CharField(max_length=50)
    slug = models.CharField(max_length=50, unique=True, null=True, default=None)
    email = models.EmailField()
    additional_emails = ArrayField(models.EmailField(), blank=True, null=True)
    website = models.URLField()
    logo = models.URLField()
    spreadsheet = models.URLField(blank=True)
    sdg_reports_enabled = models.BooleanField(
        default=False,  # type: ignore
        verbose_name="SDG Reports",
    )
    company = models.ForeignKey(
        'Company',
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
    )
    flow_type = models.IntegerField(
        choices=AFFILIATE_FLOWS,
        default=SELF_ASSESSMENT,
    )
    flow_target = models.IntegerField(
        choices=AFFILIATE_TARGETS,
        default=Company.ENTREPRENEUR,
    )

    # Used for providing a fallback Affiliate without needing to reference a primary key
    default_flow = models.BooleanField(default=False)

    supporters = models.ManyToManyField('matching.Supporter', blank=True)
    networks = models.ManyToManyField('Network', blank=True)
    question_bundles = SortedManyToManyField('matching.QuestionBundle', blank=True)
    show_team_section = models.BooleanField(default=False, help_text='Include the Team Section in this Affiliate flow')
    webhooks = models.ManyToManyField('viral.AffiliateWebhook', blank=True)

    # Defines which company lists will be populated by the companies that submit this Affiliate.
    company_lists = models.ManyToManyField(
        'company_lists.CompanyList',
        related_name='+',
        blank=True,
    )

    # Fills to display in the affiliate starting page
    summary = HTMLField(default='', help_text='Try to limit this field to 500 characters.', blank=True)
    disclaimer_heading = models.CharField(
        max_length=45, default='', help_text='This field will accept a maximum of 45 characters.', blank=True
    )
    disclaimer_body = HTMLField(default='', help_text='Try to limit this field to 160 characters.', blank=True)
    self_assessment_step_description = HTMLField(
        default='',
        verbose_name='Description',
        help_text='Try to limit this field to 100 characters. Keep in mind that there may be additional steps (questions and team members).',
        blank=True,
    )
    self_assessment_step_note = HTMLField(
        default='',
        verbose_name='Note',
        help_text='Try to limit this field to 50 characters. This note is not commonly used.',
        blank=True,
    )
    questions_step_description = HTMLField(
        default='',
        verbose_name='Description',
        help_text='Try to limit this field to 100 characters. Keep in mind that there may be additional steps (self-assessment and team members).',
        blank=True,
    )
    questions_step_note = HTMLField(
        default='',
        verbose_name='Note',
        help_text='Try to limit this field to 50 characters. This note is not commonly used.',
        blank=True,
    )
    team_members_step_description = HTMLField(
        default='',
        verbose_name='Description',
        help_text='Try to limit this field to 100 characters. Keep in mind that there may be additional steps (self-assessment and questions).',
        blank=True,
    )
    team_members_step_note = HTMLField(
        default='',
        verbose_name='Note',
        help_text='Try to limit this field to 50 characters. This note is not commonly used.',
        blank=True,
    )

    def set_slug_from_shortcode(self):
        self.slug = slugify(self.shortcode.lower())

        # Grab the amount of existing slugs that match the current one.
        existing_slugs = (
            Affiliate.objects.exclude(id=self.id)
            .filter(Q(slug=self.slug) | Q(slug__regex=r'{0}-\d+$'.format(self.slug)))
            .values_list('slug', flat=True)
        )

        # Append unique number if it's a duplicated slug
        if len(existing_slugs) and self.slug in existing_slugs:
            unique_slug = self.slug
            count = 1
            while unique_slug in existing_slugs:
                unique_slug = '%s-%d' % (self.slug, count)
                count += 1
            self.slug = unique_slug

    def validate_unique(self, *args, **kwargs):
        super().validate_unique(*args, **kwargs)

        # Validate if there's only a 'default flow' per 'flow type' and 'flow target'
        if self.default_flow:
            qs = self.__class__._default_manager.filter(
                flow_type=self.flow_type, flow_target=self.flow_target, default_flow=self.default_flow
            ).exclude(updated_at=self.updated_at)

            if qs.exists():
                raise ValidationError(
                    {
                        NON_FIELD_ERRORS: [
                            'There can only exist a single default flow',
                        ],
                    }
                )

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        # Build slug from shortcode
        self.set_slug_from_shortcode()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
