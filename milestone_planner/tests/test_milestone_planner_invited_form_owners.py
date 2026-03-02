from grid.models.level import Level
from grid.tests.factories import AssessmentFactory
from matching.tests.factories import SupporterFactory
from shared.utils import AbacaAPITestCase
from viral.models import AffiliateProgramEntry
from viral.tests.factories import AffiliateFactory, UserProfileFactory
from milestone_planner.models import UserInvitation


class TestMilestonePlannerInvitedFormOwners(AbacaAPITestCase):
    fixtures = ['levels']

    def setUp(self):
        super().setUp()
        self.entrepreneur = UserProfileFactory()
        self.milestone_planner = self.entrepreneur.company.milestone_planners.first()
        self.affiliate = AffiliateFactory()
        self.affiliate.company = UserProfileFactory().company
        self.affiliate.supporters.add(SupporterFactory(), SupporterFactory())
        self.affiliate_program_entry = AffiliateProgramEntry.objects.create(
            affiliate=self.affiliate,
            user_profile=self.entrepreneur,
            assessment=AssessmentFactory(
                user=self.entrepreneur.user,
                evaluated=self.entrepreneur.company,
            level=Level.objects.filter(value=3, group=2).first(),
            ),
        )

    def test_invite_affiliate_company_upon_submission(self):
        self.assertTrue(
            UserInvitation.objects.filter(
                milestoneplanner=self.milestone_planner, userprofile=self.affiliate.company.company_profile, is_form_owner=True
            ).exists()
        )

    def test_invite_affiliate_supporters_upon_submission(self):
        self.assertTrue(
            UserInvitation.objects.filter(
                milestoneplanner=self.milestone_planner, userprofile=self.affiliate.supporters.all()[0].user_profile, is_form_owner=True
            ).exists()
        )
        self.assertTrue(
            UserInvitation.objects.filter(
                milestoneplanner=self.milestone_planner, userprofile=self.affiliate.supporters.all()[1].user_profile, is_form_owner=True
            ).exists()
        )
