from django.dispatch import receiver
from django.db.models.signals import post_save

from matching.models import Criteria


@receiver(post_save, sender=Criteria)
def created_or_updated_criteria(**kwargs):
    instance = kwargs.get('instance')

    # Disable signal when loading fixtures
    if kwargs.get('raw'):
        return

    # Disable previous Criteria
    Criteria.objects.filter(
        supporter=instance.supporter.id, question=instance.question.id, is_active=True).exclude(
        pk=instance.pk).update(is_active=False)
