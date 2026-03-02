from allauth.account.adapter import DefaultAccountAdapter
from shared.mailjet import sendVerifyAccountEmail
from viral.models import UserProfile, Company
import os


class CustomAccountAdapter(DefaultAccountAdapter):

    def confirm_email(self, request, email_address):
        """
        Marks the email address as confirmed on the db
        """
        email_address.verified = True
        email_address.set_as_primary()
        email_address.save()

    def send_mail(self, template_prefix, email, context):
        if 'key' in context and 'user' in context:
            link = 'https://' + \
                os.getenv('APP_BASE_URL', 'viral.vilcap.com') + \
                '/auth/verify-account/' + context.get('key')
            try:
                user = UserProfile.objects.get(user=context.get('user'))
            except UserProfile.DoesNotExist:
                return
            sendVerifyAccountEmail(email, context.get('user'), link)
