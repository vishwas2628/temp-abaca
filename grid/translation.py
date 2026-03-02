from modeltranslation.translator import TranslationOptions, register

from .models import Category, CategoryLevel, Level


@register(Category)
class CategoryTranslationOptions(TranslationOptions):
    fields = ('name', 'description', 'requirements_title', 'abbreviation')


@register(CategoryLevel)
class CategoryLevelTranslationOptions(TranslationOptions):
    fields = ('achievements', 'description', 'requirements', 'next_milestones_title',
              'next_milestones_description', 'achieved_milestones_title', 'achieved_milestones_description')


@register(Level)
class LevelTranslationOptions(TranslationOptions):
    fields = ('title', 'description', 'typical_funding')
