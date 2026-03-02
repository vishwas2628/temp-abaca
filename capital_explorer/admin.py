from django.contrib import admin

from capital_explorer.models import CompanyStage, CriteriaWeight, FundingCriteria, FundingStage, FundingSource, FundingType


@admin.register(FundingSource)
class FundingSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']


@admin.register(CompanyStage)
class CompanyStageAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(FundingType)
class FundingTypeAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(FundingStage)
class FundingStageAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(FundingCriteria)
class FundingCriteriaAdmin(admin.ModelAdmin):
    list_display = ['__str__']
    list_filter = ['funding_source']


@admin.register(CriteriaWeight)
class CriteriaWeightAdmin(admin.ModelAdmin):
    list_display = ['name', 'value_matched', 'value_unmatched', 'value_unanswered']
    ordering = ['id']