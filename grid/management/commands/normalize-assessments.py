from django.core.management.base import BaseCommand
from grid.models import Assessment, Level


class Command(BaseCommand):
    """
    This command was built to normalize existing self-assessments with levels pointing incorrectly to the Supporters categories group which led to a issue on the profiles where it was showing copy created for Supporters rather than for Entrepreneurs:
    https://pixelmatters.atlassian.net/projects/VIR/issues/VIR-434
    """
    help = 'Normalize assessment levels'

    def handle(self, *args, **options):
        entrepreneur_levels = Level.objects.filter(group=2)
        # Get only assessements with levels of Supporters
        assessments = Assessment.objects.exclude(level__in=entrepreneur_levels)

        for assessment in assessments:
            # Get the corresponding level by value of a Entrepreneur
            corresponding_entrep_level = next(filter(
                lambda entrep_level: entrep_level.value == assessment.level.value, entrepreneur_levels), None)
            print("\n")
            print("(Old) Supporter level: ", assessment.level_id)
            print("(New) Entrepreneur level: ",
                  corresponding_entrep_level.id)
            assessment.level = corresponding_entrep_level
            assessment.save()
