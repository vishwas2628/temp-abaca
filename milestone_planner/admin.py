from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from grid.models.category import Category
from milestone_planner.models.milestone import Milestone


class MilestoneCategoryFilter(admin.SimpleListFilter):
    title = 'Category'
    parameter_name = 'category'

    def lookups(self, request, model_admin):
        return Category.objects.filter(group=2).values_list('id', 'name').distinct()

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(category_level__category=self.value())


class MilestoneAdmin(SimpleHistoryAdmin):
    autocomplete_fields = ['evidence']
    readonly_fields = ['uid', 'user_profile', 'category_level', 'state']
    search_fields = ['user_profile__company__name']
    history_list_display = ['state', 'plan_published', 'target_date', 'evidence_published', 'date_of_completion']
    list_filter = [MilestoneCategoryFilter]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user_profile__company',
            'category_level__category', 'category_level__level', 'category_level__category__group')


admin.site.register(Milestone, MilestoneAdmin)
