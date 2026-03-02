from modeltranslation.translator import TranslationOptions, register

from .models import (Answer, CriteriaWeight, Question, QuestionCategory,
                     SupporterOfferingCategories, SupporterOfferingTypes,
                     SupporterType)


@register(Answer)
class AnswerTranslationOptions(TranslationOptions):
    fields = ('value', 'instructions',)


@register(CriteriaWeight)
class CriteriaWeightTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Question)
class QuestionTranslationOptions(TranslationOptions):
    fields = ('entrepreneur_question', 'resource_question', 'short_name', 'instructions',)


@register(QuestionCategory)
class QuestionCategoryTranslationOptions(TranslationOptions):
    fields = ('name', 'description',)


@register(SupporterOfferingCategories)
class SupporterOfferingCategoriesTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(SupporterOfferingTypes)
class SupporterOfferingTypesTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(SupporterType)
class SupporterTypeTranslationOptions(TranslationOptions):
    fields = ('name', 'description', 'label')
