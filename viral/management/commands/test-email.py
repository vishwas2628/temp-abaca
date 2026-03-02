from django.core.management.base import BaseCommand
from shared import mailjet
from allauth.utils import get_user_model
from viral.models import Affiliate
from grid.models import Assessment


class Command(BaseCommand):

    def handle(self, *args, **options):
        # email = 'filipesantos@wearepixelmatters.com'
        # user = get_user_model().objects.get(id=80)
        # affiliate = Affiliate.objects.get(id=1)
        # link = 'https://example.com'

        # mailjet.sendVerifyAccountEmail(email, user, link)
        # mailjet.sendForgotPasswordEmail(email, user, link)
        # mailjet.sendSuccessCreatingAccount(email, user)
        # mailjet.sendRecoverUser(email, user, link)
        # mailjet.sendEntrepreneurCompletedAssessment(email, user, link)
        # mailjet.sendNotificationToAffiliate(email, user, affiliate, link)
