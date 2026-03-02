import copy
import os

import bugsnag
from allauth.account.models import EmailAddress
from allauth.account.signals import email_confirmed
from django.db import connection
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import Signal, receiver
from django.utils.timezone import now

import settings
from company_lists.models import CompanyList
from grid.models import Assessment
from matching.models import Criteria, InterestedCTA, Response, Supporter
from matching.utils import calculate_interest
from shared.execute_sql_in_thread import ExecuteSQLInThread
from shared.mailjet import (
    sendEntrepreneurCompletedProgram,
    sendESOCompletedProgram,
    sendNotificationToAffiliate,
    sendOrganizationCompletedProgram,
)
from viral.models import Affiliate, Company
from viral.models.affiliate_program_entry import AffiliateProgramEntry
from viral.models.affiliate_program_supporter_submission import AffiliateProgramSupporterSubmission
from viral.utils import request_more_data_from_vendor, submit_affiliate_webhook


@receiver(email_confirmed)
def set_new_email_primary(request, email_address, **kwargs):
    EmailAddress.objects.filter(user=email_address.user, primary=False).delete()


# Custom signals
finished_affiliate_flow = Signal()


# @receiver(finished_affiliate_flow)
# def set_entrepreneur_interested_in_supporters(**kwargs):
#     """
#     For all supporters related to an Affiliate flow,
#     set the entrepreneur, that finished a question bundles,
#     as interested in those supporters
#     """
#     affiliate = kwargs.get('affiliate')
#     entrepreneur_company = kwargs.get('entrepreneur_company')
#     print("set_entrepreneur_interested_in_supporters")

#     if affiliate and entrepreneur_company:
#         if affiliate.flow_type == Affiliate.PROGRAM:
#             for supporter in affiliate.supporters.all():
#                 interest, is_new_interest = InterestedCTA.objects.get_or_create(
#                     supporter_id=supporter.user_profile.company.id, entrepreneur_id=entrepreneur_company.id,
#                     defaults={'entrepreneur_is_interested': InterestedCTA.INTERESTED})
#                 if is_new_interest:
#                     # Set state of interest
#                     calculate_interest(interest, None)
#                 else:
#                     # Store a copy of the existing interest
#                     previous_interest = copy.deepcopy(interest)
#                     # Update interest state
#                     interest.entrepreneur_is_interested = InterestedCTA.INTERESTED
#                     interest.save()
#                     # Set state of interest
#                     calculate_interest(previous_interest, interest)


# @receiver(finished_affiliate_flow)
# def add_networks_to_entrepreneur_list(**kwargs):
#     """
#     For all networks related to an Affiliate flow,
#     add to the entrepreneur, that finished a question bundles,
#     those networks
#     """
#     print("add_networks_to_entrepreneur_list")
#     affiliate = kwargs.get('affiliate')
#     entrepreneur_company = kwargs.get('entrepreneur_company')

#     if affiliate and entrepreneur_company:
#         if affiliate.flow_type == Affiliate.PROGRAM:
#             affiliate_networks = affiliate.networks.all()

#             if affiliate_networks.count():
#                 entrepreneur_company.networks.set(affiliate_networks)
#                 entrepreneur_company.save()


@receiver(finished_affiliate_flow)
def send_data_to_affiliate_webhooks(**kwargs):
    """
    For all webhooks related to an Affiliate flow,
    send user data through each webhook.
    """
    affiliate = kwargs.get('affiliate')
    user_profile = kwargs.get('user_profile')
    entrepreneur_company = kwargs.get('entrepreneur_company')

    if affiliate and user_profile and entrepreneur_company:
        for webhook in affiliate.webhooks.all():
            submit_affiliate_webhook(webhook, affiliate, user_profile, entrepreneur_company)


@receiver(finished_affiliate_flow)
def notify_affiliate_of_assesment(**kwargs):
    """
    Send email notification to Affiliate
    of new assessment made by Entrepreneur.
    """
    affiliate = kwargs.get('affiliate')
    user_profile = kwargs.get('user_profile')
    entrepreneur_company = kwargs.get('entrepreneur_company')

    if affiliate and user_profile and entrepreneur_company:
        base_url = os.getenv('APP_BASE_URL', 'my.abaca.app')
        link = 'https://%s/profile/v/%s' % (base_url, entrepreneur_company.access_hash)
        sendNotificationToAffiliate(affiliate.email, user_profile.user, affiliate, link)


@receiver(finished_affiliate_flow)
def thank_entrepreneur_for_submission(**kwargs):
    """
    Send a thank you email for the user that finished the affiliate flow
    """
    affiliate = kwargs.get('affiliate')
    user_profile = kwargs.get('user_profile')
    program_entry = kwargs.get('program_entry')

    if affiliate and user_profile and not user_profile.user.has_usable_password():
        base_url = os.getenv('APP_BASE_URL', 'my.abaca.app')
        submissionLink = 'https://' + base_url + '/program/submission/' + program_entry.uid
        logInLink = 'https://' + base_url + '/auth/login'
        if os.getenv('APP_PARTNER', '') == settings.CLONE_APP_SMALL_FOUNDATION:
            sendOrganizationCompletedProgram(user_profile.user.email, user_profile.user, affiliate)
        elif os.getenv('APP_PARTNER', '') == settings.CLONE_APP_ESO:
            sendESOCompletedProgram(user_profile.user.email, user_profile.user, affiliate)
        else:
            sendEntrepreneurCompletedProgram(
                user_profile.user.email, user_profile.user, affiliate, submissionLink, logInLink
            )


@receiver(post_save, sender=Supporter)
def created_or_updated_supporter(**kwargs):
    # pass
    # NOTE: Disabled for performance issue debugging
    # TODO: Add check to only run updates for fields that have changed
    # sender = kwargs.get('sender')
    instance = kwargs.get('instance')

    # Disable signals when loading fixtures
    if kwargs.get('raw'):
        return

    return
    # Signal calculation start
    # with connection.cursor() as cursor:
    #     try:
    #         cursor.execute("SELECT matching.signal_calculation_start(_supporter_id := %s);" % instance.id)
    #     except Exception as error:
    #         # Only raise issue if not in a potential E2E environment:
    #         if settings.IS_TEST_ENVIRONMENT or settings.IS_LIVE_ENVIRONMENT:
    #             bugsnag.notify(error)
    #     finally:
    #         cursor.close()

    # # Begin calculations
    # sql_statement = '''do
    #     $$
    #         begin
    #             perform matching.refresh_level_score(_refresh_all := false, _supporter_id := {id});
    #             perform matching.refresh_sector_score(_refresh_all := false, _supporter_id := {id});
    #             perform matching.refresh_location_score(_refresh_all := false, _supporter_id := {id});
    #             perform matching.refresh_total_score(_refresh_all := false, _supporter_id := {id});
    #             perform matching.signal_calculation_end(_supporter_id := {id});
    #         end
    #     $$;'''.format(id=instance.id)

    # ExecuteSQLInThread(sql_statement).start()


@receiver(post_save, sender=Company)
def created_or_updated_company(**kwargs):
    # pass
    # NOTE: Disabled for performance issue debugging
    # TODO: Add check to only run updates for fields that have changed
    sender = kwargs.get('sender')
    instance = kwargs.get('instance')
    created = kwargs.get('created')

    # Disable signals when loading fixtures
    if kwargs.get('raw'):
        return

    if created and not instance.logo:
        request_more_data_from_vendor(instance)

    return
    # # Signal calculation start
    # with connection.cursor() as cursor:
    #     try:
    #         cursor.execute("SELECT matching.signal_calculation_start(_company_id := %s);" % instance.id)
    #     except Exception as error:
    #         # Only raise issue if not in a potential E2E environment:
    #         if settings.IS_TEST_ENVIRONMENT or settings.IS_LIVE_ENVIRONMENT:
    #             bugsnag.notify(error)
    #     finally:
    #         cursor.close()

    # # Begin calculations
    # sql_statement = '''do
    #     $$
    #         begin
    #             perform matching.refresh_sector_score(_refresh_all := false, _company_id := {id});
    #             perform matching.refresh_location_score(_refresh_all := false, _company_id := {id});
    #             perform matching.refresh_total_score(_refresh_all := false, _company_id := {id});
    #             perform matching.signal_calculation_end(_company_id := {id});
    #         end
    #     $$;'''.format(id=instance.id)

    # ExecuteSQLInThread(sql_statement).start()


@receiver(post_save, sender=Criteria)
@receiver(post_delete, sender=Criteria)
def created_updated_or_deleted_criteria(**kwargs):
    # pass
    # NOTE: Disabled for performance issue debugging
    # TODO: Add check to only run updates for fields that have changed
    sender = kwargs.get('sender')
    instance = kwargs.get('instance')

    # Disable signals when loading fixtures
    if kwargs.get('raw'):
        return

    return
    # # Signal calculation start
    # with connection.cursor() as cursor:
    #     try:
    #         cursor.execute("SELECT matching.signal_calculation_start(_supporter_id := %s);" % instance.supporter.id)
    #     except Exception as error:
    #         # Only raise issue if not in a potential E2E environment:
    #         if settings.IS_TEST_ENVIRONMENT or settings.IS_LIVE_ENVIRONMENT:
    #             bugsnag.notify(error)
    #     finally:
    #         cursor.close()

    # # Begin calculations
    # sql_statement = '''do
    #     $$
    #         begin
    #             perform matching.refresh_response_score(_refresh_all := false, _supporter_id := {id});
    #             perform matching.refresh_total_score(_refresh_all := false, _supporter_id := {id});
    #             perform matching.signal_calculation_end(_supporter_id := {id});
    #         end
    #     $$;'''.format(id=instance.supporter.id)

    # ExecuteSQLInThread(sql_statement).start()


@receiver(post_save, sender=Response)
@receiver(post_delete, sender=Response)
def created_updated_or_deleted_response(**kwargs):
    # pass
    # NOTE: Disabled for performance issue debugging
    # TODO: Add check to only run updates for fields that have changed
    sender = kwargs.get('sender')
    instance = kwargs.get('instance')

    # Disable signals when loading fixtures
    if kwargs.get('raw'):
        return

    return
    # # Signal calculation start
    # with connection.cursor() as cursor:
    #     try:
    #         cursor.execute("SELECT matching.signal_calculation_start(_company_id := %s);" %
    #                        instance.user_profile.company.id)
    #     except Exception as error:
    #         # Only raise issue if not in a potential E2E environment:
    #         if settings.IS_TEST_ENVIRONMENT or settings.IS_LIVE_ENVIRONMENT:
    #             bugsnag.notify(error)
    #     finally:
    #         cursor.close()

    # # Begin calculations
    # sql_statement = '''do
    #     $$
    #         begin
    #             perform matching.refresh_response_score(_refresh_all := false, _company_id := {id});
    #             perform matching.refresh_total_score(_refresh_all := false, _company_id := {id});
    #             perform matching.signal_calculation_end(_company_id := {id});
    #         end
    #     $$;'''.format(id=instance.user_profile.company.id)

    # ExecuteSQLInThread(sql_statement).start()


@receiver(post_save, sender=Assessment)
def created_or_updated_assessment(**kwargs):
    # pass
    # NOTE: Disabled for performance issue debugging
    # TODO: Add check to only run updates for fields that have changed
    sender = kwargs.get('sender')
    instance = kwargs.get('instance')

    # Disable signals when loading fixtures
    if kwargs.get('raw'):
        return

    return
    # # Signal calculation start
    # with connection.cursor() as cursor:
    #     try:
    #         cursor.execute("SELECT matching.signal_calculation_start(_company_id := %s);" % instance.evaluated)
    #     except Exception as error:
    #         # Only raise issue if not in a potential E2E environment:
    #         if settings.IS_TEST_ENVIRONMENT or settings.IS_LIVE_ENVIRONMENT:
    #             bugsnag.notify(error)
    #     finally:
    #         cursor.close()

    # # Begin calculations
    # sql_statement = '''do
    #     $$
    #         begin
    #             perform matching.refresh_level_score(_refresh_all := false, _company_id := {id});
    #             perform matching.refresh_total_score(_refresh_all := false, _company_id := {id});
    #             perform matching.signal_calculation_end(_company_id := {id});
    #         end
    #     $$;'''.format(id=instance.evaluated)

    # ExecuteSQLInThread(sql_statement).start()


@receiver(post_save, sender=Affiliate)
def create_affiliate_submissions_smart_list(sender, instance, created, **kwargs):
    if created:
        CompanyList.objects.create(
            company_list_type=CompanyList.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS,
            affiliate=instance,
        )
    else:
        CompanyList.objects.filter(
            company_list_type=CompanyList.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS,
            affiliate=instance,
        ).update(
            title=instance.name,
            description=f'Companies appear in this list if they submitted {instance.name}.',
            updated_at=now(),
        )


@receiver(pre_delete, sender=Affiliate)
def delete_affiliate_submissions_smart_list(sender, instance, **kwargs):
    CompanyList.objects.filter(
        company_list_type=CompanyList.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS, affiliate=instance
    ).delete()


@receiver(post_save, sender=AffiliateProgramEntry)
def add_entrepreneur_to_affiliate_submissions_smart_list(sender, instance, **kwargs):
    try:
        smart_list = CompanyList.objects.get(
            company_list_type=CompanyList.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS, affiliate=instance.affiliate
        )
    except CompanyList.DoesNotExist:
        smart_list = CompanyList.objects.create(
            company_list_type=CompanyList.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS, affiliate=instance
        )

    smart_list.companies.add(instance.user_profile.company)


@receiver(post_delete, sender=AffiliateProgramEntry)
def remove_entrepreneur_from_affiliate_submissions_smart_list(sender, instance, **kwargs):
    if not AffiliateProgramEntry.objects.filter(
        affiliate=instance.affiliate, user_profile=instance.user_profile
    ).exists():
        smart_list = CompanyList.objects.filter(
            company_list_type=CompanyList.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS, affiliate=instance.affiliate
        ).first()
        if smart_list:
            smart_list.companies.remove(instance.user_profile.company)


@receiver(post_save, sender=AffiliateProgramSupporterSubmission)
def add_supporter_to_affiliate_submissions_smart_list(sender, instance, **kwargs):
    if hasattr(instance.supporter.user_profile, 'company'):
        CompanyList.objects.get(
            company_list_type=CompanyList.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS, affiliate=instance.affiliate
        ).companies.add(instance.supporter.user_profile.company)


@receiver(post_delete, sender=AffiliateProgramSupporterSubmission)
def remove_supporter_from_affiliate_submissions_smart_list(sender, instance, **kwargs):
    if not AffiliateProgramSupporterSubmission.objects.filter(
        affiliate=instance.affiliate, supporter=instance.supporter
    ).exists():
        smart_list = CompanyList.objects.filter(
            company_list_type=CompanyList.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS, affiliate=instance.affiliate
        ).first()
        company = Company.objects.filter(company_profile__supporter=instance.supporter).first()
        if smart_list and company:
            smart_list.companies.remove(company)
