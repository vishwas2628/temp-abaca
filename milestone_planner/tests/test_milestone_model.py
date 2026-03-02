import random
import datetime
import factory

from django.db.models import Q
from django.db.models.signals import post_save

from grid.tests.factories import AssessmentFactory
from grid.models import CategoryLevel, Category
from matching.tests.factories import ResponseFactory
from milestone_planner.models.milestone import Milestone
from shared.models.unique_uid import random_uid
from shared.utils import AbacaAPITestCase
from viral.models.user_profile import UserProfile
from viral.tests.factories import UserProfileFactory


class TestMilestoneModel(AbacaAPITestCase):
    """
    1 - Test creating the initial milestones from existing assessments
    2 - Test syncing milestones from a newly created assessment:
    * 2.1 - Upgrading unexisting milestones
    * 2.2 - Upgrading incomplete milestones
    * 2.3 - Downgrading milestones
    * 2.3.1 - With a unselected level
    * 2.4 - Without any changes
    """
    fixtures = ['level_groups', 'category_groups', 'levels', 'categories',
                'category_levels', 'profile_id_fields', 'question_types', 'question_categories', 'questions']

    def test_creating_initial_milestones_from_existing_assessments(self):
        """1 - Test creating the initial milestones from all existing self-assessments"""
        # Disable assessment signals to make this test cover its usage on migrations.
        with factory.django.mute_signals(post_save):
            existing_assessments = AssessmentFactory.create_batch(size=10, with_user_profile=True)

        all_category_levels = CategoryLevel.objects.filter(category__group=2)
        all_levels_assessed = []

        for assessment in existing_assessments:
            # 1 - Add mandatory user profile pk to each assessment instance
            user_profile = UserProfile.objects.get(company__pk=assessment.evaluated)
            setattr(assessment, 'user_profile_pk', user_profile.pk)

            # 2 - Store each category level that will be reflected in milestones:
            for selection in assessment.data:
                assessed_category_levels = [
                    {'category_level_pk': category_level.pk, 'user_profile_pk': user_profile.pk}
                    for category_level in all_category_levels if category_level.level.value ==
                    selection.get('level') and category_level.category.pk == selection.get('category')]
                all_levels_assessed.extend(assessed_category_levels)

        # 3 - Call the milestone generator method:
        created_milestones = Milestone.objects.generate_from_assessments(assessments=existing_assessments)

        # 4 - Check if created milestones match every self-assessed category level:
        has_milestones_for_all_assessed_levels = any((
            next(
                (milestone.user_profile.pk ==
                 level_assessed['user_profile_pk']
                 and milestone.category_level.pk ==
                 level_assessed['category_level_pk']
                 for level_assessed in all_levels_assessed), None)
            for milestone in created_milestones))
        self.assertTrue(has_milestones_for_all_assessed_levels)

        # 5 - Check if all created milestones have the completed state:
        self.assertFalse(
            any(
                milestone.state != Milestone.COMPLETED_STATE or milestone.evidence_published is False
                for milestone in created_milestones))

    def test_sync_milestones_from_assessment_upgrading_unexisting_milestones(self):
        """2.1 - Test syncing milestones from a newly created self-assessment while upgrading unexisting milestones"""
        user_profile = UserProfileFactory()
        categories = Category.objects.filter(group=2)
        level_upgrade_category = random.choice(list(categories))

        # 1 - Build initial assessment:
        AssessmentFactory(
            user=user_profile.user, evaluated=user_profile.company,
            data=[{'category': level_upgrade_category.pk, 'level': 3}])

        # 2 - Change milestones initial state to test level upgrade:
        initial_milestones = Milestone.objects.filter(user_profile=user_profile)
        initial_milestones_to_be_upgraded = list(filter(
            lambda milestone: milestone.category_level.category == level_upgrade_category, initial_milestones))
        for milestone in initial_milestones_to_be_upgraded:
            milestone.date_of_completion = None
            milestone.evidence_published = False
            # 2.1 Set in-progress milestone:
            if milestone.category_level.level.value == 1:
                response = ResponseFactory()
                milestone.evidence.set([response])
            # 2.2 Set planned milestone:
            if milestone.category_level.level.value == 2:
                milestone.plan_published = True
            # 2.3 Set to be planned milestone:
            if milestone.category_level.level.value == 3:
                milestone.target_date = datetime.date.today()
            milestone.save()

        # 3 - Build new assessment:
        AssessmentFactory(
            user=user_profile.user, evaluated=user_profile.company,
            data=[{'category': level_upgrade_category.pk, 'level': 6}])

        # 4 - Check milestones from upgrade:
        has_created_milestones_upgraded = Milestone.objects.filter(
            state=Milestone.COMPLETED_STATE, evidence_published=True, category_level__category=level_upgrade_category,
            category_level__level__value__in=[4, 5, 6]).count() == 3
        has_published_in_progress_milestones = Milestone.objects.filter(
            state=Milestone.COMPLETED_STATE, evidence_published=True, category_level__level__value=1,
            category_level__category=level_upgrade_category).exists()
        has_all_existing_milestones_completed = Milestone.objects.filter(
            state=Milestone.COMPLETED_STATE, evidence_published=True,
            category_level__category=level_upgrade_category).count() == 6

        self.assertTrue(all([has_all_existing_milestones_completed,
                             has_created_milestones_upgraded, has_published_in_progress_milestones]))

    def test_sync_milestones_from_assessment_upgrading_incomplete_milestones(self):
        """2.2 - Test syncing milestones from a newly created self-assessment while upgrading incomplete milestones"""
        user_profile = UserProfileFactory()
        categories = Category.objects.filter(group=2)
        level_upgrade_category = random.choice(list(categories))

        # 1 - Add future (to-be-planned) milestone:
        future_category_level = CategoryLevel.objects.filter(category=level_upgrade_category, level__value=8).first()
        Milestone.objects.create(uid=random_uid(), category_level=future_category_level, user_profile=user_profile,
                                 target_date=datetime.date.today(), state=Milestone.TO_BE_PLANNED_STATE)

        # 2 - Build initial assessment:
        AssessmentFactory(
            user=user_profile.user, evaluated=user_profile.company,
            data=[{'category': level_upgrade_category.pk, 'level': 2}])

        # 3 - Create incomplete milestones to test level upgrade:
        in_progress_category_level, planned_category_level, to_be_planned_category_level = CategoryLevel.objects.filter(
            category=level_upgrade_category, level__value__in=[4, 5, 6])

        # TODO: Replace this with factories:
        Milestone.objects.bulk_create([
            # 3.1 Add in-progress milestone:
            Milestone(uid=random_uid(), category_level=in_progress_category_level,
                      user_profile=user_profile, date_of_completion=datetime.date.today(),
                      evidence_published=False, state=Milestone.IN_PROGRESS_STATE),
            # 3.2 Add planned milestone:
            Milestone(uid=random_uid(), category_level=planned_category_level,
                      user_profile=user_profile, strategy='abc', outcomes='abc', resources='abc',
                      finances_needed=0, target_date=datetime.date.today(), plan_published=True,
                      state=Milestone.PLANNED_STATE),
            # 3.3 Add to-be-planned milestone:
            Milestone(uid=random_uid(), category_level=to_be_planned_category_level, user_profile=user_profile,
                      target_date=datetime.date.today(), state=Milestone.TO_BE_PLANNED_STATE),
        ])

        # 3 - Build new assessment:
        AssessmentFactory(
            user=user_profile.user, evaluated=user_profile.company,
            data=[{'category': level_upgrade_category.pk, 'level': 6}])

        # 4 - Check milestones from upgrade:
        has_created_milestones_upgraded = Milestone.objects.filter(
            user_profile=user_profile, state=Milestone.COMPLETED_STATE, evidence_published=True,
            category_level__category=level_upgrade_category, category_level__level__value=6).exists()
        has_completed_incomplete_milestones = Milestone.objects.filter(
            user_profile=user_profile, state=Milestone.COMPLETED_STATE, evidence_published=True,
            category_level__category=level_upgrade_category, category_level__level__value__in=[4, 5, 6]).count() == 3
        has_kept_future_milestone = Milestone.objects.filter(
            user_profile=user_profile, state=Milestone.TO_BE_PLANNED_STATE,
            category_level__category=level_upgrade_category, category_level__level__value=8).exists()

        self.assertTrue(has_created_milestones_upgraded)
        self.assertTrue(has_completed_incomplete_milestones)
        self.assertTrue(has_kept_future_milestone)

    def test_sync_milestones_from_assessment_downgrading_milestones(self):
        """2.3 - Test syncing milestones from a newly created self-assessment while downgrading milestones"""
        user_profile = UserProfileFactory()
        categories = Category.objects.filter(group=2)
        single_level_downgrade_category, multi_level_downgrade_category = random.sample(list(categories), 2)

        # 1 - Build initial assessment:
        AssessmentFactory(
            user=user_profile.user, evaluated=user_profile.company,
            data=[
                {'category': single_level_downgrade_category.pk, 'level': 6},
                {'category': multi_level_downgrade_category.pk, 'level': 8},
            ])

        # 2 - Change milestones initial state to test level downgrade:
        initial_milestones_to_be_downgraded = Milestone.objects.filter(
            user_profile=user_profile, category_level__category=multi_level_downgrade_category)
        for milestone in initial_milestones_to_be_downgraded:
            # 2.1 Add evidence on level 4:
            if milestone.category_level.level.value == 4:
                response = ResponseFactory()
                milestone.evidence.set([response])
            # 2.2 Add published plan on level 5:
            if milestone.category_level.level.value == 5:
                milestone.plan_published = True
                milestone.strategy = 'abc'
                milestone.outcomes = 'abc'
                milestone.resources = 'abc'
                milestone.finances_needed = 0
                milestone.target_date = datetime.datetime.today()
            # 2.3 Add incomplete plan on level 6:
            if milestone.category_level.level.value == 6:
                milestone.target_date = datetime.datetime.today()
            milestone.save()

        # 3 - Build new assessment:
        AssessmentFactory(
            user=user_profile.user, evaluated=user_profile.company,
            data=[
                {'category': single_level_downgrade_category.pk, 'level': 5},
                {'category': multi_level_downgrade_category.pk, 'level': 3},
            ])

        # 4 - Check milestones from downgrade:
        has_unpublished_completed_milestones = Milestone.objects.filter(
            user_profile=user_profile, evidence_published=False,
            category_level__category=multi_level_downgrade_category).filter(
                Q(category_level__level__value=4, state=Milestone.IN_PROGRESS_STATE) |
                Q(category_level__level__value=5, state=Milestone.PLANNED_STATE) |
                Q(category_level__level__value=6, state=Milestone.TO_BE_PLANNED_STATE)).count() == 3
        has_deleted_self_assessed_milestones = Milestone.objects.filter(
            user_profile=user_profile).filter(
            Q(category_level__level__value__in=[7, 8],
              category_level__category=multi_level_downgrade_category) |
            Q(category_level__level__value=6, category_level__category=single_level_downgrade_category)).count() == 0
        has_kept_milestones_from_selected_levels = Milestone.objects.filter(
            user_profile=user_profile, state=Milestone.COMPLETED_STATE).filter(
            Q(category_level__level__value__in=[1, 2, 3],
              category_level__category=multi_level_downgrade_category) |
            Q(
                category_level__level__value__in=[1, 2, 3, 4, 5],
                category_level__category=single_level_downgrade_category)).count() == 8

        self.assertTrue(has_unpublished_completed_milestones)
        self.assertTrue(has_deleted_self_assessed_milestones)
        self.assertTrue(has_kept_milestones_from_selected_levels)

    def test_sync_milestones_from_assessment_downgrading_with_unselected_level(self):
        """2.3.1 - Test syncing milestones from self-assessment while downgrading milestones with a unselected level"""
        user_profile = UserProfileFactory()
        random_category = Category.objects.filter(group=2).first()

        # 1 - Build initial assessment:
        AssessmentFactory(
            user=user_profile.user, evaluated=user_profile.company,
            data=[
                {'category': random_category.pk, 'level': 5}
            ])

        # 2 - Build assessment with unselected level:
        AssessmentFactory(
            user=user_profile.user, evaluated=user_profile.company,
            data=[
                {'category': random_category.pk, 'level': None}
            ])

        has_deleted_all_milestones = Milestone.objects.filter(
            user_profile=user_profile, category_level__category=random_category).count() == 0
        self.assertTrue(has_deleted_all_milestones)

    def test_sync_milestones_from_assessment_without_changes(self):
        """2.4 - Test syncing milestones from self-assessment without changes"""
        user_profile = UserProfileFactory()
        random_category = Category.objects.filter(group=2).first()

        # 1 - Build initial assessment:
        initial_assessment = AssessmentFactory(
            user=user_profile.user, evaluated=user_profile.company,
            data=[{'category': random_category.pk, 'level': 3}])

        has_created_initial_milestones = Milestone.objects.filter(
            user_profile=user_profile, category_level__category=random_category,
            category_level__level__value__in=[1, 2, 3],
            evidence_published=True, date_of_completion=initial_assessment.created_at,
            state=Milestone.COMPLETED_STATE).count() == 3
        self.assertTrue(has_created_initial_milestones)

        # 2 - Build exact same assessment:
        AssessmentFactory(
            user=user_profile.user, evaluated=user_profile.company,
            data=[{'category': random_category.pk, 'level': 3}])

        has_kept_milestones_unchanged = Milestone.objects.filter(
            user_profile=user_profile, category_level__category=random_category,
            category_level__level__value__in=[1, 2, 3],
            evidence_published=True, date_of_completion=initial_assessment.created_at,
            state=Milestone.COMPLETED_STATE).count() == 3
        self.assertTrue(has_kept_milestones_unchanged)
