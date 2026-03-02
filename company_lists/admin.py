from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.contrib.admin.widgets import AutocompleteSelect
from company_lists.models import CompanyList, Process, ProcessStep


class CompanyListForm(forms.ModelForm):
    class Meta:
        model = CompanyList
        fields = '__all__'

    def clean(self):
        invited_users = self.cleaned_data.get('invited_users')

        if invited_users.filter(pk=self.instance.owner_id).exists():
            raise ValidationError({"invited_users": "Cannot add yourself as an invited user."})

        super().clean()


class CompanyListAdmin(admin.ModelAdmin):
    form = CompanyListForm
    readonly_fields = ('uid',)
    search_fields = ('owner__company__name', 'owner__user__email')
    autocomplete_fields = ('owner', 'invited_users', 'invited_guests', 'companies')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner').prefetch_related('invited_users', 'invited_guests', 'companies')
    

class ProcessStepInline(admin.TabularInline):
    model = ProcessStep
    extra = 0
    max_num = 9


class ProcessForm(forms.ModelForm):
    class Meta:
        widgets = {'company': AutocompleteSelect(Process._meta.get_field('company').remote_field, admin.site)}


class ProcessAdmin(admin.ModelAdmin):
    form = ProcessForm
    list_display = ['title', 'company']
    list_filter = ['company']
    search_fields = ['title', 'company__name']
    inlines = [ProcessStepInline]
    change_form_template = 'admin/process-form.html'


admin.site.register(CompanyList, CompanyListAdmin)
admin.site.register(Process, ProcessAdmin)
