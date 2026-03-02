import datetime
import random

from django.contrib.auth import get_user_model

from grid.models import Assessment, CategoryLevel, Category
from grid.tests.factories import AssessmentFactory
from milestone_planner.models.milestone import Milestone
from shared.utils import AbacaAPITestCase
from viral.models import UserProfile, Company
from viral.tests.factories import UserProfileFactory


class TestAssessmentModel(AbacaAPITestCase):
    """
    1 - Test syncing an assessment with a recently:
    * 1.1 - Created milestone
    * 1.1.1 - Without latest assessment
    * 1.1.2 - Being complete
    * 1.1.3 - Being incomplete
    * 1.2 - Updated milestone
    * 1.2.1 - Being complete
    * 1.2.2 - Being incomplete
    * 1.3 - Deleted milestone
    * 1.3.1 - Being complete
    * 1.3.2 - Being incomplete
    """
    fixtures = ['level_groups', 'category_groups', 'levels', 'categories', 'category_levels']

    def setUp(self):
        super().setUp()
        self.categories = Category.objects.all()
        self.upgrade_category, self.downgrade_category = random.sample(list(self.categories), 2)
        self.assessment = AssessmentFactory(with_user_profile=True,
                                            data=[
                                                {'category': self.upgrade_category.pk, 'level': 3},
                                                {'category': self.downgrade_category.pk, 'level': 6}])
        self.company = Company.objects.get(pk=self.assessment.evaluated)
        self.user = get_user_model().objects.get(id=self.assessment.user)
        self.user_profile = UserProfile.objects.get(user=self.user, company=self.company)

    def test_sync_assessment_with_created_milestone_without_latest_assessment(self):
        """1.1.1 - Test syncing an assessment with a recently created milestone without latest assessment"""
        user_profile = UserProfileFactory()
        category_levels = CategoryLevel.objects.all()
        random_category_level = random.choice(list(category_levels))
        Milestone.objects.create(
            state=Milestone.COMPLETED_STATE, user_profile=user_profile, category_level=random_category_level,
            evidence_published=True, date_of_completion=datetime.datetime.today())
        has_not_created_an_assessment = Assessment.objects.filter(user=user_profile.user.pk).count() == 0
        self.assertTrue(has_not_created_an_assessment)

    def test_sync_assessment_with_created_milestone_being_complete(self):
        """1.1.2 - Test syncing an assessment with a recently created milestone being complete"""
        category_level = CategoryLevel.objects.filter(category=self.upgrade_category, level__value__gt=3).first()
        Milestone.objects.create(
            state=Milestone.COMPLETED_STATE, user_profile=self.user_profile, category_level=category_level,
            evidence_published=True, date_of_completion=datetime.datetime.today())
        has_created_assessment_with_upgrade = Assessment.objects.filter(
            user=self.user.pk,
            data__contains=[{"level": category_level.level.value, "category": category_level.category.pk}]).exists()
        self.assertTrue(has_created_assessment_with_upgrade)

    def test_sync_assessment_with_created_milestone_being_incomplete(self):
        """1.1.3 - Test syncing an assessment with a recently created milestone being incomplete"""
        category_level = CategoryLevel.objects.filter(category=self.upgrade_category, level__value__gt=3).first()
        Milestone.objects.create(
            state=Milestone.TO_BE_PLANNED_STATE, user_profile=self.user_profile, category_level=category_level,
            target_date=datetime.datetime.today())
        has_not_created_an_assessment = Assessment.objects.filter(
            user=self.user.pk,
            data__contains=[{"level": category_level.level.value, "category": category_level.category.pk}]).count() == 0
        self.assertTrue(has_not_created_an_assessment)

    def test_sync_assessment_with_updated_milestone_being_complete(self):
        """1.2.1 - Test syncing an assessment with a recently updated milestone being complete"""
        category_level = CategoryLevel.objects.filter(category=self.upgrade_category, level__value__gt=3).first()

        # 1 - Create milestone with initial incomplete state:
        created_milestone = Milestone.objects.create(
            state=Milestone.IN_PROGRESS_STATE, user_profile=self.user_profile, category_level=category_level,
            date_of_completion=datetime.datetime.today())

        # 2 - Update milestone to a complete state:
        created_milestone.evidence_published = True
        created_milestone.save()

        has_created_assessment_with_upgrade = Assessment.objects.filter(
            user=self.user.pk,
            data__contains=[{"level": category_level.level.value, "category": category_level.category.pk}]).count() == 1
        self.assertTrue(has_created_assessment_with_upgrade)

    def test_sync_assessment_with_updated_milestone_being_incomplete(self):
        """1.2.2 - Test syncing an assessment with a recently updated milestone being incomplete"""
        category_level = CategoryLevel.objects.filter(category=self.downgrade_category, level__value=6).first()

        # 1 - Grab existing completed milestone
        existing_milestone = Milestone.objects.filter(
            state=Milestone.COMPLETED_STATE, user_profile=self.user_profile, category_level=category_level).first()

        # 2 - Update milestone to a incomplete state:
        existing_milestone.evidence_published = False
        existing_milestone.save()

        has_created_assessment_with_downgrade = Assessment.objects.filter(
            user=self.user.pk,
            data__contains=[{"level": 5, "category": category_level.category.pk}]).count() == 1
        self.assertTrue(has_created_assessment_with_downgrade)

    def test_sync_assessment_with_deleted_milestone_being_complete(self):
        """1.3.1 - Test syncing an assessment with a recently deleted milestone being complete"""
        category_level = CategoryLevel.objects.filter(category=self.downgrade_category, level__value=6).first()
        existing_milestone = Milestone.objects.filter(
            state=Milestone.COMPLETED_STATE, user_profile=self.user_profile, category_level=category_level).first()
        existing_milestone.delete()
        Assessment.objects.sync_with_milestone(milestone=existing_milestone, created=False)
        has_created_assessment_with_downgrade = Assessment.objects.filter(
            user=self.user.pk,
            data__contains=[{"level": 5, "category": category_level.category.pk}]).count() == 1
        self.assertTrue(has_created_assessment_with_downgrade)

    def test_sync_assessment_with_deleted_milestone_being_incomplete(self):
        """1.3.2 - Test syncing an assessment with a recently deleted milestone being incomplete"""
        category_level = CategoryLevel.objects.filter(category=self.downgrade_category, level__value__gt=6).first()
        incomplete_milestone = Milestone.objects.create(
            state=Milestone.TO_BE_PLANNED_STATE, user_profile=self.user_profile, category_level=category_level,
            target_date=datetime.datetime.today())
        incomplete_milestone.delete()

        has_not_created_an_assessment = Assessment.objects.filter(
            user=self.user.pk,
            data__contains=[{"level": category_level.level.value, "category": category_level.category.pk}]).count() == 0
        self.assertTrue(has_not_created_an_assessment)
