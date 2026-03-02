from django.apps import AppConfig


class CompanyListsConfig(AppConfig):
    name = 'company_lists'
    verbose_name = 'Company Lists'

    def ready(self):
        # Turn signals on
        import company_lists.signals
