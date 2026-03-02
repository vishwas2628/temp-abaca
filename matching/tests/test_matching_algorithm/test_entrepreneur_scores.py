from django.db import connection

from shared.utils import AbacaAPITestCase
from grid.models import Level
from grid.tests.factories import AssessmentFactory
from viral.tests.factories import UserProfileFactory, LocationFactory, SectorFactory
from matching.models import MatchingTotalScores, Question, QuestionType, CriteriaWeight, criteria_weight
from matching.tests.factories import SupporterFactory, ResponseFactory, CriteriaFactory


class TestEntrepreneurScores(AbacaAPITestCase):
    """
    Test calculated scores for an Entrepreneur only with:
    * 1 - Viral Level
    * 1.1 - With match
    * 1.2 - Without match

    * 2 - Location
    * 2.1 - With continent match
    * 2.2 - With country match
    * 2.3 - With city match
    * 2.4 - With region match
    * 2.5 - Without match

    * 3 - Sector
    * 3.1 - Single
    * 3.1.1 - With match
    * 3.1.2 - Without match
    * 3.2 - Multiple
    * 3.2.1 - With match
    * 3.2.2 - With partial match
    * 3.2.3 - Without match

    * 4 - Response
    * 4.1 - Single
    * 4.1.1 - Of type numeric
    * 4.1.1.1 - With match
    * 4.1.1.2 - Without match
    * 4.1.2 - Of type range
    * 4.1.2.1 - With match
    * 4.1.2.2 - Without match
    * 4.1.3 - Of type single select
    * 4.1.3.1 - With match
    * 4.1.3.2 - Without match
    * 4.1.4 - Of type multiple select
    * 4.1.4.1 - With match
    * 4.1.4.2 - Without match
    * 4.2 - Multiple (types)
    * 4.2.1 - With match
    * 4.2.2 - With partial match
    * 4.2.3 - Without match

    Test calculated scores for an Entrepreneur with:
    * 5 - Multiple criteria
    * 5.1 - With match
    * 5.2 - Without match
    * 5.3 - With partial match
    * 5.3.1 - On single value criteria
    * 5.3.2 - On multiple value criteria
    """
    fixtures = ['level_groups', 'category_groups', 'levels', 'categories', 'category_levels',
                'criteria_weights', 'profile_id_fields', 'question_types', 'question_categories',
                'questions', 'answers']

    VIRAL_LEVEL = 3
    LOCATION_CONTINENT = 'Europe'
    LOCATION_COUNTRY = 'Portugal'
    LOCATION_CITY = 'Porto'
    LOCATION_REGION = 'Porto District'

    def setUp(self):
        super().setUp()
        self.level = Level.objects.filter(value=self.VIRAL_LEVEL, group=2).first()
        self.entrepreneur_user_profile = UserProfileFactory()
        self.entrepreneur_company = self.entrepreneur_user_profile.company
        self.assessment = AssessmentFactory(level=self.level, user=self.entrepreneur_user_profile.user,
                                            evaluated=self.entrepreneur_user_profile.company)

    def _calculate_scores(self, functions=['level', 'sector', 'location', 'response']):
        refresh_query = "SELECT matching.refresh_{function}_score(_refresh_all := false, _company_id := {company_id});"
        with connection.cursor() as cursor:
            for function in functions:
                cursor.execute(refresh_query.format(function=function, company_id=self.entrepreneur_company.id))
            # Finally, refresh the final (total) scores:
            cursor.execute(refresh_query.format(function='total', company_id=self.entrepreneur_company.id))
            cursor.close()

    def test_calculated_scores_for_entrepreneur_viral_level_with_match(self):
        """1.1 - Test calculated scores for Entrepreneur only with Viral Level with match"""
        supporter = SupporterFactory(investing_level_range=[1, self.VIRAL_LEVEL])
        self._calculate_scores(['level'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_single_result = len(results) == 1
        matches_with_supporter = results.first().supporter_id == supporter.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_supporter)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_entrepreneur_viral_level_without_match(self):
        """1.2 - Test calculated scores for Entrepreneur only with Viral Level without match"""
        # Create Supporter with level range greater than the Entrepreneur viral level:
        SupporterFactory(investing_level_range=[self.VIRAL_LEVEL + 1, self.VIRAL_LEVEL + 3])
        self._calculate_scores(['level'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)

    def test_calculated_scores_for_entrepreneur_location_with_continent_match(self):
        """2.1 - Test calculated scores for Entrepreneur only with Location with continent match"""
        # Add location with same continent for both the Entrepreneur & Supporter
        common_location = LocationFactory(continent=self.LOCATION_CONTINENT)
        self.entrepreneur_company.locations.set([common_location])
        supporter = SupporterFactory()
        supporter.locations.set([common_location])

        self._calculate_scores(['location'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_single_result = len(results) == 1
        matches_with_supporter = results.first().supporter_id == supporter.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_supporter)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_entrepreneur_location_with_country_match(self):
        """2.2 - Test calculated scores for Entrepreneur only with Location with country match"""
        # Add location with same country for both the Entrepreneur & Supporter
        common_location = LocationFactory(country=self.LOCATION_COUNTRY)
        self.entrepreneur_company.locations.set([common_location])
        supporter = SupporterFactory()
        supporter.locations.set([common_location])

        self._calculate_scores(['location'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_single_result = len(results) == 1
        matches_with_supporter = results.first().supporter_id == supporter.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_supporter)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_entrepreneur_location_with_city_match(self):
        """2.3 - Test calculated scores for Entrepreneur only with Location with city match"""
        # Add location with same city for both the Entrepreneur & Supporter
        common_location = LocationFactory(city=self.LOCATION_CITY)
        self.entrepreneur_company.locations.set([common_location])
        supporter = SupporterFactory()
        supporter.locations.set([common_location])

        self._calculate_scores(['location'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_single_result = len(results) == 1
        matches_with_supporter = results.first().supporter_id == supporter.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_supporter)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_entrepreneur_location_with_region_match(self):
        """2.4 - Test calculated scores for Entrepreneur only with Location with region match"""
        # Add location with same region for both the Entrepreneur & Supporter
        common_location = LocationFactory(region=self.LOCATION_REGION)
        self.entrepreneur_company.locations.set([common_location])
        supporter = SupporterFactory()
        supporter.locations.set([common_location])

        self._calculate_scores(['location'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_single_result = len(results) == 1
        matches_with_supporter = results.first().supporter_id == supporter.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_supporter)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_entrepreneur_location_without_match(self):
        """2.5 - Test calculated scores for Entrepreneur only with Location without match"""
        # Add different locations for the Entrepreneur & Supporter
        entrep_location = LocationFactory(city=self.LOCATION_CITY)
        self.entrepreneur_company.locations.set([entrep_location])
        supporter = SupporterFactory()
        supporter_location = LocationFactory(city='Gotham')
        supporter.locations.set([supporter_location])

        self._calculate_scores(['location'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)

    def test_calculated_scores_for_entrepreneur_single_sector_with_match(self):
        """3.1.1 - Test calculated scores for Entrepreneur only with a single Sector with match"""
        # Add same sector for both the Entrepreneur & Supporter
        common_sector = SectorFactory()
        self.entrepreneur_company.sectors.set([common_sector])
        supporter = SupporterFactory()
        supporter.sectors.set([common_sector])

        self._calculate_scores(['sector'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_single_result = len(results) == 1
        matches_with_supporter = results.first().supporter_id == supporter.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_supporter)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_entrepreneur_single_sector_without_match(self):
        """3.1.2 - Test calculated scores for Entrepreneur only with a single Sector without match"""
        # Add different sector for the Entrepreneur & Supporter
        entrep_sector = SectorFactory()
        self.entrepreneur_company.sectors.set([entrep_sector])
        supporter = SupporterFactory()
        supporter_sector = SectorFactory()
        supporter.sectors.set([supporter_sector])

        self._calculate_scores(['sector'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)

    def test_calculated_scores_for_entrepreneur_multiple_sectors_with_match(self):
        """3.2.1 - Test calculated scores for Entrepreneur only with multiple Sectors with match"""
        # Add same sectors for both the Entrepreneur & Supporter
        common_sectors = SectorFactory.create_batch(size=3)
        self.entrepreneur_company.sectors.set(common_sectors)
        supporter = SupporterFactory()
        supporter.sectors.set(common_sectors)

        self._calculate_scores(['sector'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_single_result = len(results) == 1
        matches_with_supporter = results.first().supporter_id == supporter.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_supporter)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_entrepreneur_multiple_sectors_with_partial_match(self):
        """3.2.2 - Test calculated scores for Entrepreneur only with multiple Sectors with partial match"""
        # Add some common sectors for both the Entrepreneur & Supporter
        common_sectors = SectorFactory.create_batch(size=3)
        entrep_sector = SectorFactory()
        self.entrepreneur_company.sectors.set([entrep_sector, *common_sectors])
        supporter = SupporterFactory()
        supporter_sector = SectorFactory()
        supporter.sectors.set([supporter_sector, *common_sectors])

        self._calculate_scores(['sector'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_single_result = len(results) == 1
        matches_with_supporter = results.first().supporter_id == supporter.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_supporter)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_entrepreneur_multiple_sectors_without_match(self):
        """3.2.3 - Test calculated scores for Entrepreneur only with multiple Sectors without match"""
        # Add different sectors for the Entrepreneur & Supporter
        entrep_sectors = SectorFactory.create_batch(size=3)
        self.entrepreneur_company.sectors.set(entrep_sectors)
        supporter = SupporterFactory()
        supporter_sectors = SectorFactory.create_batch(size=3)
        supporter.sectors.set(supporter_sectors)

        self._calculate_scores(['sector'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)

    def test_calculated_scores_for_entrepreneur_single_response_type_numeric_with_match(self):
        """4.1.1.1 - Test calculated scores for Entrepreneur only with a single Response of type numeric with match"""
        # Add corresponding response/criteria for both the Entrepreneur & Supporter
        question = Question.objects.filter(question_type__type=QuestionType.NUMERIC).first()
        ResponseFactory(question=question, user_profile=self.entrepreneur_user_profile, value={"value": 50})
        supporter = SupporterFactory()
        relevant_criteria_weight = CriteriaWeight.objects.filter(value__gt=0).first()
        CriteriaFactory(question=question, supporter=supporter,
                        criteria_weight=relevant_criteria_weight, desired={"min": 0, "max": 100})

        self._calculate_scores(['response'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_single_result = len(results) == 1
        matches_with_supporter = results.first().supporter_id == supporter.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_supporter)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_entrepreneur_single_response_type_numeric_without_match(self):
        """4.1.1.2 - Test calculated scores for Entrepreneur only with a single Response of type numeric without match"""
        # Add mismatching response/criteria for both the Entrepreneur & Supporter
        question = Question.objects.filter(question_type__type=QuestionType.NUMERIC).first()
        ResponseFactory(question=question, user_profile=self.entrepreneur_user_profile, value={"value": 70})
        supporter = SupporterFactory()
        relevant_criteria_weight = CriteriaWeight.objects.filter(value__gt=0).first()
        CriteriaFactory(question=question, supporter=supporter,
                        criteria_weight=relevant_criteria_weight, desired={"min": 15, "max": 45})

        self._calculate_scores(['response'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)

    def test_calculated_scores_for_entrepreneur_single_response_type_range_with_match(self):
        """4.1.2.1 - Test calculated scores for Entrepreneur only with a single Response of type range with match"""
        # Add corresponding response/criteria for both the Entrepreneur & Supporter
        question = Question.objects.filter(question_type__type=QuestionType.RANGE).first()
        ResponseFactory(question=question, user_profile=self.entrepreneur_user_profile, value={"min": 20, "max": 60})
        supporter = SupporterFactory()
        relevant_criteria_weight = CriteriaWeight.objects.filter(value__gt=0).first()
        CriteriaFactory(question=question, supporter=supporter,
                        criteria_weight=relevant_criteria_weight, desired={"value": 20})

        self._calculate_scores(['response'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_single_result = len(results) == 1
        self.assertTrue(has_single_result)
        matches_with_supporter = results.first().supporter_id == supporter.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(matches_with_supporter)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_entrepreneur_single_response_type_range_without_match(self):
        """4.1.2.2 - Test calculated scores for Entrepreneur only with a single Response of type range without match"""
        # Add mismatching response/criteria for both the Entrepreneur & Supporter
        question = Question.objects.filter(question_type__type=QuestionType.RANGE).first()
        ResponseFactory(question=question, user_profile=self.entrepreneur_user_profile, value={"value": 70})
        supporter = SupporterFactory()
        relevant_criteria_weight = CriteriaWeight.objects.filter(value__gt=0).first()
        CriteriaFactory(question=question, supporter=supporter,
                        criteria_weight=relevant_criteria_weight, desired={"min": 15, "max": 45})

        self._calculate_scores(['response'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)

    def test_calculated_scores_for_entrepreneur_single_response_type_single_select_with_match(self):
        """4.1.3.1 - Test calculated scores for Entrepreneur only with a single Response of type single select with match"""
        # Add corresponding response/criteria for both the Entrepreneur & Supporter
        question = Question.objects.prefetch_related('answer_set').filter(
            question_type__type=QuestionType.SINGLE_SELECT).first()
        response = ResponseFactory(question=question, user_profile=self.entrepreneur_user_profile)
        response.answers.set([question.answer_set.first()])
        supporter = SupporterFactory()
        relevant_criteria_weight = CriteriaWeight.objects.filter(value__gt=0).first()
        criteria = CriteriaFactory(question=question, supporter=supporter, criteria_weight=relevant_criteria_weight)
        criteria.answers.set([question.answer_set.first()])

        self._calculate_scores(['response'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_single_result = len(results) == 1
        self.assertTrue(has_single_result)
        matches_with_supporter = results.first().supporter_id == supporter.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(matches_with_supporter)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_entrepreneur_single_response_type_single_select_without_match(self):
        """4.1.3.2 - Test calculated scores for Entrepreneur only with a single Response of type single select without match"""
        # Add mismatching response/criteria for both the Entrepreneur & Supporter
        question = Question.objects.prefetch_related('answer_set').filter(
            question_type__type=QuestionType.SINGLE_SELECT).first()
        response = ResponseFactory(question=question, user_profile=self.entrepreneur_user_profile)
        response.answers.set([question.answer_set.first()])
        supporter = SupporterFactory()
        relevant_criteria_weight = CriteriaWeight.objects.filter(value__gt=0).first()
        criteria = CriteriaFactory(question=question, supporter=supporter, criteria_weight=relevant_criteria_weight)
        criteria.answers.set([question.answer_set.last()])

        self._calculate_scores(['response'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)

    def test_calculated_scores_for_entrepreneur_single_response_type_multiple_select_with_match(self):
        """4.1.4.1 - Test calculated scores for Entrepreneur only with a single Response of type multiple select with match"""
        # Add corresponding response/criteria for both the Entrepreneur & Supporter
        question = Question.objects.prefetch_related('answer_set').filter(
            question_type__type=QuestionType.MULTI_SELECT).first()
        response = ResponseFactory(question=question, user_profile=self.entrepreneur_user_profile)
        response.answers.set(question.answer_set.all())
        supporter = SupporterFactory()
        relevant_criteria_weight = CriteriaWeight.objects.filter(value__gt=0).first()
        criteria = CriteriaFactory(question=question, supporter=supporter, criteria_weight=relevant_criteria_weight)
        criteria.answers.set(question.answer_set.all())

        self._calculate_scores(['response'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_single_result = len(results) == 1
        self.assertTrue(has_single_result)
        matches_with_supporter = results.first().supporter_id == supporter.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(matches_with_supporter)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_entrepreneur_single_response_type_multiple_select_without_match(self):
        """4.1.4.2 - Test calculated scores for Entrepreneur only with a single Response of type multiple select without match"""
        # Add mismatching response/criteria for both the Entrepreneur & Supporter
        question = Question.objects.prefetch_related('answer_set').filter(
            question_type__type=QuestionType.MULTI_SELECT).first()
        answers_list = list(question.answer_set.all())
        response = ResponseFactory(question=question, user_profile=self.entrepreneur_user_profile)
        response.answers.set([answers_list[0], answers_list[1]])
        supporter = SupporterFactory()
        relevant_criteria_weight = CriteriaWeight.objects.filter(value__gt=0).first()
        criteria = CriteriaFactory(question=question, supporter=supporter, criteria_weight=relevant_criteria_weight)
        criteria.answers.set([answers_list[-1]])

        self._calculate_scores(['response'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)

    def test_calculated_scores_for_entrepreneur_multiple_response_types_with_match(self):
        """4.2.1 - Test calculated scores for Entrepreneur only with multiple Response types with match"""
        # Grab all question types (even those that aren't part of the calculated scores: date & free response)
        date_question = Question.objects.filter(question_type__type=QuestionType.DATE).first()
        range_question = Question.objects.filter(question_type__type=QuestionType.RANGE).first()
        numeric_question = Question.objects.filter(question_type__type=QuestionType.NUMERIC).first()
        free_text_question = Question.objects.filter(question_type__type=QuestionType.FREE_RESPONSE).first()
        single_select_question = Question.objects.prefetch_related(
            'answer_set').filter(question_type__type=QuestionType.SINGLE_SELECT).first()
        multi_select_question = Question.objects.prefetch_related(
            'answer_set').filter(question_type__type=QuestionType.MULTI_SELECT).first()

        # Add responses for the Entrepreneur that will correspond to the Supporter:
        ResponseFactory(question=numeric_question,
                        user_profile=self.entrepreneur_user_profile, value={"value": 50})
        ResponseFactory(
            question=range_question, user_profile=self.entrepreneur_user_profile, value={"min": 5, "max": 80})
        ResponseFactory(
            question=date_question, user_profile=self.entrepreneur_user_profile, value={"date": "2022-01-01"})
        ResponseFactory(question=free_text_question,
                        user_profile=self.entrepreneur_user_profile, value={"text": "Lorem"})
        single_select_response = ResponseFactory(
            question=single_select_question, user_profile=self.entrepreneur_user_profile)
        single_select_response.answers.set([single_select_question.answer_set.first()])
        multi_select_response = ResponseFactory(question=multi_select_question,
                                                user_profile=self.entrepreneur_user_profile)
        multi_select_response.answers.set(multi_select_question.answer_set.all())

        # Add criteria for the Supporter that will correspond to the Entrepreneur:
        supporter = SupporterFactory()
        CriteriaFactory(question=numeric_question, supporter=supporter, desired={"min": 0, "max": 100})
        CriteriaFactory(question=range_question, supporter=supporter, desired={"value": 50})
        CriteriaFactory(question=date_question, supporter=supporter, desired={"date": "2022-01-01"})
        CriteriaFactory(question=free_text_question, supporter=supporter, desired={"text": "Lorem"})
        single_select_criteria = CriteriaFactory(question=single_select_question, supporter=supporter)
        single_select_criteria.answers.set([single_select_question.answer_set.first()])
        multi_select_criteria = CriteriaFactory(question=multi_select_question, supporter=supporter)
        multi_select_criteria.answers.set(multi_select_question.answer_set.all())

        self._calculate_scores(['response'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_single_result = len(results) == 1
        self.assertTrue(has_single_result)
        matches_with_supporter = results.first().supporter_id == supporter.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(matches_with_supporter)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_entrepreneur_multiple_response_types_with_partial_match(self):
        """4.2.2 - Test calculated scores for Entrepreneur only with multiple Response types with partial match"""
        # Grab all question types (even those that aren't part of the calculated scores: date & free response)
        date_question = Question.objects.filter(question_type__type=QuestionType.DATE).first()
        range_question = Question.objects.filter(question_type__type=QuestionType.RANGE).first()
        numeric_question = Question.objects.filter(question_type__type=QuestionType.NUMERIC).first()
        free_text_question = Question.objects.filter(question_type__type=QuestionType.FREE_RESPONSE).first()
        single_select_question = Question.objects.prefetch_related(
            'answer_set').filter(question_type__type=QuestionType.SINGLE_SELECT).first()
        multi_select_question = Question.objects.prefetch_related(
            'answer_set').filter(question_type__type=QuestionType.MULTI_SELECT).first()

        # Add responses for the Entrepreneur that will correspond to the Supporter:
        ResponseFactory(question=numeric_question,
                        user_profile=self.entrepreneur_user_profile, value={"value": 50})
        ResponseFactory(
            question=range_question, user_profile=self.entrepreneur_user_profile, value={"min": 5, "max": 80})

        # Add responses for the Entrepreneur that will not correspond to the Supporter:
        single_select_response = ResponseFactory(
            question=single_select_question, user_profile=self.entrepreneur_user_profile)
        single_select_response.answers.set([single_select_question.answer_set.first()])
        multi_select_response = ResponseFactory(question=multi_select_question,
                                                user_profile=self.entrepreneur_user_profile)
        multi_select_response.answers.set([multi_select_question.answer_set.first()])

        # Add criteria for the Supporter that will correspond to the Entrepreneur:
        supporter = SupporterFactory()
        relevant_criteria_weight = CriteriaWeight.objects.filter(value__gt=0).first()
        CriteriaFactory(question=numeric_question, supporter=supporter,
                        criteria_weight=relevant_criteria_weight, desired={"min": 0, "max": 100})
        CriteriaFactory(question=range_question, supporter=supporter,
                        criteria_weight=relevant_criteria_weight, desired={"value": 50})

        # Add criteria for the Supporter that will not correspond to the Entrepreneur:
        single_select_criteria = CriteriaFactory(
            question=single_select_question, supporter=supporter, criteria_weight=relevant_criteria_weight,)
        single_select_criteria.answers.set([single_select_question.answer_set.last()])
        multi_select_criteria = CriteriaFactory(question=multi_select_question,
                                                supporter=supporter, criteria_weight=relevant_criteria_weight,)
        multi_select_criteria.answers.set([multi_select_question.answer_set.last()])

        self._calculate_scores(['response'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_single_result = len(results) == 1
        self.assertTrue(has_single_result)
        matches_with_supporter = results.first().supporter_id == supporter.pk
        is_partial_match = results.first().max_score_percentil < 100
        self.assertTrue(matches_with_supporter)
        self.assertTrue(is_partial_match)

    def test_calculated_scores_for_entrepreneur_multiple_response_types_without_match(self):
        """4.2.3 - Test calculated scores for Entrepreneur only with multiple Response types without match"""
        # Grab all question types (even those that aren't part of the calculated scores: date & free response)
        date_question = Question.objects.filter(question_type__type=QuestionType.DATE).first()
        range_question = Question.objects.filter(question_type__type=QuestionType.RANGE).first()
        numeric_question = Question.objects.filter(question_type__type=QuestionType.NUMERIC).first()
        free_text_question = Question.objects.filter(question_type__type=QuestionType.FREE_RESPONSE).first()
        single_select_question = Question.objects.prefetch_related(
            'answer_set').filter(question_type__type=QuestionType.SINGLE_SELECT).first()
        multi_select_question = Question.objects.prefetch_related(
            'answer_set').filter(question_type__type=QuestionType.MULTI_SELECT).first()

        # Add responses for the Entrepreneur that will not correspond to the Supporter:
        ResponseFactory(question=numeric_question,
                        user_profile=self.entrepreneur_user_profile, value={"value": 150})
        ResponseFactory(
            question=range_question, user_profile=self.entrepreneur_user_profile, value={"min": 100, "max": 200})
        ResponseFactory(
            question=date_question, user_profile=self.entrepreneur_user_profile, value={"date": "2022-01-01"})
        ResponseFactory(question=free_text_question,
                        user_profile=self.entrepreneur_user_profile, value={"text": "Lorem"})
        single_select_response = ResponseFactory(
            question=single_select_question, user_profile=self.entrepreneur_user_profile)
        single_select_response.answers.set([single_select_question.answer_set.first()])
        multi_select_response = ResponseFactory(question=multi_select_question,
                                                user_profile=self.entrepreneur_user_profile)
        multi_select_response.answers.set([multi_select_question.answer_set.first()])

        # Add criteria for the Supporter that will not correspond to the Entrepreneur:
        supporter = SupporterFactory()
        CriteriaFactory(question=numeric_question, supporter=supporter, desired={"min": 0, "max": 100})
        CriteriaFactory(question=range_question, supporter=supporter, desired={"value": 50})
        CriteriaFactory(question=date_question, supporter=supporter, desired={"date": "2022-01-01"})
        CriteriaFactory(question=free_text_question, supporter=supporter, desired={"text": "Lorem"})
        single_select_criteria = CriteriaFactory(question=single_select_question, supporter=supporter)
        single_select_criteria.answers.set([single_select_question.answer_set.last()])
        multi_select_criteria = CriteriaFactory(question=multi_select_question, supporter=supporter)
        multi_select_criteria.answers.set([multi_select_question.answer_set.last()])

        self._calculate_scores(['response'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)

    def test_calculated_scores_for_entrepreneur_multiple_criteria_with_match(self):
        """5.1 - Test calculated scores for Entrepreneur with multiple criteria with match"""
        # Set multiple Entrepreneur criteria:
        common_sector = SectorFactory()
        self.entrepreneur_company.sectors.set([common_sector])
        common_location = LocationFactory(city=self.LOCATION_CITY)
        self.entrepreneur_company.locations.set([common_location])
        numeric_question = Question.objects.filter(question_type__type=QuestionType.NUMERIC).first()
        ResponseFactory(question=numeric_question,
                        user_profile=self.entrepreneur_user_profile, value={"value": 50})

        # Set multiple Supporter criteria that matches Entrepreneur:
        supporter = SupporterFactory(investing_level_range=[1, self.VIRAL_LEVEL])
        supporter.sectors.set([common_sector])
        supporter.locations.set([common_location])
        CriteriaFactory(question=numeric_question, supporter=supporter, desired={"min": 0, "max": 50})

        self._calculate_scores(['level', 'sector', 'location', 'response'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_single_result = len(results) == 1
        matches_with_supporter = results.first().supporter_id == supporter.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_supporter)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_entrepreneur_multiple_criteria_without_match(self):
        """5.2 - Test calculated scores for Entrepreneur with multiple criteria without match"""
        # Set multiple Entrepreneur criteria:
        entrep_sector = SectorFactory()
        self.entrepreneur_company.sectors.set([entrep_sector])
        entrep_location = LocationFactory(city=self.LOCATION_CITY)
        self.entrepreneur_company.locations.set([entrep_location])
        numeric_question = Question.objects.filter(question_type__type=QuestionType.NUMERIC).first()
        ResponseFactory(question=numeric_question,
                        user_profile=self.entrepreneur_user_profile, value={"value": 10})

        # Set multiple Supporter criteria that matches Entrepreneur:
        supporter = SupporterFactory(investing_level_range=[self.VIRAL_LEVEL + 1, self.VIRAL_LEVEL + 2])
        supporter_sector = SectorFactory()
        supporter_location = LocationFactory(city=self.LOCATION_COUNTRY)
        supporter.sectors.set([supporter_sector])
        supporter.locations.set([supporter_location])
        CriteriaFactory(question=numeric_question, supporter=supporter, desired={"min": 20, "max": 30})

        self._calculate_scores(['level', 'sector', 'location', 'response'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)

    def test_calculated_scores_for_entrepreneur_multiple_criteria_single_value_with_partial_match(self):
        """5.3.1 - Test calculated scores for Entrepreneur with multiple criteria having single values with partial match"""
        # Set multiple Entrepreneur criteria:
        numeric_question = Question.objects.filter(question_type__type=QuestionType.NUMERIC).first()
        entrep_sector = SectorFactory()
        self.entrepreneur_company.sectors.set([entrep_sector])
        entrep_location = LocationFactory(city=self.LOCATION_CITY)
        self.entrepreneur_company.locations.set([entrep_location])
        ResponseFactory(question=numeric_question,
                        user_profile=self.entrepreneur_user_profile, value={"value": 50})

        # Set multiple Supporter criteria that partially matches Entrepreneur:
        supporter = SupporterFactory(investing_level_range=[1, self.VIRAL_LEVEL])
        supporter_sector = SectorFactory()
        supporter_location = LocationFactory(city=self.LOCATION_COUNTRY)
        supporter.sectors.set([supporter_sector])
        supporter.locations.set([supporter_location])
        relevant_criteria_weight = CriteriaWeight.objects.filter(value__gt=0).first()
        CriteriaFactory(question=numeric_question, supporter=supporter,
                        criteria_weight=relevant_criteria_weight, desired={"min": 0, "max": 50})

        self._calculate_scores(['level', 'sector', 'location', 'response'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_single_result = len(results) == 1
        self.assertTrue(has_single_result)
        matches_with_supporter = results.first().supporter_id == supporter.pk
        is_partial_match = results.first().max_score_percentil < 100
        self.assertTrue(matches_with_supporter)
        self.assertTrue(is_partial_match)

    def test_calculated_scores_for_entrepreneur_multiple_criteria_multi_value_with_partial_match(self):
        """5.3.2 - Test calculated scores for Entrepreneur with multiple criteria having multiple values with partial match"""
        # Set multiple Entrepreneur criteria:
        range_question = Question.objects.filter(question_type__type=QuestionType.RANGE).first()
        numeric_question = Question.objects.filter(question_type__type=QuestionType.NUMERIC).first()
        common_sectors = SectorFactory.create_batch(size=3)
        entrep_sector = SectorFactory()
        self.entrepreneur_company.sectors.set([entrep_sector, *common_sectors])
        common_location = LocationFactory(city=self.LOCATION_CITY)
        self.entrepreneur_company.locations.set([common_location])
        ResponseFactory(question=numeric_question,
                        user_profile=self.entrepreneur_user_profile, value={"value": 50})
        ResponseFactory(
            question=range_question, user_profile=self.entrepreneur_user_profile, value={"min": 10, "max": 30})

        # Set multiple Supporter criteria that partially matches Entrepreneur:
        supporter = SupporterFactory(investing_level_range=[1, self.VIRAL_LEVEL])
        supporter_sector = SectorFactory()
        supporter_location = LocationFactory(city=self.LOCATION_COUNTRY)
        supporter.sectors.set([supporter_sector, *common_sectors])
        supporter.locations.set([supporter_location])
        relevant_criteria_weight = CriteriaWeight.objects.filter(value__gt=0).first()
        CriteriaFactory(question=numeric_question, supporter=supporter,
                        criteria_weight=relevant_criteria_weight, desired={"min": 0, "max": 50})
        CriteriaFactory(question=range_question, supporter=supporter,
                        criteria_weight=relevant_criteria_weight, desired={"value": 50})

        self._calculate_scores(['level', 'sector', 'location', 'response'])
        results = MatchingTotalScores.objects.filter(company_id=self.entrepreneur_company.id)
        has_single_result = len(results) == 1
        self.assertTrue(has_single_result)
        matches_with_supporter = results.first().supporter_id == supporter.pk
        is_partial_match = results.first().max_score_percentil < 100
        self.assertTrue(matches_with_supporter)
        self.assertTrue(is_partial_match)
