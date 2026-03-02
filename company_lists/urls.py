from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from company_lists import views

urlpatterns = [
    # Company Lists
    # Create or List (owned lists)
    url(r'^user/company-lists/?$', views.ListOrCreateCompanyListsView.as_view(),
        name='list_or_create_company_lists'),

    # List (shared lists)
    url(r'^user/company-lists/shared/?$', views.ListSharedCompanyListsView.as_view(),
        name='list_shared_company_lists'),
    url(r'^user/company-lists/shared/(?P<uid>[0-9\w]+)/?$', views.RemoveUserFromSharedCompanyListsView.as_view(),
        name='remove_shared_company_list'),

    # Company List
    # Retrieve, Update or Delete (owned list)
    url(r'^user/company-lists/(?P<uid>[0-9\w]+)/?$', views.RetrieveUpdateOrDeleteCompanyListView.as_view(),
        name='retrieve_update_or_delete_company_lists'),
    # Fetch Company List companies
    url(r'^user/company-lists/(?P<uid>[0-9\w]+)/companies/?$', views.FetchCompanyListCompanies.as_view(),
        name='list_company_list_companies'),
    # Fetch Company List invited users
    url(r'user/company-lists/(?P<list_uid>[0-9\w]+)/users/?', views.FetchCompanyListUsersView.as_view(),
        name='list_company_list_users'),

    # Fetch Company Lists for a given Company (admin-only)
    url(r'^companies/(?P<pk>[0-9]+)/company-lists/?$', views.CompanyListChoicesView.as_view(),
        name='company_list_choices'),

    # Fetch Processes
    url(r'user/processes/?$', views.ListProcessesView.as_view()),

    # Fetch Process Details
    url(r'user/processes/(?P<process_id>[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12})/?$', views.RetrieveProcessView.as_view()),

    # Fetch Process Demographic Stats
    url(r'user/processes/(?P<process_id>[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12})/demographic-stats/?$', views.RetrieveProcessDemographicStatsView.as_view(), name='process_demographic_stats'),

    # Fetch Milestone Planner Stats
    url(r'^milestone-progress/base/(?P<uid>[0-9\w]+)?$', views.MilestoneProgressBaseView.as_view(),
        name='milestone_progress_base'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
