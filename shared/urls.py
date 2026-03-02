from django.conf.urls import url
from django.views.generic import TemplateView
from rest_framework.urlpatterns import format_suffix_patterns

from shared.views import (
    AdminConfirmSessionView,
    AdminValidateSessionView,
    ConsentView,
    InitTestingDatabaseView,
    MailjetUnsubView,
    ResetTestingDatabaseView,
    SupportSuggestionView,
    AdminTypesenseView,
    AdminTokenView,
)
from urls import url_for_staging

urlpatterns = [
    url('maintainence/admin/token/', AdminTokenView.as_view(), name='admin_token'),
    url('typesense/', AdminTypesenseView.as_view(), name='typesense_admin_page'),
    url_for_staging(
        r'^tests/database/init/?$',
        InitTestingDatabaseView.as_view(),
        name='init_testing_database',
    ),
    url_for_staging(
        r'^tests/database/reset/?$',
        ResetTestingDatabaseView.as_view(),
        name='reset_testing_database',
    ),
    url(r'^mailjet/unsub/?$', MailjetUnsubView.as_view(), name='mailjet_unsubscribe'),
    # TEMP: While Mailjet unsubscribe doesn't work
    url(
        r'^weekly/unsubscribe/?$',
        TemplateView.as_view(template_name='weekly-unsubscribe.html'),
        name='weekly_unsubscribe',
    ),
    # Admin as User Auth Validate Token
    url(
        r'^admin/auth/validate$',
        AdminValidateSessionView.as_view(),
        name='admin_validate_session',
    ),
    # # WebApp - Confirm Admin Session as User
    url(
        r'^admin/auth/confirm/(?P<hash>[-:\w]+)/$',
        AdminConfirmSessionView.as_view(),
        name='admin_confirm_session',
    ),
    # User suggestions sent to Admin via email
    url(
        r'^support/suggestion/?$',
        SupportSuggestionView.as_view(),
        name='support_suggestion',
    ),
    # Consents
    url(r'^consent/?$', ConsentView.as_view(), name='consent'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
