from django.db import connection

from grid.models import Level
from grid.tests.factories import AssessmentFactory
from matching.models import MatchingTotalScores, CriteriaWeight, Question, QuestionType
from matching.tests.factories import CriteriaFactory, ResponseFactory, SupporterFactory
from shared.utils import AbacaAPITestCase
from viral.tests.factories import SectorFactory, UserProfileFactory, LocationFactory


class TestSupporterScores(AbacaAPITestCase):
    """
    Test calculated scores for a Supporter with:
    * 1 - Investing Level Range
    * 1.1 - Having lowest criteria weight
    * 1.1.1 - With match
    * 1.1.2 - Without match
    * 1.2 - Having middle criteria weight
    * 1.2.1 - With match
    * 1.2.2 - Without match
    * 1.3 - Having highest criteria weight
    * 1.3.1 - With match
    * 1.3.2 - Without match

    * 2 - Sectors of Interest
    * 2.1 - Having lowest criteria weight
    * 2.1.1 - With match
    * 2.1.2 - Without match
    * 2.2 - Having middle criteria weight
    * 2.2.1 - With match
    * 2.2.2 - Without match
    * 2.3 - Having highest criteria weight
    * 2.3.1 - With match
    * 2.3.2 - Without match

    * 3 - Locations of Interest
    * 3.1 - Having lowest criteria weight
    * 3.1.1 - With match
    * 3.1.2 - Without match
    * 3.2 - Having middle criteria weight
    * 3.2.1 - With match
    * 3.2.2 - Without match
    * 3.3 - Having highest criteria weight
    * 3.3.1 - With match
    * 3.3.2 - Without match

    * 4 - Criteria (Response)
    * 4.1 - Having lowest criteria weight
    * 4.1.1 - With match
    * 4.1.2 - Without match
    * 4.2 - Having middle criteria weight
    * 4.2.1 - With match
    * 4.2.2 - Without match
    * 4.3 - Having highest criteria weight
    * 4.3.1 - With match
    * 4.3.2 - Without match
    """
    fixtures = ['level_groups', 'category_groups', 'levels', 'categories', 'category_levels',
                'criteria_weights', 'profile_id_fields', 'question_types', 'question_categories',
                'questions', 'answers']

    INVESTING_LEVEL_RANGE = [3, 6]
    MATCH_LEVEL = 3
    MISMATCH_LEVEL = 8

    def setUp(self):
        super().setUp()
        self.supporter = SupporterFactory(investing_level_range=self.INVESTING_LEVEL_RANGE)

    def _calculate_scores(self, functions=['level', 'sector', 'location', 'response']):
        refresh_query = "SELECT matching.refresh_{function}_score(_refresh_all := false, _supporter_id := {supporter_id});"
        with connection.cursor() as cursor:
            for function in functions:
                cursor.execute(refresh_query.format(function=function, supporter_id=self.supporter.id))
            # Finally, refresh the final (total) scores:
            cursor.execute(refresh_query.format(function='total', supporter_id=self.supporter.id))
            cursor.close()

    def test_calculated_scores_for_supporter_investing_level_range_low_weight_with_match(self):
        """1.1.1 - Test calculated scores for a Supporter with investing level range having lowest criteria weight with match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set Criteria Weight
        lowest_criteria_weight = CriteriaWeight.objects.order_by('value').first()
        self.supporter.level_weight = lowest_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['level'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_single_result = len(results) == 1
        matches_with_entrepreneur = results.first().company_id == entrepreneur_profile.company.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_entrepreneur)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_supporter_investing_level_range_low_weight_without_match(self):
        """1.1.2 - Test calculated scores for a Supporter with investing level range having lowest criteria weight without match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MISMATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set Criteria Weight
        lowest_criteria_weight = CriteriaWeight.objects.order_by('value').first()
        self.supporter.level_weight = lowest_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['level'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_single_result = len(results) == 1
        matches_with_entrepreneur = results.first().company_id == entrepreneur_profile.company.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_entrepreneur)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_supporter_investing_level_range_middle_weight_with_match(self):
        """1.2.1 - Test calculated scores for a Supporter with investing level range having middle criteria weight with match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set Criteria Weight
        middle_criteria_weight = CriteriaWeight.objects.exclude(value__lte=0).order_by('value').first()
        self.supporter.level_weight = middle_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['level'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_single_result = len(results) == 1
        matches_with_entrepreneur = results.first().company_id == entrepreneur_profile.company.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_entrepreneur)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_supporter_investing_level_range_middle_weight_without_match(self):
        """1.2.2 - Test calculated scores for a Supporter with investing level range having middle criteria weight without match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MISMATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set Criteria Weight
        middle_criteria_weight = CriteriaWeight.objects.exclude(value__lte=0).order_by('value').first()
        self.supporter.level_weight = middle_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['level'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)

    def test_calculated_scores_for_supporter_investing_level_range_high_weight_with_match(self):
        """1.3.1 - Test calculated scores for a Supporter with investing level range having highest criteria weight with match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set Criteria Weight
        highest_criteria_weight = CriteriaWeight.objects.order_by('-value').first()
        self.supporter.level_weight = highest_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['level'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_single_result = len(results) == 1
        matches_with_entrepreneur = results.first().company_id == entrepreneur_profile.company.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_entrepreneur)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_supporter_investing_level_range_high_weight_without_match(self):
        """1.3.2 - Test calculated scores for a Supporter with investing level range having highest criteria weight without match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MISMATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set Criteria Weight
        highest_criteria_weight = CriteriaWeight.objects.order_by('-value').first()
        self.supporter.level_weight = highest_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['level'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)

    def test_calculated_scores_for_supporter_sectors_low_weight_with_match(self):
        """2.1.1 - Test calculated scores for a Supporter with sectors of interest having lowest criteria weight with match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set sectors
        common_sector = SectorFactory()
        entrepreneur_profile.company.sectors.set([common_sector])
        self.supporter.sectors.set([common_sector])

        # Set Criteria Weight
        lowest_criteria_weight = CriteriaWeight.objects.order_by('value').first()
        self.supporter.sectors_weight = lowest_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['sector'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_single_result = len(results) == 1
        matches_with_entrepreneur = results.first().company_id == entrepreneur_profile.company.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_entrepreneur)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_supporter_sectors_low_weight_without_match(self):
        """2.1.2 - Test calculated scores for a Supporter with sectors of interest having lowest criteria weight without match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set sectors
        entrep_sector = SectorFactory()
        entrepreneur_profile.company.sectors.set([entrep_sector])
        supporter_sector = SectorFactory()
        self.supporter.sectors.set([supporter_sector])

        # Set Criteria Weight
        lowest_criteria_weight = CriteriaWeight.objects.order_by('value').first()
        self.supporter.sectors_weight = lowest_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['sector'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_single_result = len(results) == 1
        matches_with_entrepreneur = results.first().company_id == entrepreneur_profile.company.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_entrepreneur)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_supporter_sectors_middle_weight_with_match(self):
        """2.2.1 - Test calculated scores for a Supporter with sectors of interest having middle criteria weight with match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set sectors
        common_sector = SectorFactory()
        entrepreneur_profile.company.sectors.set([common_sector])
        self.supporter.sectors.set([common_sector])

        # Set Criteria Weight
        middle_criteria_weight = CriteriaWeight.objects.exclude(value__lte=0).order_by('value').first()
        self.supporter.sectors_weight = middle_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['sector'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_single_result = len(results) == 1
        matches_with_entrepreneur = results.first().company_id == entrepreneur_profile.company.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_entrepreneur)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_supporter_sectors_middle_weight_without_match(self):
        """2.2.2 - Test calculated scores for a Supporter with sectors of interest having middle criteria weight without match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set sectors
        entrep_sector = SectorFactory()
        entrepreneur_profile.company.sectors.set([entrep_sector])
        supporter_sector = SectorFactory()
        self.supporter.sectors.set([supporter_sector])

        # Set Criteria Weight
        middle_criteria_weight = CriteriaWeight.objects.exclude(value__lte=0).order_by('value').first()
        self.supporter.sectors_weight = middle_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['sector'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)

    def test_calculated_scores_for_supporter_sectors_high_weight_with_match(self):
        """2.3.1 - Test calculated scores for a Supporter with sectors of interest having highest criteria weight with match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set sectors
        common_sector = SectorFactory()
        entrepreneur_profile.company.sectors.set([common_sector])
        self.supporter.sectors.set([common_sector])

        # Set Criteria Weight
        highest_criteria_weight = CriteriaWeight.objects.order_by('-value').first()
        self.supporter.sectors_weight = highest_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['sector'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_single_result = len(results) == 1
        matches_with_entrepreneur = results.first().company_id == entrepreneur_profile.company.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_entrepreneur)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_supporter_sectors_high_weight_without_match(self):
        """2.3.2 - Test calculated scores for a Supporter with sectors of interest having highest criteria weight without match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set sectors
        entrep_sector = SectorFactory()
        entrepreneur_profile.company.sectors.set([entrep_sector])
        supporter_sector = SectorFactory()
        self.supporter.sectors.set([supporter_sector])

        # Set Criteria Weight
        highest_criteria_weight = CriteriaWeight.objects.order_by('-value').first()
        self.supporter.sectors_weight = highest_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['sector'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)

    def test_calculated_scores_for_supporter_locations_low_weight_with_match(self):
        """3.1.1 - Test calculated scores for a Supporter with locations of interest having lowest criteria weight with match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set locations
        common_location = LocationFactory()
        entrepreneur_profile.company.locations.set([common_location])
        self.supporter.locations.set([common_location])

        # Set Criteria Weight
        lowest_criteria_weight = CriteriaWeight.objects.order_by('value').first()
        self.supporter.locations_weight = lowest_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['location'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_single_result = len(results) == 1
        matches_with_entrepreneur = results.first().company_id == entrepreneur_profile.company.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_entrepreneur)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_supporter_locations_low_weight_without_match(self):
        """3.1.2 - Test calculated scores for a Supporter with locations of interest having lowest criteria weight without match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set locations
        entrep_location = LocationFactory(city='Porto')
        entrepreneur_profile.company.locations.set([entrep_location])
        supporter_location = LocationFactory(city='Lisbon')
        self.supporter.locations.set([supporter_location])

        # Set Criteria Weight
        lowest_criteria_weight = CriteriaWeight.objects.order_by('value').first()
        self.supporter.locations_weight = lowest_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['location'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_single_result = len(results) == 1
        matches_with_entrepreneur = results.first().company_id == entrepreneur_profile.company.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_entrepreneur)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_supporter_locations_middle_weight_with_match(self):
        """3.2.1 - Test calculated scores for a Supporter with locations of interest having middle criteria weight with match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set locations
        common_location = LocationFactory()
        entrepreneur_profile.company.locations.set([common_location])
        self.supporter.locations.set([common_location])

        # Set Criteria Weight
        middle_criteria_weight = CriteriaWeight.objects.exclude(value__lte=0).order_by('value').first()
        self.supporter.locations_weight = middle_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['location'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_single_result = len(results) == 1
        matches_with_entrepreneur = results.first().company_id == entrepreneur_profile.company.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_entrepreneur)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_supporter_locations_middle_weight_without_match(self):
        """3.2.2 - Test calculated scores for a Supporter with locations of interest having middle criteria weight without match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set locations
        entrep_location = LocationFactory(city='Porto')
        entrepreneur_profile.company.locations.set([entrep_location])
        supporter_location = LocationFactory(city='Lisbon')
        self.supporter.locations.set([supporter_location])

        # Set Criteria Weight
        middle_criteria_weight = CriteriaWeight.objects.exclude(value__lte=0).order_by('value').first()
        self.supporter.locations_weight = middle_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['location'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)

    def test_calculated_scores_for_supporter_locations_high_weight_with_match(self):
        """3.3.1 - Test calculated scores for a Supporter with locations of interest having highest criteria weight with match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set locations
        common_location = LocationFactory()
        entrepreneur_profile.company.locations.set([common_location])
        self.supporter.locations.set([common_location])

        # Set Criteria Weight
        highest_criteria_weight = CriteriaWeight.objects.order_by('-value').first()
        self.supporter.locations_weight = highest_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['location'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_single_result = len(results) == 1
        matches_with_entrepreneur = results.first().company_id == entrepreneur_profile.company.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_entrepreneur)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_supporter_locations_high_weight_without_match(self):
        """3.3.2 - Test calculated scores for a Supporter with locations of interest having highest criteria weight without match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Set locations
        entrep_location = LocationFactory(city='Porto')
        entrepreneur_profile.company.locations.set([entrep_location])
        supporter_location = LocationFactory(city='Lisbon')
        self.supporter.locations.set([supporter_location])

        # Set Criteria Weight
        highest_criteria_weight = CriteriaWeight.objects.order_by('-value').first()
        self.supporter.locations_weight = highest_criteria_weight
        self.supporter.save()

        # Calculate scores and assert results
        self._calculate_scores(['location'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)

    def test_calculated_scores_for_supporter_criteria_low_weight_with_match(self):
        """4.1.1 - Test calculated scores for a Supporter with criteria having lowest criteria weight with match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Grab lowest criteria weight
        lowest_criteria_weight = CriteriaWeight.objects.order_by('value').first()

        # Set numeric criteria/response
        numeric_question = Question.objects.filter(question_type__type=QuestionType.NUMERIC).first()
        ResponseFactory(question=numeric_question, user_profile=entrepreneur_profile, value={"value": 50})
        CriteriaFactory(question=numeric_question, supporter=self.supporter,
                        criteria_weight=lowest_criteria_weight, desired={"min": 0, "max": 100})

        # Set single select criteria/response
        single_select_question = Question.objects.prefetch_related(
            'answer_set').filter(question_type__type=QuestionType.SINGLE_SELECT).first()
        single_select_response = ResponseFactory(
            question=single_select_question, user_profile=entrepreneur_profile)
        single_select_response.answers.set([single_select_question.answer_set.first()])
        single_select_criteria = CriteriaFactory(
            question=single_select_question, supporter=self.supporter, criteria_weight=lowest_criteria_weight)
        single_select_criteria.answers.set([single_select_question.answer_set.first()])

        # Calculate scores and assert results
        self._calculate_scores(['response'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_single_result = len(results) == 1
        matches_with_entrepreneur = results.first().company_id == entrepreneur_profile.company.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_entrepreneur)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_supporter_criteria_low_weight_without_match(self):
        """4.1.2 - Test calculated scores for a Supporter with criteria having lowest criteria weight without match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Grab lowest criteria weight
        lowest_criteria_weight = CriteriaWeight.objects.order_by('value').first()

        # Set numeric criteria/response
        numeric_question = Question.objects.filter(question_type__type=QuestionType.NUMERIC).first()
        ResponseFactory(question=numeric_question, user_profile=entrepreneur_profile, value={"value": 100})
        CriteriaFactory(question=numeric_question, supporter=self.supporter,
                        criteria_weight=lowest_criteria_weight, desired={"min": 0, "max": 10})

        # Set single select criteria/response
        single_select_question = Question.objects.prefetch_related(
            'answer_set').filter(question_type__type=QuestionType.SINGLE_SELECT).first()
        single_select_response = ResponseFactory(
            question=single_select_question, user_profile=entrepreneur_profile)
        single_select_response.answers.set([single_select_question.answer_set.first()])
        single_select_criteria = CriteriaFactory(
            question=single_select_question, supporter=self.supporter, criteria_weight=lowest_criteria_weight)
        single_select_criteria.answers.set([single_select_question.answer_set.last()])

        # Calculate scores and assert results
        self._calculate_scores(['response'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_single_result = len(results) == 1
        matches_with_entrepreneur = results.first().company_id == entrepreneur_profile.company.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_entrepreneur)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_supporter_criteria_middle_weight_with_match(self):
        """4.2.1 - Test calculated scores for a Supporter with criteria having middle criteria weight with match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Grab middle criteria weight
        middle_criteria_weight = CriteriaWeight.objects.exclude(value__lte=0).order_by('value').first()

        # Set numeric criteria/response
        numeric_question = Question.objects.filter(question_type__type=QuestionType.NUMERIC).first()
        ResponseFactory(question=numeric_question, user_profile=entrepreneur_profile, value={"value": 50})
        CriteriaFactory(question=numeric_question, supporter=self.supporter,
                        criteria_weight=middle_criteria_weight, desired={"min": 0, "max": 100})

        # Set single select criteria/response
        single_select_question = Question.objects.prefetch_related(
            'answer_set').filter(question_type__type=QuestionType.SINGLE_SELECT).first()
        single_select_response = ResponseFactory(
            question=single_select_question, user_profile=entrepreneur_profile)
        single_select_response.answers.set([single_select_question.answer_set.first()])
        single_select_criteria = CriteriaFactory(
            question=single_select_question, supporter=self.supporter, criteria_weight=middle_criteria_weight)
        single_select_criteria.answers.set([single_select_question.answer_set.first()])

        # Calculate scores and assert results
        self._calculate_scores(['response'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_single_result = len(results) == 1
        matches_with_entrepreneur = results.first().company_id == entrepreneur_profile.company.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_entrepreneur)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_supporter_criteria_middle_weight_without_match(self):
        """4.2.2 - Test calculated scores for a Supporter with criteria having middle criteria weight without match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Grab middle criteria weight
        middle_criteria_weight = CriteriaWeight.objects.exclude(value__lte=0).order_by('value').first()

        # Set numeric criteria/response
        numeric_question = Question.objects.filter(question_type__type=QuestionType.NUMERIC).first()
        ResponseFactory(question=numeric_question, user_profile=entrepreneur_profile, value={"value": 100})
        CriteriaFactory(question=numeric_question, supporter=self.supporter,
                        criteria_weight=middle_criteria_weight, desired={"min": 0, "max": 10})

        # Set single select criteria/response
        single_select_question = Question.objects.prefetch_related(
            'answer_set').filter(question_type__type=QuestionType.SINGLE_SELECT).first()
        single_select_response = ResponseFactory(
            question=single_select_question, user_profile=entrepreneur_profile)
        single_select_response.answers.set([single_select_question.answer_set.first()])
        single_select_criteria = CriteriaFactory(
            question=single_select_question, supporter=self.supporter, criteria_weight=middle_criteria_weight)
        single_select_criteria.answers.set([single_select_question.answer_set.last()])

        # Calculate scores and assert results
        self._calculate_scores(['response'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)

    def test_calculated_scores_for_supporter_criteria_high_weight_with_match(self):
        """4.3.1 - Test calculated scores for a Supporter with criteria having highest criteria weight with match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Grab highest criteria weight
        highest_criteria_weight = CriteriaWeight.objects.order_by('-value').first()

        # Set numeric criteria/response
        numeric_question = Question.objects.filter(question_type__type=QuestionType.NUMERIC).first()
        ResponseFactory(question=numeric_question, user_profile=entrepreneur_profile, value={"value": 50})
        CriteriaFactory(question=numeric_question, supporter=self.supporter,
                        criteria_weight=highest_criteria_weight, desired={"min": 0, "max": 100})

        # Set single select criteria/response
        single_select_question = Question.objects.prefetch_related(
            'answer_set').filter(question_type__type=QuestionType.SINGLE_SELECT).first()
        single_select_response = ResponseFactory(
            question=single_select_question, user_profile=entrepreneur_profile)
        single_select_response.answers.set([single_select_question.answer_set.first()])
        single_select_criteria = CriteriaFactory(
            question=single_select_question, supporter=self.supporter, criteria_weight=highest_criteria_weight)
        single_select_criteria.answers.set([single_select_question.answer_set.first()])

        # Calculate scores and assert results
        self._calculate_scores(['response'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_single_result = len(results) == 1
        matches_with_entrepreneur = results.first().company_id == entrepreneur_profile.company.pk
        is_100_percent_match = results.first().max_score_percentil == 100
        self.assertTrue(has_single_result)
        self.assertTrue(matches_with_entrepreneur)
        self.assertTrue(is_100_percent_match)

    def test_calculated_scores_for_supporter_criteria_high_weight_without_match(self):
        """4.3.2 - Test calculated scores for a Supporter with criteria having highest criteria weight without match"""
        # Setup Entrepreneur
        entrepreneur_profile = UserProfileFactory()
        level = Level.objects.filter(value=self.MATCH_LEVEL, group=2).first()
        AssessmentFactory(level=level, user=entrepreneur_profile.user, evaluated=entrepreneur_profile.company)

        # Grab highest criteria weight
        highest_criteria_weight = CriteriaWeight.objects.order_by('-value').first()

        # Set numeric criteria/response
        numeric_question = Question.objects.filter(question_type__type=QuestionType.NUMERIC).first()
        ResponseFactory(question=numeric_question, user_profile=entrepreneur_profile, value={"value": 100})
        CriteriaFactory(question=numeric_question, supporter=self.supporter,
                        criteria_weight=highest_criteria_weight, desired={"min": 0, "max": 10})

        # Set single select criteria/response
        single_select_question = Question.objects.prefetch_related(
            'answer_set').filter(question_type__type=QuestionType.SINGLE_SELECT).first()
        single_select_response = ResponseFactory(
            question=single_select_question, user_profile=entrepreneur_profile)
        single_select_response.answers.set([single_select_question.answer_set.first()])
        single_select_criteria = CriteriaFactory(
            question=single_select_question, supporter=self.supporter, criteria_weight=highest_criteria_weight)
        single_select_criteria.answers.set([single_select_question.answer_set.last()])

        # Calculate scores and assert results
        self._calculate_scores(['response'])
        results = MatchingTotalScores.objects.filter(supporter_id=self.supporter.id)
        has_empty_results = len(results) == 0
        self.assertTrue(has_empty_results)
