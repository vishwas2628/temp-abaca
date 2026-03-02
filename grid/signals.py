from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete

from milestone_planner.models import Milestone
from grid.models import Assessment


@receiver(post_save, sender=Milestone, dispatch_uid="milestone_created_or_updated")
def sync_assessment_upon_milestone_created_or_updated_or_deleted(**kwargs):
    """
    Sync latest assessment when a milestone is created, updated or deleted.
    """
    instance = kwargs.get('instance')
    created = kwargs.get('created', False)

    # Disable signal when loading fixtures
    if kwargs.get('raw'):
        return

    return Assessment.objects.sync_with_milestone(milestone=instance, created=created)
