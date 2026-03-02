from datetime import datetime

import bugsnag

from django.apps import apps
from matching.models import QuestionType
from rest_framework.serializers import Serializer


class UpdateProfileFieldsSerializerMixin(Serializer):
    """
    A mixin that provides a method that when gets called,
    will update profile fields based on the responses given
    with questions that have a profile field override.
    """

    def _update_profile_fields(self, user_profile, responses=None, criteria=None):
        values_to_update = responses or criteria
        values_key = 'value' if responses else 'desired'

        for response in values_to_update:
            profile_field = response.question.profile_field

            # Skip update for questions without profile field
            if profile_field is None:
                continue

            source_model = apps.get_model(app_label=profile_field.app_label, model_name=profile_field.model_name)
            relation_to_profile = profile_field.user_profile_relation
            by_user_profile = {relation_to_profile: user_profile}

            try:
                # Find user's model instance
                model_instance = source_model.objects.get(**by_user_profile)

                # TEMP: For now, only text & date values are supported
                question_type = response.question.question_type.type
                response_value = getattr(response, values_key)

                if response_value:
                    if question_type == QuestionType.FREE_RESPONSE:
                        text_value = str(response_value.get('text', ''))
                        setattr(model_instance, profile_field.field_name, text_value)
                    elif question_type == QuestionType.DATE:
                        date_value = response_value.get('date', datetime.now())
                        date_value = datetime.strptime(date_value, "%Y-%m-%d").date()
                        setattr(model_instance, profile_field.field_name, date_value)
                elif response.answers.exists():
                    setattr(model_instance, profile_field.field_name, response.answers.all())
                model_instance.save()
            except Exception as e:
                bugsnag.notify(Exception("Could not sync profile field."),
                               meta_data={"context": {"error": e}})
