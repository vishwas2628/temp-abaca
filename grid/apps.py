from django.apps import AppConfig


class GridConfig(AppConfig):
    name = 'grid'

    def ready(self):
        # Turn signals on
        import grid.signals
