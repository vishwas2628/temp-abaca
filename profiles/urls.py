from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from profiles import views

urlpatterns = [
    url(r'^profile-id-fields/(?P<pk>[0-9]+)/?$', views.ProfileIDFieldsView.as_view(),
        name="get_profile_id_fields"),
]

urlpatterns = format_suffix_patterns(urlpatterns)
