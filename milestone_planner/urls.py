from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from milestone_planner import views

urlpatterns = [
    # Create or List (owned milestones)
    url(r'^milestones/?$', views.ListOrCreateMilestonesView.as_view(),
        name='list_or_create_milestones'),

    # Retrieve or Update (owned milestone)
    url(r'^milestones/(?P<uid>[0-9\w]+)/?$', views.RetrieveUpdateOrDeleteMilestoneView.as_view(),
        name='retrieve_update_or_delete_milestone'),

    # List milestone planners owned by the auth user
    url(r'^milestone-planners/?$',
        views.ListMilestonePlannersView.as_view(), name='list_milestone_planners'),

    # Retrieve a milestone planner (with milestones)
    url(r'^milestone-planners/(?P<uid>[0-9\w]+)/?$',
        views.RetrieveOrUpdateMilestonePlannerView.as_view(), name='retrieve_or_update_milestone_planner')
]

urlpatterns = format_suffix_patterns(urlpatterns)
