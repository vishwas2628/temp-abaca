from django.conf.urls import url  # pyright: ignore[reportAttributeAccessIssue]

from sdg.views import sdg_data
from sdg.views import getReport
from sdg.views import sdg_submissions
from sdg.views import generate_reports 
from sdg.views import update_job_status
from sdg.views import SaveImpactAndRatingView
from sdg.views import SDGAffiliateProgramEntryListAPIView

urlpatterns = [
    url(r'^sdg/question_options$', sdg_data, name='sdg-data'),
    url(r'^sdg/affiliate-submissions$', sdg_submissions, name='sdg-submissions'),
    url(r"^sdg/generate-reports/?$", generate_reports, name='generate_sdg_reports'),
    url(r"^sdg/update-job-status/?$", update_job_status, name='update_job_status'),
    url(r"^sdg/report/?$", getReport, name='get_sdg_report'),
    url(
        r'^sdg/affiliate-program-entries/(?P<affiliate_id>\d+)/?$',
        SDGAffiliateProgramEntryListAPIView.as_view(),
        name='sdg-affiliate-program-entries',
    ),
    url(
        r'^sdg/affiliate-program-entries/(?P<affiliate_id>\d+)/company/(?P<company_id>\d+)/?$',
        SDGAffiliateProgramEntryListAPIView.as_view(),
        name='sdg-affiliate-program-entries-company',
    ),
    url(
        r'^sdg/affiliate-program-entries/(?P<affiliate_id>\d+)/?$',
        SDGAffiliateProgramEntryListAPIView.as_view(),
        name='sdg-affiliate-program-entries',
    ),
    url(
        r'^sdg/save-impact-and-rating$',
        SaveImpactAndRatingView.as_view(),
        name='save-impact-and-rating',
    ),
]
