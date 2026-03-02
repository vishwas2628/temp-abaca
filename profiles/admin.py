from django.contrib import admin

from .models import ProfileIDField
from .forms import ProfileIDFieldAdminForm


class ProfileIDFieldAdmin(admin.ModelAdmin):
    list_display = ('name', 'source')
    form = ProfileIDFieldAdminForm


admin.site.register(ProfileIDField, ProfileIDFieldAdmin)
