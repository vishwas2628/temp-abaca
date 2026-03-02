from django.apps import AppConfig


class CapitalExplorerConfig(AppConfig):
    name = 'capital_explorer'
    verbose_name = 'Capital Explorer'
    
    def ready(self):
        from . import signals