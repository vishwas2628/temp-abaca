from functools import cached_property
from django.db import models, connection
from django.urls import path, reverse, resolve
from django.contrib import admin
from django.utils.safestring import mark_safe

from django.template.response import TemplateResponse

from grid.models import Assessment
from viral.models import Company
from matching.models import Supporter, CriteriaWeight, Response


def getAlgorithmModel(db_table):
    class InnerMetaClass(models.base.ModelBase):
        def __new__(cls, name, bases, attrs):
            model = super(InnerMetaClass, cls).__new__(cls, name, bases, attrs)
            model._meta.db_table = db_table
            return model

    class MatchingAlgorithmResults(models.Model):
        __metaclass__ = InnerMetaClass

        company = models.OneToOneField(
            Company, primary_key=True, on_delete=models.DO_NOTHING)
        match_quantity = models.IntegerField(verbose_name='Matches Available')

        @property
        def company_role(self):
            for user_type in Company.USER_TYPE:
                if self.company.type in user_type:
                    return user_type[self.company.type]
            return ""

        @property
        def company_name(self):
            return self.company.name or ""

        class Meta:
            managed = False
            verbose_name_plural = 'Algorithm List'

    return MatchingAlgorithmResults


def getAlgorithmDetailsModel(db_table):
    class InnerMetaClass(models.base.ModelBase):
        def __new__(cls, name, bases, attrs):
            model = super(InnerMetaClass, cls).__new__(cls, name, bases, attrs)
            model._meta.db_table = db_table
            return model

    class MatchingAlgorithmDetail(models.Model):
        __metaclass__ = InnerMetaClass

        company = models.OneToOneField(
            Company, primary_key=True, on_delete=models.DO_NOTHING, verbose_name='Entrepreneur')
        supporter = models.OneToOneField(
            Supporter, on_delete=models.DO_NOTHING)
        max_score_percentil = models.IntegerField()

        # Extra fields needed for showcasing the matching calculus rationale:
        viral_level = None
        total_score = 0
        criteria_scores = None

        def matching_percentage(self):
            return f"{self.max_score_percentil}%"
        matching_percentage.admin_order_field = 'max_score_percentil'

        def investing_level_range(self):
            return self.supporter.investing_level_range

        def company_link(self):
            company_link = reverse('admin:%s_%s_change' %
                                   (self.company._meta.app_label, self.company._meta.model_name),
                                   args=[self.company.pk])
            return mark_safe(
                f'''<a onclick="return windowpop(this.href, 900, 500)" href="{company_link}" target="blank">
                    {self.company.name}</a>''')
        company_link.short_description = 'Entrepreneur'

        def supporter_link(self):
            supporter_link = reverse('admin:%s_%s_change' %
                                     (self.supporter._meta.app_label, self.supporter._meta.model_name),
                                     args=[self.supporter.pk])
            return mark_safe(
                f'''<a onclick="return windowpop(this.href, 900, 500)" href="{supporter_link}" target="blank">
                    {self.supporter.name}</a>''')
        supporter_link.short_description = 'Supporter'

        def company_responses_link(self):
            response_list_link = f'{reverse("admin:matching_response_changelist")}?q={self.company.company_profile.user.email}'
            return mark_safe(
                f'''<a onclick="return windowpop(this.href, 900, 500)" href="{response_list_link}"
                    target="blank">view</a>''')
        company_responses_link.short_description = 'Responses'

        def supporter_responses_link(self):
            criteria_list_link = f'{reverse("admin:matching_criteria_changelist")}?q={self.supporter.user_profile.user.email}'
            return mark_safe(
                f'''<a onclick="return windowpop(this.href, 900, 500)" href="{criteria_list_link}"
                    target="blank">view</a>''')
        supporter_responses_link.short_description = 'Responses'

        def get_relative_percentage_score_of_criteria(self, criteria):
            # Calculate and return the relative percentage score of an
            # individual criteria in regards to its total matching percentage
            score = self.criteria_scores[criteria]['score'] if self.criteria_scores else 0
            max_score = self.criteria_scores[criteria]['max_score'] if self.criteria_scores else 0

            if None in [score, max_score, self.max_score_percentil, self.total_score] or self.total_score == 0:
                return 0

            impact_by_score = round(
                self.max_score_percentil * round(score * 100 / self.total_score, 2) / 100, 2)
            impact_by_max_score = round(
                self.max_score_percentil * round(max_score * 100 / self.total_score, 2) / 100)

            if score > 0:
                return f"+{impact_by_score}%" if impact_by_score else 0
            elif score < 0:
                return f"{impact_by_score}%" if impact_by_score < 0 else f"-{impact_by_max_score}%"
            else:
                return 0

        def level_impact(self):
            return self.get_relative_percentage_score_of_criteria('level')

        def location_impact(self):
            return self.get_relative_percentage_score_of_criteria('location')

        def sector_impact(self):
            return self.get_relative_percentage_score_of_criteria('sector')

        def response_impact(self):
            return self.get_relative_percentage_score_of_criteria('response')

        class Meta:
            managed = False
            verbose_name_plural = 'Algorithm Detailed Results'

    return MatchingAlgorithmDetail


class MatchingAlgorithms(models.Model):
    """
    Model class only used on Admin to show different
    matching algorithm versions
    """

    class Meta:
        managed = False
        verbose_name_plural = 'Algorithms'
        db_table = "matching\".\"algorithm"


class MatchingAlgorithmsAdmin(admin.ModelAdmin):
    """
    Add custom admin page and lists for the different
    matching algorithm versions
    """
    change_list_template = 'matching/algorithm_list.html'
    algorithms = {
        'initial': {
            'table': 'initial_match_quantity_view'
        },
        'exclusion': {
            'table': 'exclusion_match_quantity_view'
        },
        'penalisation': {
            'table': 'penalisation_match_quantity_view'
        },
        'penalisation101': {
            'table': 'penalisation101_match_quantity_view'
        }
    }

    @cached_property
    def default_criteria_weights(self):
        c = connection.cursor()
        try:
            c.execute("""select level_weight_id, location_weight_id, sector_weight_id, response_weight_id
                         from matching.algorithm where active = true""")
            row = c.fetchone()
            criteria_weights = CriteriaWeight.objects.filter(pk__in=row)
            return {
                'level': criteria_weights.get(pk=row[0]),
                'location': criteria_weights.get(pk=row[1]),
                'sector': criteria_weights.get(pk=row[2]),
                'response': criteria_weights.get(pk=row[3]),
            }
        except Exception:
            return None

    def is_details_view(self, request):
        return 'algorithm_detail_view' in resolve(request.path).view_name

    def get_queryset(self, request):
        # Add lookup field filtering:
        queryset = super().get_queryset(request)

        if self.is_details_view(request):
            queryset.select_related('company__company_profile__user', 'supporter')

        if hasattr(self, 'lookup') and self.lookup:
            return queryset.filter(**self.lookup)
        return queryset

    def check_for_algorithm_refresh(self, request, algorithm, company=None):
        # Refresh algorithm results when the refresh query param exists:
        request.GET = request.GET.copy()  # First, turn GET property into mutable
        needs_refresh = request.GET.pop('refresh', None)  # Then, pop out refresh param if exists.

        if needs_refresh:
            c = connection.cursor()
            try:
                # Either, refresh specific criteria scores
                if company and company.type == Company.SUPPORTER:
                    supporter_pk = Supporter.objects.filter(
                        user_profile__company__pk=company_id).values_list(
                        'pk', flat=True).first()
                    if supporter_pk:
                        c.execute(f"""
                        select matching.refresh_sector_score(_refresh_all := false, _supporter_id := {supporter_pk});
                        select matching.refresh_level_score(_refresh_all := false, _supporter_id := {supporter_pk});
                        select matching.refresh_location_score(_refresh_all := false, _supporter_id := {supporter_pk});
                        select matching.refresh_response_score(_refresh_all := false, _supporter_id := {supporter_pk});
                        select matching.refresh_total_score(_refresh_all := false, _supporter_id := {supporter_pk});
                        """)
                elif company and company.type == Company.ENTREPRENEUR:
                    c.execute(f"""
                        select matching.refresh_sector_score(_refresh_all := false, _company_id := {company.pk});
                        select matching.refresh_level_score(_refresh_all := false, _company_id := {company.pk});
                        select matching.refresh_location_score(_refresh_all := false, _company_id := {company.pk});
                        select matching.refresh_response_score(_refresh_all := false, _company_id := {company.pk});
                        select matching.refresh_total_score(_refresh_all := false, _company_id := {company.pk});
                        """)
                # Or, refresh all total scores
                else:
                    c.execute(f"refresh materialized view matching.{algorithm}_total_score")
            except Exception as error:
                raise error

    def has_add_permission(self, request):
        # Remove add button
        return False

    def changelist_view(self, request, extra_context=None):
        # Reset settings
        self.lookup = None
        self.list_filter = ()
        self.search_fields = ()

        # Inject the algorithm list menu on the template
        extra_context = extra_context or {}
        extra_context['algorithms_menu'] = []

        for slug, options in self.algorithms.items():
            name = options['name'] if 'name' in options else slug.capitalize()
            extra_context['algorithms_menu'].append({
                'uri': slug, 'name': name
            })
        return super().changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        # Inject algorithm results & detail views' urls
        urls = super().get_urls()
        my_urls = []

        my_urls.append(
            path(
                'calculator/', self.admin_site.admin_view(self.algorithm_calculator_view),
                name="matching_algorithm_calculator"))

        for slug, options in self.algorithms.items():
            my_urls.append(
                path('<{uri}>/'.format(uri=slug),
                     self.admin_site.admin_view(self.algorithm_results_view))
            )
            my_urls.append(
                path('<path:object_id>/',
                     self.admin_site.admin_view(self.algorithm_detail_view))
            )

        return my_urls + urls

    def algorithm_results_view(self, request, **algorithm):
        current_algorithm = next(iter(algorithm.values()))
        algorithm_options = self.algorithms[current_algorithm] if current_algorithm in self.algorithms else {}
        list_title = algorithm_options['title'] if 'title' in algorithm_options else current_algorithm.capitalize()

        # Refresh current algorithm results before presenting results:
        self.check_for_algorithm_refresh(request, current_algorithm)

        # Reset lookups
        self.lookup = None

        # Set current algorithm table
        algorithm_table = "matching\".\"{table}".format(table=algorithm_options['table'])
        self.model = getAlgorithmModel(algorithm_table)
        self.model._meta.db_table = algorithm_table
        super().__init__(self.model, self.admin_site)

        # Set list columns
        self.list_display = ('company_name', 'match_quantity')
        # Add scores filter
        self.list_filter = ('company__type', MatchesAvailableFilter,)
        # Add searchable fields
        self.search_fields = ['company__name']
        # Prefetch data
        self.list_select_related = ('company',)

        # Fetch list
        cl = self.get_changelist_instance(request)
        cl.formset = None
        cl.title = '{algorithm} - Results'.format(algorithm=list_title)

        context = dict(
            self.admin_site.each_context(request),
            title=cl.title,
            is_popup=cl.is_popup,
            to_field=cl.to_field,
            cl=cl,
            has_add_permission=self.has_add_permission(request),
            opts=cl.opts,
        )

        return TemplateResponse(request, 'matching/algorithm_results.html', context)

    def _preload_data_for_supporter_matches(self, supporter, changelist):
        # Load all viral levels in bulk:
        company_ids = list(map(lambda result: result.company.pk, list(changelist.queryset)))
        companies_viral_levels = Assessment.objects.filter(
            evaluated__in=company_ids).distinct('evaluated').order_by(
            'evaluated', '-created_at').values('evaluated', 'level__value')
        for result in changelist.result_list:
            result.viral_level = next(
                (viral_level['level__value'] for viral_level in companies_viral_levels
                    if viral_level['evaluated'] == result.company.pk), None)

        # Load scores between the Supporter and each Entrepreneur:
        c = connection.cursor()
        company_ids = list(map(str, company_ids))
        try:
            # 1 - Get final score
            c.execute(f"""select company_id, supporter_id, score from matching.total_score
                where supporter_id = {supporter.pk}""")
            total_scores = c.fetchall()
            for result in changelist.result_list:
                result.total_score = next(
                    (row[2] for row in total_scores
                        if row[0] == result.company.pk and row[1] == result.supporter.pk), None)
            # 2 - Get criteria scores:
            c.execute(f"""
                select ls.company_id, ls.supporter_id,
                    ls.score as level_score, ls.max_score as level_max_score,
                    ss.score as sector_score, ss.max_score as sector_max_score,
                    lcs.score as location_score, lcs.max_score as location_max_score,
                    rs.score as response_score, rs.max_score as response_max_score
                from matching.level_score as ls
                left join matching.sector_score as ss
                    on ss.company_id = ls.company_id and ss.supporter_id = ls.supporter_id
                left join matching.location_score as lcs
                    on lcs.company_id = ls.company_id and lcs.supporter_id = ls.supporter_id
                left join matching.response_score as rs
                    on rs.company_id = ls.company_id and rs.supporter_id = ls.supporter_id
                where ls.supporter_id = {supporter.pk};
            """)
            all_criteria_scores = c.fetchall()
            # Skip setting all criteria scores when missing from a pending refresh:
            if not len(all_criteria_scores):
                return
            for result in changelist.result_list:
                criteria_scores = next(
                    (row for row in all_criteria_scores
                     if row[0] == result.company.pk and row[1] == result.supporter.pk),
                    [])
                if not len(criteria_scores):
                    continue
                _, _, level_score, level_max_score, \
                    sector_score, sector_max_score, location_score, location_max_score, \
                    response_score, response_max_score = criteria_scores
                result.criteria_scores = {
                    'level': {
                        'score': level_score,
                        'max_score': level_max_score
                    },
                    'sector': {
                        'score': sector_score,
                        'max_score': sector_max_score
                    },
                    'location': {
                        'score': location_score,
                        'max_score': location_max_score
                    },
                    'response': {
                        'score': response_score,
                        'max_score': response_max_score
                    }
                }
        except Exception as error:
            raise error

    def _preload_data_for_entrepreneur_matches(self, company, changelist):
        # Load scores between the Entrepreneur and each Supporter:
        c = connection.cursor()
        try:
            # 1 - Get final score
            c.execute(f"""select company_id, supporter_id, score from matching.total_score
                where company_id = {company.pk}""")
            total_scores = c.fetchall()
            for result in changelist.result_list:
                result.total_score = next(
                    (row[2] for row in total_scores
                        if row[0] == result.company.pk and row[1] == result.supporter.pk), None)
            # 2 - Get criteria scores:
            c.execute(f"""
                select ls.company_id, ls.supporter_id,
                    ls.score as level_score, ls.max_score as level_max_score,
                    ss.score as sector_score, ss.max_score as sector_max_score,
                    lcs.score as location_score, lcs.max_score as location_max_score,
                    rs.score as response_score, rs.max_score as response_max_score
                from matching.level_score as ls
                left join matching.sector_score as ss
                    on ss.company_id = ls.company_id and ss.supporter_id = ls.supporter_id
                left join matching.location_score as lcs
                    on lcs.company_id = ls.company_id and lcs.supporter_id = ls.supporter_id
                left join matching.response_score as rs
                    on rs.company_id = ls.company_id and rs.supporter_id = ls.supporter_id
                where ls.company_id = {company.pk};
            """)
            all_criteria_scores = c.fetchall()
            # Skip setting all criteria scores when missing from a pending refresh:
            if not len(all_criteria_scores):
                return
            for result in changelist.result_list:
                criteria_scores = next(
                    (row for row in all_criteria_scores
                     if row[0] == result.company.pk and row[1] == result.supporter.pk),
                    [])
                if not len(criteria_scores):
                    continue
                _, _, level_score, level_max_score, \
                    sector_score, sector_max_score, location_score, location_max_score, \
                    response_score, response_max_score = criteria_scores
                result.criteria_scores = {
                    'level': {
                        'score': level_score,
                        'max_score': level_max_score
                    },
                    'sector': {
                        'score': sector_score,
                        'max_score': sector_max_score
                    },
                    'location': {
                        'score': location_score,
                        'max_score': location_max_score
                    },
                    'response': {
                        'score': response_score,
                        'max_score': response_max_score
                    }
                }
        except Exception as error:
            raise error

    def algorithm_detail_view(self, request, **kwargs):
        kwargs_list = next(iter(kwargs.values())).split('/')
        current_algorithm = kwargs_list[0]
        current_company_id = kwargs_list[1]
        current_company = Company.objects.get(pk=current_company_id)
        supporter = None

        # Refresh current algorithm results before presenting results:
        self.check_for_algorithm_refresh(request, current_algorithm, current_company)

        # Set current algorithm table
        self.algorithm_table = "matching\".\"{table}_total_score".format(table=current_algorithm)
        self.model = getAlgorithmDetailsModel(self.algorithm_table)
        self.model._meta.db_table = self.algorithm_table
        super().__init__(self.model, self.admin_site)

        if current_company.type == Company.ENTREPRENEUR:
            self.lookup = {'company_id': current_company_id}
            self.list_display = ('supporter_link', 'matching_percentage', 'investing_level_range', 'level_impact',
                                 'sector_impact', 'location_impact', 'response_impact', 'supporter_responses_link')
            self.list_select_related = ('company', 'supporter', 'supporter__user_profile__user')
            self.search_fields = ['supporter__name']
        elif current_company.type == Company.SUPPORTER:
            supporter = Supporter.objects.prefetch_related(
                'criteria_set', 'sectors', 'locations').get(
                user_profile__company__pk=current_company_id)
            self.lookup = {'supporter_id': supporter.id}
            self.list_select_related = ('company', 'company__company_profile',
                                        'company__company_profile__user',)
            self.list_display = ('company_link', 'matching_percentage', 'viral_level', 'level_impact',
                                 'sector_impact', 'location_impact', 'response_impact', 'company_responses_link')
            self.search_fields = ['company__name']

        # Disable any list filters:
        self.list_filter = []

        # Fetch list
        cl = self.get_changelist_instance(request)
        cl.formset = None
        cl.title = '{company} - Available Matches'.format(company=current_company.name)

        if supporter:
            self._preload_data_for_supporter_matches(supporter, cl)
        else:
            self._preload_data_for_entrepreneur_matches(current_company, cl)

        # Initialize template context:
        context = dict(
            self.admin_site.each_context(request),
            title=cl.title,
            is_popup=cl.is_popup,
            to_field=cl.to_field,
            cl=cl,
            has_add_permission=self.has_add_permission(request),
            opts=cl.opts,
        )

        # Include Supporter instance to showcase his criteria and criteria weights:
        if supporter:
            context['supporter'] = supporter
            # Provide fallback criteria weights:
            context['default_weights'] = self.default_criteria_weights
        else:
            # Include Entrepreneur's latest assessment's viral level
            context['company'] = current_company
            context['viral_level'] = Assessment.objects.filter(
                evaluated=current_company.id).values_list(
                'level__value', flat=True).order_by('-created_at').first()
            context['entrepreneur_responses'] = Response.objects.filter(user_profile__company=current_company)

        return TemplateResponse(request, 'matching/algorithm_detail.html', context)

    def algorithm_calculator_view(self, request):
        change_list = self.get_changelist_instance(request)
        change_list.formset = None
        context = dict(
            self.admin_site.each_context(request),
            title='Algorithm Calculator',
            is_popup=change_list.is_popup,
            to_field=change_list.to_field,
            cl=change_list,
            has_add_permission=self.has_add_permission(request),
            opts=change_list.opts,
        )
        return TemplateResponse(request, 'matching/algorithm_calculator.html', context)


class MatchesAvailableFilter(admin.SimpleListFilter):
    """
    Custom list filter for the matching algorithm results 
    """
    title = 'Matches Available'
    parameter_name = 'ma'

    def lookups(self, request, model_admin):
        return (
            ('zero', ('No matches')),
            ('l10', ("Less than 10")),
            ('l25', ("Less than 25")),
        )

    def queryset(self, request, queryset):
        if self.value() == 'zero':
            return queryset.filter(match_quantity=0)
        if self.value() == 'l10':
            return queryset.filter(match_quantity__lte=10).exclude(match_quantity=0)
        if self.value() == 'l25':
            return queryset.filter(match_quantity__lte=25).exclude(match_quantity=0)
