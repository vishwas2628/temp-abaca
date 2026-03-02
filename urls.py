# -*- coding: utf-8 -*-
# from admin_site.admin import AdminSite
import settings

import aldryn_addons.urls
import debug_toolbar
from aldryn_django.utils import i18n_patterns
from django.urls import path
from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from markdownx import urls as markdownx
from rest_framework.documentation import include_docs_urls

from shared.views import AdminLoginAsUserView

# adminSite = AdminSite(name="Abaca Admin")
# print(adminSite.urls)


def url_for_staging(*args, **kwargs):
    result = url(*args, **kwargs)
    if settings.IS_LIVE_ENVIRONMENT:
        result.resolve = lambda *args: None
    return result


urlpatterns = (
    [
        url_for_staging(r'^docs/', include_docs_urls(title='Viral API Documentation')),
        url_for_staging(r'__debug__/', include(debug_toolbar.urls)),
        url(r'^', include('sdg.urls')),
        url(r'^', include('viral.urls')),
        url(r'^', include('grid.urls')),
        url(r'^', include('matching.urls')),
        url(r'^', include('shared.urls')),
        url(r'^', include('profiles.urls')),
        url(r'^', include('company_lists.urls')),
        url(r'^', include('milestone_planner.urls')),
        url(r'^', include('capital_explorer.urls')),
        url(r'^markdownx/', include(markdownx)),
        url(r'^tinymce/', include('tinymce.urls')),
        # url(r'^admin-site/', adminSite.urls),
        # add your own patterns here
    ]
    + aldryn_addons.urls.patterns()
    + i18n_patterns(
        # Admin as User - Request session
        *aldryn_addons.urls.i18n_patterns(),  # MUST be the last entry!
    )
    + static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT,
    )
)

# Include Silk routes locally
# if settings.IS_DEBUG_ON:
urlpatterns.insert(0, url(r'^silk/', include('silk.urls', namespace='silk')))

if settings.JET_PROJECT and settings.JET_TOKEN:
    from jet_django.urls import jet_urls

    urlpatterns.insert(0, url(r'^jet_api/', include(jet_urls)))
