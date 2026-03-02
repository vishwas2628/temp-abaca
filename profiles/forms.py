from django import forms
from django.apps import apps

from .models import ProfileIDField


class ProfileIDFieldAdminForm(forms.ModelForm):
    """
    Overrides the source field with a custom select
    containing the field names from selectable app models
    """

    def __init__(self, *args, **kwargs):
        super(ProfileIDFieldAdminForm, self).__init__(*args, **kwargs)

        selectable_fields = {}
        for app_model in ProfileIDField.SELECTABLE_APP_MODELS:
            app_label, model_name = app_model['source'].split(
                '.') if '.' in app_model['source'] else []

            if app_label and model_name:
                model_instance = apps.get_model(
                    app_label=app_label, model_name=model_name)
                model_fields = model_instance._meta.get_fields()
                model_options = [
                    ('%s.%s.%s' % (app_label, model_name, field.name), field.name) for field in model_fields]
                selectable_fields[model_name] = model_options

        # Convert to tuple
        selectable_fields = [(k, v) for k, v in selectable_fields.items()]
        # Add model fields' options to source as a custom select
        self.fields['source'].widget = forms.Select(choices=selectable_fields)
