from django.dispatch import receiver
from django.db.models.signals import post_save

from grid.models import Assessment
from milestone_planner.models import Milestone, MilestonePlanner
from milestone_planner.models.user_invitation import UserInvitation
from viral.models import Company, AffiliateProgramEntry


@receiver(post_save, sender=Assessment)
def sync_milestones_upon_assessment_created_or_updated(**kwargs):
    """
    Create milestones or update its current state when a new assessment is created.
    """
    instance = kwargs.get('instance')
    created = kwargs.get('created', False)

    # Disable signal when loading fixtures or when assessment has been created from sync:
    if kwargs.get('raw') or created and instance.from_milestone_planner:
        return

    return Milestone.objects.sync_from_assessment(assessment=instance)


@receiver(post_save, sender=Company)
def create_milestone_planner_upon_company_created(**kwargs):
    """
    Create a milestone planner when a new company of an Entrepreneur is created.
    """
    instance = kwargs.get('instance')
    created = kwargs.get('created', False)

    if not created or instance.type == Company.SUPPORTER:
        return

    MilestonePlanner.objects.create(company=instance)


@receiver(post_save, sender=AffiliateProgramEntry)
def invite_affiliate_owner_to_milestone_planner_upon_submission(sender, instance, **kwargs):
    try:
        milestone_planner = MilestonePlanner.objects.get(company=instance.user_profile.company)
    except MilestonePlanner.DoesNotExist:
        return

    # The "form owners" are all users on the `company` and `supporters` fields of the Affiliate
    form_owners = [supporter.user_profile for supporter in instance.affiliate.supporters.all()]

    if instance.affiliate.company:
        form_owners.append(instance.affiliate.company.company_profile)

    for user_profile in form_owners:
        UserInvitation.objects.update_or_create(
            milestoneplanner=milestone_planner, userprofile=user_profile, defaults={'is_form_owner': True}
        )
