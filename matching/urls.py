from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from matching.views import (
    CreateOfferView, CriteriaWeightList, FinishedPendingSupporterView, InterestedCTAView, LatestResponseList,
    ListQuestionBundlesView, MatchingByCompanyView, MatchingCriteriaBySupporter, MatchingInterestedView,
    MatchingLoadingStateView, MatchingQuestionsForAdditionalCriteriaView, MatchingView, QuestionsList,
    RegisterPendingSupporterView, RegisterSupporterView, ResponseList, RetrieveMatchingScoresImpactView,
    SupportCategoriesTypes, SupporterListOrCreateAssessmentLinkView, SupportersTypesList, SupportersView,
    AlgorithmCalculatorSearchCompaniesView, AlgorithmCalculatorMatchingCriteriaView, QuestionAnswerResponseView)

urlpatterns = [
    url(r'^matching/responses/?$', ResponseList.as_view(), name='response_list'),
    url(r'^matching/responses/latest/?$',
        LatestResponseList.as_view(), name='response_list'),
    url(r'^matching/questions/?$', QuestionsList.as_view(), name='questions_list'),
    url(r'^matching/question-bundles/?$', ListQuestionBundlesView.as_view(), name='list_question_bundles'),
    url(r'^matching/questions-with-responses(?:/(?P<company_id>\d+))?/?$', QuestionAnswerResponseView.as_view(), name='questions_with_responses'),
    url(r'^matching/scores/?$', MatchingView.as_view(), name='matching_percentage'),
    url(r'^matching/scores/loading/?$',
        MatchingLoadingStateView.as_view(), name='matching_loading_state'),
    url(r'^matching/scores/(?P<company>\w+)/?$',
        MatchingByCompanyView.as_view(), name='matching_percentage_by_company'),
    url(r'matching/scores/(?P<company>\w+)/impact/?$',
        RetrieveMatchingScoresImpactView.as_view(), name="get_scores_impact"),
    url(r'^matching/interested/(?P<connection>\w+)?/?$',
        MatchingInterestedView.as_view(), name='matching_interested'),
    url(r'^matching/questions/additional-criteria/?$',
        MatchingQuestionsForAdditionalCriteriaView.as_view(), name="list_additional_criteria"),

    # Supporters.
    url(r'^supporterstypes/?$', SupportersTypesList.as_view(),
        name='supporters_type_list'),
    url(r'^supporters/register', RegisterSupporterView.as_view(),
        name="register_supporters"),
    url(r'^supporters/?(?P<pk>[0-9]+)?/?',
        SupportersView.as_view(), name="retrieve_or_update_supporter"),
    url(r'^supporter/affiliates/?',
        SupporterListOrCreateAssessmentLinkView.as_view(), name="list_or_create_supporter_affiliates"),

    # Pending Supporters
    url(r'^pending-supporter/register/?$', RegisterPendingSupporterView.as_view(),
        name="register_pending_supporter"),
    url(r'^pending-supporter/finished/?$', FinishedPendingSupporterView.as_view(),
        name="finished_pending_supporter"),

    # Offerings.
    url(r'^offering/categoriestypes/?$', SupportCategoriesTypes.as_view(),
        name='support_categories_types'),

    url(r'^offering/?(?P<pk>[0-9]\w+)?/?$', CreateOfferView.as_view(),
        name='support_categories_types'),

    # Criteria Weight.
    url(r'^criteriaweight/?$', CriteriaWeightList.as_view()),

    url(r'^matching/criteria/?$',
        MatchingCriteriaBySupporter.as_view(), name="retrieve_matching_criteria"),

    url(r'^interested/?$',
        InterestedCTAView.as_view(), name="register_interested_cta"),


    url(r'^algorithm-calculator/search-companies/?$',
        AlgorithmCalculatorSearchCompaniesView.as_view(), name="algorithm_calculator_search_companies"),
    url(r'^algorithm-calculator/matching-criteria/?$',
        AlgorithmCalculatorMatchingCriteriaView.as_view(), name="algorithm_calculator_matching_criteria")

]

urlpatterns = format_suffix_patterns(urlpatterns)
