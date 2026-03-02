import os
from django.db.models.signals import m2m_changed

from company_lists.models import CompanyList
from viral.models import UserProfile
from shared.mailjet.mailjet import sendEmailWithoutTemplate


def invited_users_added(sender, **kwargs):
    """
    Send invitation email for users that were invited to a Company List
    """
    action = kwargs.get('action', None)
    instance = kwargs.get('instance', None)
    pk_set = kwargs.get('pk_set', None)

    if not action or action != 'post_add' or not instance or not pk_set:
        return

    users_to_be_invited = UserProfile.objects.filter(pk__in=list(pk_set))
    has_passcode = bool(instance.passcode)
    requirements = "link and passcode" if has_passcode else "link"
    list_url = 'https://' + os.getenv('APP_BASE_URL', 'my.abaca.app') + '/lists/%s' % instance.uid
    access = list_url

    if has_passcode:
        access += "<br>Passcode: %s" % instance.passcode

    data = {
        'subject': "Abaca - You've been invited to a list!",
        'message': """
            Howdy,<br><br>
            You've been invited to the following list:<br>
            {list_title}<br><br>
            Here's the {list_requirements} to access the list:<br>
            {list_access}<br><br>
            Best regards,<br> <i>The Abaca Team</i>
        """.format(list_title=instance.title, list_requirements=requirements, list_access=access)
    }

    for user_profile in users_to_be_invited:
        sendEmailWithoutTemplate(user_profile.user.email, data)


m2m_changed.connect(invited_users_added, sender=CompanyList.invited_users.through)
