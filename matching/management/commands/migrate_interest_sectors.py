from django.core.management.base import BaseCommand

from viral.models import Group
from matching.models import SupporterInterestSector

class Command(BaseCommand):
    """
    This command was built to: 
    1 - Convert selections of two or more interest sectors,
    that are in fact sub-sectors (like Therapeutics, Biopharma) 
    which belong to the same group (Health Care) into a "grouped sectors selection"

    2 - Convert all interest sectors that are replicates 
    of a group (such as healthcare) into a "grouped sectors selection"
    """

    def handle(self, *args, **options):
        self.migrate_multiple_sectors_into_group()
        self.migrate_group_replicates_into_full_selection()

        print("\r")
        print("Finished migrating interest sectors.")
        print("\r")

    def migrate_multiple_sectors_into_group(self):
        interest_sectors = SupporterInterestSector.objects.prefetch_related('sector__groups').filter(group__isnull=True).exclude(sector__groups=None)
        supporter_sectors_grouped = []

        for selection in interest_sectors:
            sector_group = selection.sector.groups.first()
            supporter_in_list = any(selection.supporter.id == item['supporter'] for item in supporter_sectors_grouped)

            if not supporter_in_list:
                supporter_sectors_grouped.append({
                    'supporter': selection.supporter.id,
                    'sectors': {}
                })

            item_index = next((index for (index, item) in enumerate(supporter_sectors_grouped) if item["supporter"] == selection.supporter.id), None)

            if item_index:
                if sector_group.id not in supporter_sectors_grouped[item_index]['sectors']:
                    supporter_sectors_grouped[item_index]['sectors'][sector_group.id] = []
                
                if selection.sector.id not in supporter_sectors_grouped[item_index]['sectors'][sector_group.id]:
                    supporter_sectors_grouped[item_index]['sectors'][sector_group.id].append(selection.sector.id)

        for item in supporter_sectors_grouped:
            for group_id, sectors in item['sectors'].items():
                if len(sectors) > 1:
                    sectors_of_same_group = interest_sectors.filter(sector__in=sectors, supporter=item['supporter']).distinct('pk', 'sector')
                    print("Grouped sectors: ", sectors_of_same_group)
                    sectors_of_same_group.update(group=group_id)

    def migrate_group_replicates_into_full_selection(self):
        interest_sectors = SupporterInterestSector.objects.filter(group__isnull=True).exclude(sector__groups=None)
        
        for selection in interest_sectors:
            try:
                replicated_group = selection.sector.groups.get(name=selection.sector.name)

                print("\n")
                print("Updating selection: ", selection)
                selection.group = replicated_group
                selection.save()

                group_sectors = replicated_group.sectors.exclude(pk=selection.sector.id)
                if len(group_sectors):
                    print("Adding group sectors:")

                for sector in group_sectors:
                    grouped_sector, created = SupporterInterestSector.objects.get_or_create(supporter=selection.supporter, sector=sector)
                    if created:
                        grouped_sector.group = replicated_group
                        grouped_sector.save()
                        print(grouped_sector)
            except Group.DoesNotExist:
                pass
            except Exception as error:
                print("\r")
                print(error)
                print("\r")
                break

