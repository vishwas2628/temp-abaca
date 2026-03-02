import os
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from capital_explorer.models import Submission
from shared.mailjet.mailjet import sendEmailWithoutTemplate
from viral.models.user_profile import UserProfile


@receiver(m2m_changed, sender=Submission.invited_users.through)
def send_new_invitation_emails(sender, instance, action, **kwargs):
    if action != 'post_add':
        return

    users = UserProfile.objects.filter(pk__in=list(kwargs.get('pk_set', [])))

    if users.count() == 0:
        return

    link = f'https://{os.getenv("APP_BASE_URL", "my.abaca.app")}/capital-explorer/{instance.uid}'

    subject = f"Explore {instance.company.name}'s Capital Explorer Results"

    message = "<p>Hi,</p>\n"
    message += f"<p>You've been invited to explore {instance.company.name}'s Capital Explorer Results."

    if instance.passcode:
        message += " To access these results, please use the passcode provided below:</p>\n"
        message += f"<p>Passcode: {instance.passcode}"

    message += "</p>\n"
    message += f"<p>You can access the results by clicking <a href=\"{link}\">here</a>. In case the direct link doesn't work, you can also use this URL:<br>{link}</p>\n"
    message += "<p>If you have any questions or need assistance, don't hesitate to reach out.</p>\n"
    message += "<p>Best regards,<br><i>The Abaca Team</i></p>"

    email_data = {
        'subject': subject,
        'message': message,
    }

    for user_profile in users:
        sendEmailWithoutTemplate(user_profile.user.email, email_data)
