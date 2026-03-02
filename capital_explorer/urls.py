from django.conf.urls import url

from capital_explorer.views import ListSubmissionView, RetrieveSubmissionView, PatchSubmissionView, CapitalExplorerView

urlpatterns = [
    url(r'capital-explorer/?$', CapitalExplorerView.as_view(), name='capital_explorer_index'),
    
    # Used by logged in user to retrieve its own Capital Explorer Submission,
    # or create a new one if none exists.
    url(r'capital-explorer/submission/?$', ListSubmissionView.as_view()),

    # Used by logged in user to update its own Capital Explorer Submission.
    url(
        r'capital-explorer/submission/(?P<pk>[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12})/?$',
        PatchSubmissionView.as_view(),
    ),

    # Used by visitors (guests or logged in users) to retrieve
    # another user's Capital Explorer Submission.
    url(
        r'capital-explorer/submission/(?P<uid>[0-9\w]+)/?$',
        RetrieveSubmissionView.as_view(),
    ),
]
