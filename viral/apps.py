from django.apps import AppConfig
import watson
from watson import search as watson


class SectorSearchAdapter(watson.SearchAdapter):
    def get_content(self, obj):
        return obj.name.replace("-", "")


class ViralConfig(AppConfig):
    name = 'viral'

    def ready(self):
        # Turn signals on
        import viral.signals

        # Configure Watson for sectors
        Sector = self.get_model('Sector')
        SectorGroup = self.get_model('Group')

        watson.register(SectorGroup)
        watson.register(Sector, SectorSearchAdapter)

        # Configure Watson for companies
        Company = self.get_model('Company')
        # TEMPORARY: Disable search by email
        # watson.register(Company, fields=('name', 'email',))
        watson.register(Company, fields=('name',))
