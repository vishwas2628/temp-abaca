from django.contrib import admin

from modeltranslation.admin import TabbedTranslationAdmin

from adminsortable.admin import SortableAdmin
from markdownx.admin import MarkdownxModelAdmin
from grid.models import Category, CategoryLevel, Level


class CategoryAdmin(SortableAdmin, TabbedTranslationAdmin):
    pass


class CategoryLevelAdmin(MarkdownxModelAdmin, TabbedTranslationAdmin):
    pass


class LevelAdmin(MarkdownxModelAdmin, TabbedTranslationAdmin):
    pass


admin.site.register(Category, CategoryAdmin)
admin.site.register(CategoryLevel, CategoryLevelAdmin)
admin.site.register(Level, LevelAdmin)
