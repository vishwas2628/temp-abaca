import json
import os

from datetime import datetime
from django import forms
from django.db.models import Q, Count, Case, When, IntegerField
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.urls import reverse
from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin
from easy_select2 import Select2, Select2Multiple
from modeltranslation.admin import TabbedTranslationAdmin
from modeltranslation import settings as mt_settings
from django.utils.safestring import mark_safe

from grid.models import Category
from django.contrib.admin import DateFieldListFilter
from viral.data.geo_countries_continents import GEO_COUNTRIES_CONTINENTS
from viral.models import (
    Affiliate,
    AffiliateProgramEntry,
    AffiliateProgramSupporterSubmission,
    AffiliateWebhook,
    Company,
    Group,
    Location,
    LocationGroup,
    Network,
    Subscription,
    TeamMember,
    UserProfile,
    UserGuest,
    Vendor,
)
from sdg.models import SdgReport
from viral.utils import get_usable_admin_token
from matching.models import Response, QuestionBundle
from sortedm2m.forms import SortedMultipleChoiceField


class AffiliateForm(forms.ModelForm):
    question_bundles = SortedMultipleChoiceField(
        required=False,
        queryset=QuestionBundle.objects.filter(has_team_member_questions=False),
    )
    team_question_bundles = SortedMultipleChoiceField(
        required=False,
        queryset=QuestionBundle.objects.filter(has_team_member_questions=True),
    )

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super(AffiliateForm, self).__init__(*args, **kwargs)
        self.fields[
            'sdg_reports_enabled'
        ].help_text = 'Add start page at /entreprenuers/sdgs'
        if instance:
            self.fields[
                'team_question_bundles'
            ].initial = instance.question_bundles.filter(
                has_team_member_questions=True,
            )

    class Meta:
        model = Affiliate
        fields = '__all__'
        widgets = {
            'networks': Select2Multiple,
            'supporters': Select2Multiple,
            'webhooks': Select2Multiple,
            'company_lists': Select2Multiple,
            'company': Select2,
        }

    def validate_program_relations(self):
        # Check if there's at least one Supporter or Network selected.
        supporters = self.cleaned_data.get('supporters')
        networks = self.cleaned_data.get('networks')

        if not supporters.exists() and not networks.exists():
            raise ValidationError('Select at least one Supporter or Network')

    def validate_program_questions(self):
        # Check if selected any questions.
        question_bundles = self.cleaned_data.get('question_bundles')

        if not len(question_bundles):
            raise ValidationError('Select a Question Bundle')

    def validate_lists_ownership(self):
        # Check if selected lists are owner by the company selected on the Affiliate.
        company = self.cleaned_data.get('company')
        company_lists = self.cleaned_data.get('company_lists')

        if not bool(company) and not bool(company_lists):
            return

        if company_lists.exclude(owner__company__pk=company.pk).exists():
            raise ValidationError(
                'Select only company lists owned by the current selected company: %s'
                % company.name
            )

    def clean(self):
        if self.cleaned_data['show_team_section']:
            self.cleaned_data['question_bundles'] = self.cleaned_data.get(
                'question_bundles'
            ) + self.cleaned_data.get('team_question_bundles')

        flow_type = self.cleaned_data.get('flow_type')

        if flow_type == Affiliate.PROGRAM:
            self.validate_program_relations()
            self.validate_program_questions()

        self.validate_lists_ownership()

        super(AffiliateForm, self).clean()


class AffiliateAdmin(TabbedTranslationAdmin):
    class Media:
        js = TabbedTranslationAdmin.Media.js + DynamicArrayMixin.Media.js
        css = {
            'all': TabbedTranslationAdmin.Media.css['all']
            + DynamicArrayMixin.Media.css['all']
        }

    readonly_fields = (
        'id',
        'slug',
    )
    autocomplete_fields = ['company']
    form = AffiliateForm
    search_fields = ('name', 'shortcode')
    filter_horizontal = ()
    list_filter = ()
    fieldsets = (
        (
            'Affiliate configuration',
            {
                'classes': ['configuration'],
                'fields': (
                    'name',
                    'shortcode',
                    'email',
                    'additional_emails',
                    'website',
                    'logo',
                    'spreadsheet',
                    'company',
                    'flow_type',
                    'flow_target',
                    'default_flow',
                    'supporters',
                    'networks',
                    'question_bundles',
                    'show_team_section',
                    'team_question_bundles',
                    'webhooks',
                    'company_lists',
                    'id',
                    'slug',
                    'sdg_reports_enabled',
                ),
            },
        ),
        (
            'Left panel',
            {
                'classes': ['collapse', 'left-panel'],
                'fields': (
                    'summary',
                    'disclaimer_heading',
                    'disclaimer_body',
                ),
            },
        ),
        (
            'Self-assessment step',
            {
                'classes': ['collapse', 'self-assessment-step'],
                'fields': (
                    'self_assessment_step_description',
                    'self_assessment_step_note',
                ),
            },
        ),
        (
            'Questions step',
            {
                'classes': ['collapse', 'questions-step'],
                'fields': (
                    'questions_step_description',
                    'questions_step_note',
                ),
            },
        ),
        (
            'Team members step',
            {
                'classes': ['collapse', 'team-members-step'],
                'fields': ('team_members_step_description', 'team_members_step_note'),
            },
        ),
    )

    list_display = ('name', 'get_supporters', 'get_submission_count')
    change_form_template = 'admin/affiliate-form.html'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Add SDG report job status context so the template can conditionally
        show an 'Update report status' action when jobs are in progress.
        """
        extra_context = extra_context or {}
        report_request = SdgReport.objects.filter(affiliate=object_id).first()
        if report_request:
            extra_context['has_sdg_report_request'] = True
            extra_context['sdg_report_job_id'] = report_request.job_id
            extra_context['sdg_report_request_status'] = report_request.job_status
            extra_context['sdg_report_pdf_url'] = report_request.report_pdf_url
            extra_context['sdg_report_xlsx_url'] = report_request.report_xlsx_url
        else:
            extra_context['has_sdg_report_request'] = False

        return super().change_view(
            request,
            object_id,
            form_url,
            extra_context=extra_context,
        )

    def get_queryset(self, request):
        qs = super().get_queryset(request).prefetch_related('supporters')
        qs = qs.annotate(
            entry_count=Count('affiliateprogramentry'),
            supporter_submission_count=Count('affiliateprogramsupportersubmission'),
        )
        return qs

    def get_submission_count(self, obj):
        if obj.flow_target == Company.ENTREPRENEUR:
            return getattr(obj, 'entry_count', 0)
        elif obj.flow_target == Company.SUPPORTER:
            return getattr(obj, 'supporter_submission_count', 0)
        else:
            return 0

    get_submission_count.short_description = 'Submission Count'

    def get_supporters(self, obj):
        return ', '.join([supporter.name for supporter in obj.supporters.all()])

    get_supporters.short_description = 'Supporters'


class InputFilter(admin.SimpleListFilter):
    """
    Base class for defining simple filters for admin list views
    """

    template = 'admin/input-filter.html'

    def lookups(self, request, model_admin):
        return ((),)

    def choices(self, changelist):
        all_choice = next(super().choices(changelist))
        all_choice['query_parts'] = (
            (k, v)
            for k, v in changelist.get_filters_params().items()
            if k != self.parameter_name
        )
        yield all_choice


class SectorFilter(InputFilter):
    """
    Filter by sector in list view for Company admin
    """

    parameter_name = 'sectors'
    title = 'Sector'

    def queryset(self, request, queryset):
        term = self.value()

        if term is None:
            return

        return queryset.filter(
            Q(sectors__name__icontains=term) | Q(sectors__groups__name__icontains=term)
        )


class CompanyAdmin(admin.ModelAdmin):
    """
    Add Login as Button to each Company
    -> This generates an admin token associated to a single company
    -> Tokens are valid for 1 hour
    """

    change_form_template = 'admin/admin-as-user.html'

    list_display = [
        'name',
        'type',
        'get_sectors',
        'get_viral_score',
        'get_cities',
        'get_regions',
        'get_countries',
        'get_continents',
        'get_user_login',
        'get_user_joined',
    ]
    list_filter = ['type', SectorFilter]
    search_fields = ['name']
    readonly_fields = ('slug', 'uid')
    exclude = ('access_hash',)
    autocomplete_fields = ('sectors', 'locations', 'networks')

    # Custom variable to limit fields with too much data (sectors, locations)
    formatted_display_limit = 10

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related('locations', 'sectors', 'networks', 'company_profile')
        )

    def _get_formatted_locations_field(self, all_locations, field):
        return ', '.join(
            [
                getattr(location, field)
                for location in all_locations
                if hasattr(location, field) and getattr(location, field) is not None
            ]
        )

    def get_user_login(self, obj):
        return obj.company_profile.user.last_login

    get_user_login.short_description = 'Last Login Date'
    get_user_login.admin_order_field = 'company_profile__user__last_login'

    def get_user_joined(self, obj):
        return obj.company_profile.user.date_joined

    get_user_joined.short_description = 'Date Joined'
    get_user_joined.admin_order_field = 'company_profile__user__date_joined'

    def get_viral_score(self, obj):
        return obj.latest_assessment().level.value if obj.latest_assessment() else None

    get_viral_score.short_description = 'Viral Score'

    def get_sectors(self, obj):
        sectors = [sector.name.capitalize() for sector in obj.sectors.all()]
        # Grab sectors with limit and join them by commas
        formatted_sectors = ', '.join(sectors[: self.formatted_display_limit])
        formatted_sectors += (
            '...' if len(sectors) > self.formatted_display_limit else ''
        )
        return formatted_sectors

    get_sectors.short_description = 'Sector'

    def get_cities(self, obj):
        return self._get_formatted_locations_field(obj.locations.all(), 'city')

    get_cities.short_description = 'City'

    def get_regions(self, obj):
        return self._get_formatted_locations_field(obj.locations.all(), 'region')

    get_regions.short_description = 'Region'

    def get_countries(self, obj):
        return self._get_formatted_locations_field(obj.locations.all(), 'country')

    get_countries.short_description = 'Country'

    def get_continents(self, obj):
        return self._get_formatted_locations_field(obj.locations.all(), 'continent')

    get_continents.short_description = 'Continent'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        try:
            user_profile = UserProfile.objects.get(company=object_id.split('/')[0])
        except Exception as e:
            raise e

        company = Company.objects.get(pk=object_id.split('/')[0])
        user_id = user_profile.user.id
        extra_context = extra_context or {}
        extra_context['target_url'] = (
            os.getenv('API_DOMAIN', 'localhost') + '/admin/auth/validate'
        )
        extra_context['redirect_url'] = os.getenv('APP_DOMAIN', 'localhost')
        extra_context['user_id'] = user_id
        extra_context['company_id'] = object_id.split('/')[0]
        extra_context['access_hash'] = company.access_hash

        admin_token = get_usable_admin_token(user_profile.user)

        extra_context['token'] = admin_token.key

        return super().change_view(
            request,
            object_id,
            form_url,
            extra_context=extra_context,
        )

    def get_deleted_objects(self, objs, request):
        """
        Override default behavior to include User related objects
        """
        (deleted_objects, model_count, perms_needed, protected) = (
            super().get_deleted_objects(objs, request)
        )

        for obj_index, obj in enumerate(objs):
            try:
                user = obj.company_profile.user
            except ObjectDoesNotExist:
                break
            user_queryset = get_user_model().objects.filter(pk=user.pk)
            user_deleted_objects = super().get_deleted_objects(user_queryset, request)

            # Due to the deleted_objects nesting format, we need this formula to get the correct index
            related_deleted_objects = deleted_objects[obj_index * 2 + 1]

            # Filter out User Profile (and its sub-records), since it is already related to the Company
            user_profile_index = None
            for i, v in enumerate(user_deleted_objects[0][1]):
                if isinstance(v, str) and v.startswith('User profile'):
                    user_profile_index = i
            if type(user_profile_index) == int:
                try:
                    del user_deleted_objects[0][1][user_profile_index + 1]
                    del user_deleted_objects[0][1][user_profile_index]
                except IndexError:
                    pass

            # Add User related objects to the deleted_objects list
            related_deleted_objects.extend(user_deleted_objects[0])

            # Add User related model count to the model_count list
            for model, count in user_deleted_objects[1].items():
                if not model == 'user profiles':
                    model_count[model] = model_count.get(model, 0) + count

        return (deleted_objects, model_count, perms_needed, protected)

    def delete_model(self, request, obj):
        """
        Override default behavior to also delete the User model related to the Company
        """
        try:
            user = obj.company_profile.user
        except ObjectDoesNotExist:
            user = None

        obj.delete()

        if user:
            user.delete()

    def delete_queryset(self, request, queryset):
        """
        Override default behavior to also delete the User models related to each Company
        """
        user_ids = []

        for company in queryset.all():
            try:
                user_ids.append(company.company_profile.user.id)
            except ObjectDoesNotExist:
                pass

        queryset.delete()
        get_user_model().objects.filter(id__in=user_ids).delete()


class PasswordInput(forms.PasswordInput):
    def format_value(self, value):
        """
        Return uncrypted password value
        """
        if value == '' or value is None:
            return None

        return str(signing.loads(value))


class NumberInput(forms.NumberInput):
    def format_value(self, value):
        """
        Generate time-based value
        """
        if value:
            return value

        return round(datetime.now().timestamp())


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        widgets = {
            'auth_password': PasswordInput(render_value=True),
            'uuid': NumberInput(),
        }
        fields = '__all__'


class VendorAdmin(admin.ModelAdmin, DynamicArrayMixin):
    form = VendorForm

    def get_fieldsets(self, request, obj=None):
        fieldset = super(VendorAdmin, self).get_fieldsets(request, obj)
        # Move ID field to top
        for index, field in enumerate(fieldset[0][1]['fields']):
            if field == 'uuid':
                id_field = fieldset[0][1]['fields'].pop(index)
                fieldset[0][1]['fields'].insert(0, id_field)

        return fieldset


class UserProfileAdmin(admin.ModelAdmin):
    list_filter = (('created_at', DateFieldListFilter),)
    list_display = ('__str__', 'uid', 'pk', 'created_at')
    search_fields = ('pk', 'uid', 'user__email', 'company__name')
    readonly_fields = ('uid', 'is_offline')
    autocomplete_fields = ('user', 'company', 'source')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'company')


class AffiliateProgramEntryAdmin(admin.ModelAdmin):
    list_display = ['affiliate', 'get_company', 'get_supporters']
    readonly_fields = ('get_questionary', 'get_assessment', 'get_team_members')
    exclude = ('responses', 'assessment', 'team_members')
    autocomplete_fields = ('affiliate', 'user_profile')

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related('user_profile__company')
            .prefetch_related(
                'affiliate__supporters',
                'responses__question',
                'responses__answers',
                'assessment',
            )
        )

    def get_object(self, request, object_id, from_field=None):
        """
        Override get_object to ensure prefetch_related from get_queryset is used.
        Standard get_object uses .get() which does not support prefetch_related.
        """
        queryset = self.get_queryset(request)
        model = queryset.model
        field = (
            model._meta.pk if from_field is None else model._meta.get_field(from_field)
        )
        try:
            object_id = field.to_python(object_id)
            return queryset.filter(**{field.name: object_id}).first()
        except (model.DoesNotExist, ValidationError, ValueError):
            return None

    def get_questionary(self, obj):
        questionary = ''

        for response in obj.responses.all():
            questionary += '<b>{}</b>'.format(str(response.question))
            questionary += '<br>'

            if response.value:
                single_values = ['text', 'value', 'date']
                questionary += next(
                    (
                        str(response.value[key])
                        for key in single_values
                        if key in response.value
                    )
                ) or str(response.value.get('min', '')) + str(
                    response.value.get('max', '')
                )
            else:
                questionary += ', '.join(
                    [answer.value for answer in response.answers.all()]
                )
            questionary += '<br><br><br>'

        return mark_safe(questionary)

    get_questionary.short_description = 'Questionary'

    def get_assessment(self, obj):
        viral_assessment = '<b>{}</b>'.format(obj.assessment.level)
        viral_assessment += '<br><br>'

        # Optimize: Fetch all categories at once
        category_ids = [
            a.get('category') for a in obj.assessment.data or [] if a.get('category')
        ]
        categories = {
            c.pk: c.name
            for c in Category.objects.filter(pk__in=category_ids).only('id', 'name')
        }

        for assessment in obj.assessment.data:
            category_id = assessment.get('category')
            category_name = categories.get(category_id, 'Unknown')
            level = str(assessment.get('level') or 0)
            viral_assessment += '<p>{} - {}</p>'.format(level, category_name)

        return mark_safe(viral_assessment)

    get_assessment.short_description = 'Assessment'

    def get_company(self, obj):
        return obj.user_profile.company

    get_company.short_description = 'Company'

    def get_supporters(self, obj):
        return ', '.join(
            [supporter.name for supporter in obj.affiliate.supporters.all()]
        )

    get_supporters.short_description = 'Supporters'

    def get_team_members(self, obj):
        html = ''
        team_members = obj.team_members or []

        # Optimize: Fetch all responses at once
        all_response_ids = []
        for team_member in team_members:
            all_response_ids.extend(team_member.get('responses', []))

        responses = (
            Response.objects.filter(pk__in=all_response_ids)
            .select_related('question')
            .prefetch_related('answers')
        )
        response_map = {r.pk: r for r in responses}

        for team_member in team_members:
            html += '<ul style="margin-left: 0; padding-left: 0;">'
            html += f'<li><b>Name:</b> {team_member["first_name"]} {team_member["last_name"]}</li>'
            html += f'<li><b>Position:</b> {team_member["position"]}</li>'
            html += f'<li><b>Email:</b> {team_member["email"]}</li>'
            for id in team_member.get('responses', []):
                response = response_map.get(id)
                if response:
                    if response.value:
                        single_values = ['text', 'value', 'date']
                        response_str = next(
                            (
                                str(response.value[key])
                                for key in single_values
                                if key in response.value
                            )
                        ) or str(response.value.get('min', '')) + str(
                            response.value.get('max', '')
                        )
                    else:
                        response_str = ', '.join(
                            [answer.value for answer in response.answers.all()]
                        )
                    html += f'<li><b>{str(response.question)}</b>: {response_str}</li>'
            html += '</ul>'
        return mark_safe(html)

    get_team_members.short_description = 'Team Members'


class AffiliateProgramSupporterSubmissionAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'affiliate', 'supporter', 'get_networks']
    readonly_fields = (
        'uid',
        'get_investing_range',
        'get_questionary',
        'get_interests',
        'get_team_members',
    )
    exclude = (
        'investing_level_range',
        'criteria',
        'additional_criteria',
        'sectors_of_interest',
        'locations_of_interest',
        'team_members',
    )
    autocomplete_fields = ('affiliate', 'supporter')
    search_fields = (
        'affiliate__name',
        'affiliate__slug',
        'affiliate__shortcode',
        'supporter__name',
        'supporter__email',
        'uid',
        'created_at',
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related('affiliate', 'supporter')
            .prefetch_related(
                'affiliate__networks',
                'criteria__question',
                'criteria__answers',
                'additional_criteria__question',
                'additional_criteria__answers',
            )
        )

    def get_object(self, request, object_id, from_field=None):
        """
        Override get_object to ensure prefetch_related from get_queryset is used.
        Standard get_object uses .get() which does not support prefetch_related.
        """
        queryset = self.get_queryset(request)
        model = queryset.model
        field = (
            model._meta.pk if from_field is None else model._meta.get_field(from_field)
        )
        try:
            object_id = field.to_python(object_id)
            return queryset.filter(**{field.name: object_id}).first()
        except (model.DoesNotExist, ValidationError, ValueError):
            return None

    def get_investing_range(self, obj):
        level_range = str(obj.investing_level_range.lower)
        level_range += (
            ' - {}'.format(obj.investing_level_range.upper)
            if obj.investing_level_range.upper
            else ''
        )
        return level_range

    get_investing_range.short_description = 'Investing Level Range'

    def get_questionary(self, obj):
        questionary = ''

        for criteria in obj.criteria.all():
            questionary += '<b>{}</b>'.format(str(criteria.question))
            questionary += '<br>'

            if criteria.desired:
                single_values = ['text', 'value', 'date']
                questionary += next(
                    (
                        str(criteria.desired[key])
                        for key in single_values
                        if key in criteria.desired
                    ),
                    None,
                ) or str(criteria.desired.get('min', '')) + str(
                    criteria.desired.get('max', '')
                )
            else:
                questionary += ', '.join(
                    [answer.value for answer in criteria.answers.all()]
                )
            questionary += '<br><br><br>'

        return mark_safe(questionary)

    get_questionary.short_description = 'Questionary'

    def get_interests(self, obj):
        interests = ''

        for criteria in obj.additional_criteria.all():
            question = (
                criteria.question.short_name or criteria.question.resource_question
            )
            question_category = str(criteria.question.question_category)
            interests += '<b>{category} > {question}</b>'.format(
                category=question_category, question=question
            )
            interests += '<br>'

            if criteria.desired:
                single_values = ['text', 'value', 'date']
                interests += next(
                    (
                        str(criteria.desired[key])
                        for key in single_values
                        if key in criteria.desired
                    ),
                    None,
                ) or str(criteria.desired.get('min', '')) + str(
                    criteria.desired.get('max', '')
                )
            else:
                interests += ', '.join(
                    [answer.value for answer in criteria.answers.all()]
                )
            interests += '<br><br><br>'

        return mark_safe(interests)

    get_interests.short_description = 'Interests'

    def get_networks(self, obj):
        return ', '.join([network.name for network in obj.affiliate.networks.all()])

    get_networks.short_description = 'Networks'

    def get_team_members(self, obj):
        html = ''
        team_members = obj.team_members or []

        # Optimize: Fetch all responses at once
        all_response_ids = []
        for team_member in team_members:
            all_response_ids.extend(team_member.get('responses', []))

        responses = (
            Response.objects.filter(pk__in=all_response_ids)
            .select_related('question')
            .prefetch_related('answers')
        )
        response_map = {r.pk: r for r in responses}

        for team_member in team_members:
            html += '<ul style="margin-left: 0; padding-left: 0;">'
            html += f'<li><b>Name:</b> {team_member["first_name"]} {team_member["last_name"]}</li>'
            html += f'<li><b>Position:</b> {team_member["position"]}</li>'
            html += f'<li><b>Email:</b> {team_member["email"]}</li>'
            for id in team_member.get('responses', []):
                response = response_map.get(id)
                if response:
                    if response.value:
                        single_values = ['text', 'value', 'date']
                        response_str = next(
                            (
                                str(response.value[key])
                                for key in single_values
                                if key in response.value
                            )
                        ) or str(response.value.get('min', '')) + str(
                            response.value.get('max', '')
                        )
                    else:
                        response_str = ', '.join(
                            [answer.value for answer in response.answers.all()]
                        )
                    html += f'<li><b>{str(response.question)}</b>: {response_str}</li>'
            html += '</ul>'
        return mark_safe(html)

    get_team_members.short_description = 'Team Members'


class GooglePlacesInput(forms.TextInput):
    is_required = False
    template_name = 'admin/google-places-search.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['key'] = os.getenv('GOOGLE_PLACES_KEY', None)
        context['continents'] = mark_safe(json.dumps(GEO_COUNTRIES_CONTINENTS))
        return context


class LocationForm(forms.ModelForm):
    google_search = forms.CharField(widget=GooglePlacesInput, required=False)

    class Meta:
        model = Location
        fields = '__all__'


class LocationAdmin(admin.ModelAdmin):
    form = LocationForm
    exclude = ('groups',)
    search_fields = [
        'formatted_address',
        'city',
        'region',
        'country',
        'continent',
        'country_code',
    ]
    list_display = ['__str__', 'continent', 'country_code', 'country', 'region', 'city']
    list_filter = ['continent', 'country_code', 'country']

    def get_fieldsets(self, request, obj=None):
        fieldset = super(LocationAdmin, self).get_fieldsets(request, obj)
        # Move Google Search field to top
        for index, field in enumerate(fieldset[0][1]['fields']):
            if field == 'google_search':
                id_field = fieldset[0][1]['fields'].pop(index)
                fieldset[0][1]['fields'].insert(0, id_field)

        return fieldset


class LocationInline(admin.StackedInline):
    autocomplete_fields = ('location',)
    verbose_name = 'Location to Group'
    verbose_name_plural = 'Locations in Group'
    model = Location.groups.through


class GroupAdmin(TabbedTranslationAdmin):
    search_fields = ['name']


class LocationGroupAdmin(TabbedTranslationAdmin):
    inlines = [LocationInline]
    search_fields = ['name']


class NetworkAdmin(admin.ModelAdmin):
    search_fields = ['name']


class UserGuestAdmin(admin.ModelAdmin):
    search_fields = ('name', 'email')
    readonly_fields = ('uid',)


class TeamMemberAdmin(admin.ModelAdmin):
    search_fields = ('first_name', 'last_name', 'email', 'position', 'company__name')


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'customer_id', 'subscription_id', 'plan_id')
    search_fields = (
        'user__email',
        'user__userprofile__company__name',
        'customer_id',
        'subscription_id',
        'plan_id',
    )

    def company(self, obj):
        link = reverse(
            'admin:viral_company_change', args=[obj.user.userprofile.company.pk]
        )
        return mark_safe(f'<a href="{link}">{obj.user.userprofile.company.name}</a>')

    company.short_description = 'Company'
    company.admin_order_field = 'user__userprofile__company__name'


admin.site.register(Affiliate, AffiliateAdmin)
admin.site.register(AffiliateWebhook)
admin.site.register(Company, CompanyAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(UserGuest, UserGuestAdmin)
admin.site.register(Network, NetworkAdmin)
admin.site.register(Vendor, VendorAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(AffiliateProgramEntry, AffiliateProgramEntryAdmin)
admin.site.register(
    AffiliateProgramSupporterSubmission, AffiliateProgramSupporterSubmissionAdmin
)
admin.site.register(Location, LocationAdmin)
admin.site.register(LocationGroup, LocationGroupAdmin)
admin.site.register(TeamMember, TeamMemberAdmin)
admin.site.register(Subscription, SubscriptionAdmin)

admin.site.site_header = 'Abaca Administration'
admin.site.site_title = 'Abaca Administration'
