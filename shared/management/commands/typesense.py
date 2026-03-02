from django.core.management.base import BaseCommand, CommandError
from shared.Typesense import Typesense


class Command(BaseCommand):
    help = 'execute drf view to seed company data into typesense'
    typesense = Typesense()

    def add_arguments(self, parser):
        parser.add_argument('action', nargs='*', type=str)

    def update(self):
        return self.typesense.seed("update")

    def clear(self):
        print('clear: not implemented')
        pass

    def seed(self):
        print("seeding")
        return self.typesense.seed("seed")

    def handle(self, *args, **options):
        try:
            result = None
            action = options['action'][0].split('=')[1]

            if action == 'seed':
                result = self.seed()
            elif action == 'update':
                result = self.update()
            elif action == 'clear':
                result = self.clear()
            else:
                print('unknown action type')

            print("completed")
            print(result)
        except:
            print('something went wrong')

