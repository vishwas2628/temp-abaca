from django.core.management.base import BaseCommand
from django.db.models import Count

from matching.models import Criteria


class Command(BaseCommand):
    """
    This command was built to normalize existing criteria that is outdated and should be inactive:
    https://pixelmatters.atlassian.net/projects/VIR/issues/VIR-958
    """
    help = 'Normalize in/active criteria'

    def handle(self, *args, **options):
        self._disable_outdated_criteria()
        print("\r")
        print("Finished active criteria normalization")
        print("\r")

    def _disable_outdated_criteria(self):
        duplicated_criteria = Criteria.objects.values('question', 'supporter').annotate(
            duplicated=Count('question')).filter(duplicated__gt=1, is_active=True).order_by('duplicated')

        if not duplicated_criteria:
            print("\n")
            print("Nothing to do here!")

        for criteria in duplicated_criteria:
            outdated_criteria_pks = Criteria.objects.filter(
                is_active=True, question=criteria['question'],
                supporter=criteria['supporter']).values_list('pk', flat=True).order_by('-updated_at')[1:]
            Criteria.objects.filter(pk__in=list(outdated_criteria_pks)).update(is_active=False)
            print("\n")
            print("Disabled outdated Criteria:")
            print(outdated_criteria_pks)
            print("\n")
