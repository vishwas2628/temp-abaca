from django.conf import settings
from allauth.utils import get_user_model
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated


class AuthUserThroughAdminMixin:
    """
    Enable requests as admin to mimic an 
    authenticated user by specifying the 
    user ID via request header 'A-User'
    """
    permission_classes = (IsAuthenticated,)

    def initial(self, request, *args, **kwargs):
        is_admin = request.user and request.user.is_staff

        if is_admin:
            user_id = request.headers.get('A-User', None)
            try:
                setattr(request, 'user', get_user_model().objects.get(pk=user_id))
            except:
                pass

        super().initial(request, args, kwargs)


class ConditionalRequiredPerFieldMixin:
    """
    Allows setting a serializer field required value through a custom method:
    Example:
    * email = serializers.EmailField(required=False)
    * def is_email_required(self):
    *    return BOOLEAN_FROM_CONDITION
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            method_name = f'is_{field_name}_required'
            if hasattr(self, method_name):
                field.required = getattr(self, method_name)()


class TranslationsSerializerMixin:
    """
    A mixin to handle translated fields on serializers:
    * 1 - Exclude translation fields (e.g. name_en) from being serialized to avoid bottlenecks.
    * Usage:
    * class MySerializer(TranslationsSerializerMixin):
    *    class Translations:
    *       exclude = ['name']
    """
    available_language_codes = [language[0] for language in settings.LANGUAGES]

    def _exclude_translated_fields(self, fields=[]):
        for field_name in fields:
            for language_code in self.available_language_codes:
                translated_field = f'{field_name}_{language_code}'

                if translated_field in self.fields:
                    self.fields.pop(translated_field)

    def __init__(self, *args, **kwargs):
        assert isinstance(self, serializers.Serializer), "This mixin needs to be applied along with a Serializer class"
        translation_options = getattr(self, 'Translations', None)
        fields_to_exclude = translation_options.exclude if hasattr(translation_options, 'exclude') else []

        # 1 - Initialize serializer:
        super().__init__(*args, **kwargs)

        # 2 - Exclude translated fields:
        self._exclude_translated_fields(fields_to_exclude)
