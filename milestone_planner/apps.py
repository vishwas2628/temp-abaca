from django.apps import AppConfig


class MilestonePlannerConfig(AppConfig):
    name = 'milestone_planner'
    verbose_name = 'Milestone Planner'

    def ready(self):
        # Turn signals on
        import milestone_planner.signals
