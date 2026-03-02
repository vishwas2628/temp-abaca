import json

from allauth.account.models import EmailAddress
from easy_select2 import Select2, Select2Multiple

from django import forms
from django.contrib import admin
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.urls import reverse

from modeltranslation.admin import TabbedTranslationAdmin

from viral.models import Company, Sector, UserProfile

from .models import (Answer, Criteria, CriteriaWeight, InterestedCTA, Question,
                     QuestionBundle, QuestionCategory, QuestionType, Response,
                     Supporter, SupporterInterestLocation,
                     SupporterInterestSector, SupporterOffering,
                     SupporterOfferingCategories, SupporterOfferingTypes,
                     SupporterType, SupporterWizard)
# Import custom algorithm model and admin classes
from .models.matching_algorithm_results import (MatchingAlgorithms,
                                                MatchingAlgorithmsAdmin)
from profiles.models import ProfileIDField


class ResponseAdmin(admin.ModelAdmin):
    search_fields = ['user_profile__user__email']
    list_filter = ['question__question_type__name']
    autocomplete_fields = ['question', 'user_profile']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('question', 'user_profile').prefetch_related('answers')


class SupporterInterestSectorInline(admin.TabularInline):
    model = SupporterInterestSector
    extra = 1
    autocomplete_fields = ['sector', 'group']
    raw_id_fields = ['supporter']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sector', 'group', 'supporter')


class SupporterInterestLocationInline(admin.TabularInline):
    model = SupporterInterestLocation
    extra = 1
    autocomplete_fields = ['location', 'group']
    raw_id_fields = ['supporter']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('location', 'group', 'supporter')


class IsActiveFilter(admin.SimpleListFilter):
    title = 'Active'
    parameter_name = 'is_active'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == 'yes':
            return queryset.filter(user_profile__user__last_login__isnull=False)
        elif value == 'no':
            return queryset.filter(user_profile__user__last_login__isnull=True)
        return queryset


class SupporterTypeFilter(admin.SimpleListFilter):
    title = 'Types'
    parameter_name = 'types'

    def lookups(self, request, model_admin):
        return SupporterType.objects.filter(public=True).values_list('id', 'name').distinct()

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(types__in=self.value())


class SupporterAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_display = ['name', 'email', 'get_viral_range']
    list_filter = [IsActiveFilter, SupporterTypeFilter]
    inlines = (SupporterInterestSectorInline, SupporterInterestLocationInline)
    autocomplete_fields = ['user_profile', 'types']

    change_list_template = 'admin/supporters-list.html'

    def get_viral_range(self, obj):
        level_range = str(obj.investing_level_range.lower)
        level_range += '-{}'.format(
            obj.investing_level_range.upper) if obj.investing_level_range.upper else ''
        return level_range
    get_viral_range.short_description = 'Investing Level Range'


class SupporterTypeAdmin(TabbedTranslationAdmin):
    search_fields = ['name']


class SupporterWizardForm(forms.ModelForm):
    name = forms.CharField()
    website = forms.CharField()

    class Meta():
        fields = ['name', 'email', 'website', 'about', 'types',
                  'locations', 'sectors', 'investing_level_range']
        labels = {
            'locations': 'Locations of Interest',
            'sectors': 'Sectors of Interest',
        }
        widgets = {
            'company': Select2,
            'locations': Select2Multiple,
            'sectors': Select2Multiple,
        }


class SupporterWizardAdmin(admin.ModelAdmin):
    """
    A custom admin page that creates all needed models
    to have a fully functioning Supporter account
    """
    form = SupporterWizardForm

    def has_module_permission(self, request):
        # Hides model from main admin list
        return False

    def has_change_permission(self, request, *args):
        # Disable editing
        return False

    def changelist_view(self, request, extra_context=None):
        # Use Supporters' list as default changelist view
        return HttpResponseRedirect(reverse("admin:matching_supporter_changelist"))

    def _create_user(self):
        self.user = User.objects.create_user(
            username=self.valid_data['email'], email=self.valid_data['email'])

    def _create_email_address(self):
        EmailAddress.objects.create(
            user=self.user, email=self.valid_data['email'], primary=True, verified=True)

    def _create_company(self):
        self.company = Company(name=self.valid_data['name'],
                               about=self.valid_data['about'],
                               email=self.valid_data['email'],
                               website=self.valid_data['website'],
                               type=Company.SUPPORTER)
        self.company.save()
        self.company.sectors.add(*self.valid_data['sectors'])
        self.company.locations.add(*self.valid_data['locations'])
        self.company.save()

    def _create_user_profile(self):
        self.user_profile = UserProfile.objects.create(
            user=self.user, company=self.company)

    def save_model(self, request, obj, form, change):
        """
        Save all models submitted with this form (Company, Supporter, User)
        """
        self.valid_data = form.cleaned_data

        # Only allow creation
        if not change:
            self._create_user()
            self._create_email_address()
            self._create_company()
            self._create_user_profile()
            obj.user_profile = self.user_profile
            # Create Supporter
            super().save_model(request, obj, form, change)


class SectorForm(forms.ModelForm):
    class Meta:
        model = Sector
        fields = '__all__'
        widgets = {
            'groups': Select2Multiple,
        }


class SectorAdmin(TabbedTranslationAdmin):
    list_display = ['name', 'get_groups', 'get_number']
    search_fields = ('name', 'groups__name')

    form = SectorForm

    filter_horizontal = ()
    list_filter = ()
    fieldsets = ()

    def get_groups(self, obj):
        return ", ".join([group.name for group in obj.groups.all()])
    get_groups.short_description = 'Groups'

    def get_number(self, obj):
        return len(obj.company_set.all())
    get_number.short_description = "Number of Companies"


class InterestedAdmin(admin.ModelAdmin):
    list_per_page = 25
    list_display = ['supporter', 'entrepreneur', 'supporter_is_interested',
                    'entrepreneur_is_interested', 'state_of_interest', 'get_entrepreneur_viral_level',
                    'get_entrepreneur_locations', 'get_entrepreneur_sectors', 'get_supporter_investing_level_range',
                    'get_supporter_locations', 'get_supporter_sectors']

    list_filter = ['supporter_is_interested',
                   'entrepreneur_is_interested', 'state_of_interest']
    search_fields = ['supporter', 'entrepreneur', 'supporter_is_interested',
                     'entrepreneur_is_interested', 'state_of_interest']

    # Custom variable to limit fields with too much data (sectors, locations)
    formatted_display_limit = 10

    def _get_formatted_sectors(self, all_sectors):
        sectors = [sector.name.capitalize() for sector in all_sectors]
        # Grab sectors with limit and join them by commas
        formatted_sectors = ", ".join(sectors[:self.formatted_display_limit])
        formatted_sectors += "..." if len(
            sectors) > self.formatted_display_limit else ""
        return formatted_sectors

    def _get_formatted_locations(self, all_locations):
        location_fields = ['city', 'region', 'country', 'continent']
        formatted_locations = []

        for location in all_locations:
            valid_location = ''
            available_fields = list(
                filter(lambda field: hasattr(location, field) and len(getattr(location, field)), location_fields))
            # Create valid location with existing values separated by commas
            valid_location += ', '.join([getattr(location, field)
                                         for field in available_fields])
            if valid_location:
                formatted_locations.append(valid_location)

        # Grab all valid locations and separate them by dashes
        formatted_locations = ' — '.join(formatted_locations)
        return formatted_locations

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('entrepreneur__sectors',
                                                              'entrepreneur__locations',
                                                              'supporter__sectors',
                                                              'supporter__locations')

    def get_entrepreneur_viral_level(self, obj):
        return obj.entrepreneur.latest_assessment().level.value if obj.entrepreneur.latest_assessment() else ''
    get_entrepreneur_viral_level.short_description = 'Entrepreneur Viral Level'

    def get_entrepreneur_sectors(self, obj):
        # Get just enough sectors to check if it's above the display limit
        sectors = obj.entrepreneur.sectors.all(
        )[:self.formatted_display_limit + 1]
        return self._get_formatted_sectors(sectors)
    get_entrepreneur_sectors.short_description = 'Entrepreneur Sectors'

    def get_entrepreneur_locations(self, obj):
        # Get just enough locations to check if it's above the display limit
        locations = obj.entrepreneur.locations.all(
        )[:self.formatted_display_limit + 1]
        return self._get_formatted_locations(locations)
    get_entrepreneur_locations.short_description = 'Entrepreneur Locations'

    def get_supporter_investing_level_range(self, obj):
        return obj.supporter.company_profile.supporter.get().investing_level_range
    get_supporter_investing_level_range.short_description = 'Supporter Investing Level Range'

    def get_supporter_sectors(self, obj):
        # Get just enough sectors to check if it's above the display limit
        sectors = obj.supporter.company_profile.supporter.get().sectors.all(
        )[:self.formatted_display_limit + 1]
        return self._get_formatted_sectors(sectors) or None
    get_supporter_sectors.short_description = 'Supporter Sectors of Interest'
    get_supporter_sectors.empty_value_display = '(Any)'

    def get_supporter_locations(self, obj):
        # Get just enough locations to check if it's above the display limit
        locations = obj.supporter.company_profile.supporter.get().locations.all(
        )[:self.formatted_display_limit + 1]
        return self._get_formatted_locations(locations) or None
    get_supporter_locations.short_description = 'Supporter Locations of Interest'
    get_supporter_locations.empty_value_display = '(Any)'


class CriteriaAdmin(admin.ModelAdmin):
    search_fields = ('name', 'question__resource_question', 'supporter__user_profile__user__email',)
    autocomplete_fields = ('supporter', 'question', 'answers')


class QuestionProfileFieldsFilter(admin.SimpleListFilter):
    title = 'Linked to Profile Fields'
    parameter_name = 'field'

    def lookups(self, request, model_admin):
        return ProfileIDField.objects.values_list('id', 'name').distinct()

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(profile_field__in=self.value())
        return queryset


class QuestionAdmin(TabbedTranslationAdmin):
    search_fields = ('entrepreneur_question', 'resource_question', 'short_name')
    list_filter = [QuestionProfileFieldsFilter]


class QuestionBundleAdmin(admin.ModelAdmin):
    change_form_template = 'admin/questionbundle-form.html'

    def changeform_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['team_member_question_ids'] = json.dumps(
            list(Question.objects.filter(is_team_member_question=True).values_list('id', flat=True)))
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)


class AnswerAdmin(TabbedTranslationAdmin):
    search_fields = ('value',)


admin.site.register(Sector, SectorAdmin)

admin.site.register(Supporter, SupporterAdmin)
admin.site.register(SupporterType, SupporterTypeAdmin)
admin.site.register(SupporterWizard, SupporterWizardAdmin)
admin.site.register(CriteriaWeight, TabbedTranslationAdmin)
admin.site.register(Criteria, CriteriaAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(QuestionType)
admin.site.register(QuestionCategory, TabbedTranslationAdmin)
admin.site.register(QuestionBundle, QuestionBundleAdmin)
admin.site.register(Answer, AnswerAdmin)
admin.site.register(Response, ResponseAdmin)
admin.site.register(SupporterOffering)
admin.site.register(SupporterOfferingCategories, TabbedTranslationAdmin)
admin.site.register(SupporterOfferingTypes, TabbedTranslationAdmin)
admin.site.register(InterestedCTA, InterestedAdmin)

admin.site.register(MatchingAlgorithms, MatchingAlgorithmsAdmin)
