from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ObjectDoesNotExist

from shared.models.logs import Logs
from viral.models.company import Company
from shared.models.consent import Consent

class CustomUserAdmin(UserAdmin):
    def get_deleted_objects(self, objs, request):
        """
        Override default behavior to include User related objects
        """
        (deleted_objects, model_count, perms_needed, protected) = super().get_deleted_objects(objs, request)

        for obj_index, obj in enumerate(objs):
            try:
                company = obj.userprofile.company
            except ObjectDoesNotExist:
                break
            company_queryset = Company.objects.filter(pk=company.pk)
            company_deleted_objects = super().get_deleted_objects(company_queryset, request)

            # Due to the deleted_objects nesting format, we need this formula to get the correct index
            related_deleted_objects = deleted_objects[obj_index * 2 + 1]

            # Filter out User Profile (and its sub-records), since it is already related to the Company
            user_profile_index = None
            for i, v in enumerate(company_deleted_objects[0][1]):
                if isinstance(v, str) and v.startswith('User profile'):
                    user_profile_index = i
            if type(user_profile_index) == int:
                try:
                    del company_deleted_objects[0][1][user_profile_index + 1]
                    del company_deleted_objects[0][1][user_profile_index]
                except IndexError:
                    pass

            # Add User related objects to the deleted_objects list
            related_deleted_objects.extend(company_deleted_objects[0])

            # Add User related model count to the model_count list
            for model, count in company_deleted_objects[1].items():
                if not model == 'user profiles':
                    model_count[model] = model_count.get(model, 0) + count

        return (deleted_objects, model_count, perms_needed, protected)
    
    def delete_model(self, request, obj):
        """
        Override default behavior to also delete the User model related to the Company
        """
        try:
            company = obj.userprofile.company
        except ObjectDoesNotExist:
            company = None

        obj.delete()

        if company:
            company.delete()
        
    def delete_queryset(self, request, queryset):
        """
        Override default behavior to also delete the User models related to each Company
        """
        company_ids = []
        
        for user in queryset.all():
            try:
                company_ids.append(user.userprofile.company.id)
            except ObjectDoesNotExist:
                pass

        queryset.delete()
        Company.objects.filter(id__in=company_ids).delete()

admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), CustomUserAdmin)

@admin.register(Consent)
class ConsentAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'updated_at']
    list_filter = ['consent_type']

admin.site.register(Logs)