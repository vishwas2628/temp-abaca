from django.urls import path
from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from rest_auth.views import LoginView, LogoutView

from viral import views
from viral.jet_admin_affiliate import CustomAdminAuth, AffiliateView

urlpatterns = [
    # Authentication
    url(r'^auth/login$', views.CustomLoginView.as_view(), name='rest_login'),
    url(r'^auth/logout$', LogoutView.as_view(), name='rest_login'),
    url(r'^auth/validate$', views.ValidateSessionView.as_view(), name='validate_session'),

    # Workaround to avoid using the configurations used by rest-auth
    url(
        r'^rest-auth/registration/account-email-verification-sent/$',
        views.django_rest_auth_null,
        name='account_email_verification_sent',
    ),

    # Users
    url(
        r'^user/register-with-assessment$',
        views.UserRegistrationWithAssessmentView.as_view(),
        name="register_user_assessment",
    ),
    url(r'^user/register', views.RegisterUserView.as_view(), name="register_user"),
    url(r'^user/email/update', views.UpdateEmail.as_view(), name="update_email"),
    url(r'^user/email/confirm/(?P<key>[-:\w]+)/$', views.ConfirmEmail.as_view(), name='account_confirm_email'),
    url(r'^user/recover$', views.RecoverUser.as_view(), name="recover_user"),
    url(r'^user/recover/(?P<key>[-:\w]+)$', views.RetrieveUserFromKey.as_view(), name='retrieve_user'),
    url(r'^user/password/change$', views.ChangePassword.as_view(), name="change_password"),
    url(r'^user/password/reset$', views.ResetPasswordView.as_view(), name='reset_password'),
    url(r'^user/password/reset/verify$', views.VerifyResetPasswordView.as_view(), name='verify_reset_password'),
    url(r'^user/password/reset/send$', views.SendResetPasswordEmailView.as_view(), name='send_reset_password'),
    url(
        r'^user/resend-verification-email/?$', views.ResendEmailVerification.as_view(), name="resend_verification_email"
    ),
    url(r'^user/metadata/?$', views.UserMetadataListView.as_view()),

    # Pending User -> User registed on Question Bundle modal.
    url(r'^pending-user/register', views.PrimaryRegisterView.as_view(), name="register_pending_user"),
    url(r'^pending-user/update', views.PendingUserUpdateView.as_view(), name="update_pending_user"),
    url(
        r'^pending-user/password', views.PendingUserCreatePasswordView.as_view(), name="register_pending_user_password"
    ),
    url(
        r'^pending-user/self_assessment',
        views.PendingUserSelfAssessmentRegisterView.as_view(),
        name="self_assessment_pending_user",
    ),

    # Affiliate Programs
    # Pending Users
    url(
        r'^pending-user/program/assessment',
        views.PendingUserProgramAssessmentRegisterView.as_view(),
        name="program_pending_user_assessment",
    ),
    url(
        r'^pending-user/program/question-bundles',
        views.PendingUserQuestionBundlesRegisterView.as_view(),
        name="program_pending_user_question_bundles",
    ),

    # Notify Affiliate if Pending User does not complete registration
    url(
        r'^pending-user/program/finished',
        views.PendingUserFinishedProgramView.as_view(),
        name="program_pending_user_finished",
    ),

    # Registered Users
    url(r'^program/assessment', views.ProgramAssessmentRegisterView.as_view(), name="program_auth_user"),
    url(r'^program/question-bundles', views.ProgramQuestionBundlesRegisterView.as_view(), name="program_auth_user"),

    # Affiliates
    url(r'^affiliates/$', views.AffiliateList.as_view(), name="get_affiliates"),
    url(r"^affiliates/((?P<pk>[0-9]+)|(?P<slug__iexact>[\w'-]+))/?$", views.Affiliate.as_view(), name='get_affiliate'),
    url(
        r"^affiliates/(?P<pk>[0-9]+)/question-bundles/?$",
        views.AffiliateQuestionBundles.as_view(),
        name='get_affiliate_question_bundles',
    ),
    url(
        r"^affiliates/supporter/default/program/?$",
        views.AffiliateSupporterDefault.as_view(),
        name='get_supporter_affiliate_default',
    ),
    url(
        r"^affiliates/supporter/((?P<pk>[0-9]+)|(?P<slug__iexact>[\w'-]+))/?$",
        views.AffiliateSupporterView.as_view(),
        name='get_supporter_affiliate',
    ),
    url(
        r"^affiliates/(?P<pk>[0-9]+)/regenerate-spreadsheet/?$",
        views.RegenerateAffiliateSpreadsheetView.as_view(),
        name='regenerate_affiliate_spreadsheet',
    ),

    # Affiliate Supporter Program
    url(
        r'^affiliate/supporter/program/submissions/?$',
        views.CreateAffiliateSupporterProgramSubmissionView.as_view(),
        name="submit_affiliate_supporter_program",
    ),
    url(
        r'^affiliate/supporter/program/submissions/(?P<uid>[a-z0-9]+)/?$',
        views.RetrieveAffiliateSupporterProgramSubmissionView.as_view(),
        name="retrieve_affiliate_supporter_program",
    ),

    # Affiliate Submissions
    url(
        r'^affiliate-program-submissions/?$',
        views.AffiliateProgramEntryListView.as_view(),
        name="list_affiliate_program_entries",
    ),
    url(
        r'^affiliate-program-submissions/(?P<uid>[a-z0-9]+)/?$',
        views.AffiliateProgramEntryDetailView.as_view(),
        name="get_affiliate_program_entry",
    ),
     
    # Company
    url(r'^companies/search/?', views.CompanySearchView.as_view(), name='company_search'),
    url(r'^companies/((?P<pk>[0-9]+)|(?P<access_hash>\w+))/$', views.CompanyView.as_view(), name='retrieve_company'),
    url(
        r"^companies/(?P<pk>[0-9]+)/assessments/?$",
        views.CompanyAssessmentsView.as_view(),
        name="retrieve_company_assessments",
    ),

    # User profile
    url(r'^userprofiles/?$', views.ListUserProfilesView.as_view(), name='list_user_profiles'),
    url(r'^userprofiles/(?P<pk>[0-9]+)/$', views.RetrieveUserProfileView.as_view(), name='retrieve_user_profile'),

    # Sectors
    url(r'^sectors/$', views.SectorList.as_view(), name="get_sectors"),
    url(r'^sector-groups/$', views.SectorGroupsList.as_view(), name="get_sector_groups"),
    url(
        r'^sector-groups/sectors/?$', views.SectorGroupsListWithSectors.as_view(), name="get_sector_groups_with_sectors"
    ),

    # Locations
    url(r'^location-search/$', views.LocationSearch.as_view(), name="search_locations"),
     
    # Misc.
    url(r'^self_assessment', views.SelfAssessmentRegisterView.as_view(), name="self_assessment"),
    
    # Vendors
    url(r'^vendor/self-assessment', views.VendorRegisterView.as_view(), name="vendor_assessment"),

    # Custom affiliate submissions endpoint
    url(
        r'^vendor/affiliates/(?P<affiliate_id>[0-9]+)/submissions/(?P<pk>[0-9]+)/?$',
        views.VendorAffiliateSubmissions.as_view(),
        name='get_affiliates_submissions',
    ),
    url(
        r'^vendor/affiliates/(?P<affiliate_id>[0-9]+)/submissions/?$',
        views.VendorAffiliateSubmissions.as_view(),
        name='get_affiliates_submissions',
    ),

    # Custom entrepreneurs & supporters list endpoint
    url(r'^vendor/entrepreneurs/?', views.VendorEntrepreneursListView.as_view(), name='vendor_list_entrepreneurs'),
    url(r'^vendor/supporters/?', views.VendorSupportersListView.as_view(), name='vendor_list_supporters'),

    # Supporters.
    url(r'^request-viral-level-range', views.SupportersLevelRange.as_view(), name="request-viral-level-range"),

    # Networks
    url(r'^network/$', views.NetworkList.as_view(), name="get_network"),
    url(r'^network/(?P<pk>[0-9]+)/members/?$', views.NetworkMembersView.as_view(), name="get_network_members"),
    url(r'^network/(?P<pk>[0-9]+)/metrics/?$', views.NetworkMetricsView.as_view(), name="get_network_metrics"),

    # Users Guest
    url(r'^users-guest', views.UsersGuestView.as_view(), name="users-guest"),

    # Team Members
    url(r'^team-members/?$', views.TeamMembersView.as_view(), name="team_members"),

    # Demographic composition of team members in a list of companies
    url(
        r'^demographic-composition/?',
        views.FetchListDemographicCompositionView.as_view(),
        name='fetch_demographic_composition',
    ),

    # Affiliate Submission Drafts
    url(
        r'^affiliate-submission-drafts/?$',
        views.AffiliateSubmissionDraftListView.as_view(),
        name="affiliate_submission_drafts",
    ),
    url(
        r"^affiliate-submission-drafts/((?P<pk>[0-9]+)|(?P<slug__iexact>[\w'-]+))/?$",
        views.AffiliateSubmissionDraftView.as_view(),
        name="affiliate_submission_draft",
    ),

    # User's Affiliate Submissions
    url(r'^affiliate-submissions/?$', views.AffiliateSubmissionsView.as_view(), name='affiliate_submissions'),

    # Supporter owned affiliates submissions
    url(
        r'^supporter-owned-affiliates-submissions/?$',
        views.SupporterOwnedAffiliatesSubmissionsView.as_view(),
        name='supporter_owned_affiliates_submissions',
    ),

    # Subscriptions
    url(r'^subscription/?$', views.SubscriptionView.as_view(), name='subscription'),
    url(r'^chargebee/portal/?$', views.ChargebeePortalView.as_view(), name='chargebee_portal'),
    url(r'^chargebee/checkout/?$', views.ChargebeeCheckoutView.as_view(), name='chargebee_checkout'),

    # JetAdmin Integration
    url(r'^admin/auth/login$', CustomAdminAuth.as_view(), name='admin_auth_login'),
    url(r'^viral/affiliate/create$', AffiliateView.as_view(), name='create_affiliate'),

]

urlpatterns = format_suffix_patterns(urlpatterns)
