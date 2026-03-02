from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from grid import views

urlpatterns = [
    # Categories
    url(r'^categories/$', views.CategoryList.as_view(), name="get_categories"),
    url(r"^categories/(?P<slug>\w+)/$",
        views.CategoryList.as_view(), name='get_categories_group'),
    url(r'^levels/$', views.LevelList.as_view(), name='get_levels'),
    url(r'^viral_level/$', views.ViralLevelCalculator.as_view(),
        name="calculate_viral_level"),
    url(r'^assessments/token/(?P<token>[-:\w]+)/?$',
        views.AssessmentToken.as_view(), name='get_assessment_token'),
    url(r'^assessments/latest/(?P<pk>[0-9]+)/?$',
        views.LatestAssessmentView.as_view(), name='get_latest_assessment'),
    url(r'^assessments/?$', views.CreateAssessmentView.as_view(),
        name='create_assessment'),

    # PDF Grid Generator
    url(r'^pdfgrid/(?P<company>[\w|\W]+)/(?P<overall_level>\d+)/(?P<team_level>\d+)/(?P<prob_level>\d+)/(?P<val_level>\d+)/(?P<prod_level>\d+)/(?P<mkt_level>\d+)/(?P<bizm_level>\d+)/(?P<scale_level>\d+)/(?P<exit_level>\d+)/?$', views.PdfGrid.as_view(), name='pdf_grid')
]

urlpatterns = format_suffix_patterns(urlpatterns)
