from modeltranslation.translator import TranslationOptions, register

from .models import Sector, Group, LocationGroup, Affiliate


@register(Group)
class SectorGroupTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Sector)
class SectorTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(LocationGroup)
class LocationGroupTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Affiliate)
class AffiliateTranslationOptions(TranslationOptions):
    fields = ('summary', 'disclaimer_heading', 'disclaimer_body', 'self_assessment_step_description', 'self_assessment_step_note', 'questions_step_description', 'questions_step_note', 'team_members_step_description', 'team_members_step_note')