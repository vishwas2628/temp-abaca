from django.core.management.base import BaseCommand
from allauth.utils import get_user_model
from datetime import date
from mailjet_rest import Client
from django.core import signing
from shared import mailjet
import os


class Command(BaseCommand):
    help = 'Script to register users'

    def handle(self, *args, **options):
        users = get_user_model().objects.all()
        usersToRegister = []
        for user in users:
            if not user.has_usable_password():

                key = signing.dumps(obj=user.id)
                base_url = os.getenv('APP_BASE_URL', 'viral.vilcap.com')
                link = 'https://' + base_url + '/auth/enlist/' + key
                mailjet.sendRecoverUser(email, user, link)
