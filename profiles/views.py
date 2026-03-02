from django.apps import apps

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from viral.models import UserProfile

from .models import ProfileIDField
from .serializers import ProfileIDFieldSerializer


class ProfileIDFieldsView(generics.RetrieveAPIView):
    """
    Return a Profile ID Field with its name 
    and associated value from a user's profile 
    """
    queryset = ProfileIDField.objects.all()
    serializer_class = ProfileIDFieldSerializer
    permission_classes = (IsAuthenticated,)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        field_name = instance.name
        field_value = None

        try:
            # Find profile field value
            user_profile = UserProfile.objects.get(user=request.user)
            source_model = apps.get_model(
                app_label=instance.app_label, model_name=instance.model_name)
            by_user_profile = {instance.user_profile_relation: user_profile}
            model_instance = source_model.objects.get(**by_user_profile)
            field_value = getattr(model_instance, instance.field_name, None)
        except:
            # Else return null
            pass

        serializer = self.get_serializer(
            data={'name': field_name, 'value': field_value})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
