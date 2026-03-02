from django.apps import apps
from allauth.utils import get_user_model

from viral.models import Company, Affiliate, UserProfile
from grid.models import Assessment, Level, Category, CategoryLevel
from grid.serializers import ViralLevelSerializer
from .base import BaseGenerator


class AssessmentsGenerator(BaseGenerator):
    """
    Generator for Assessments
    """
    fixtures = {
        'assessments': {
            'model': apps.get_model('grid', 'Assessment'),
            'value': []
        },
    }

    def __init__(self, amount):
        super().__init__()
        self.amount = amount
        self._set_fixtures_count()
        self._generate_fixtures()

    def _set_fixtures_count(self):
        for fixture in self.fixtures:
            self.fixtures[fixture]['count'] = self.fixtures[fixture]['model'].objects.count(
            )

    def _generate_fixtures(self):
        start = 1
        end = self.amount + start

        for index in range(start, end):
            # Indexing based on database count
            assessment_id = index + self.fixtures['assessments']['count']

            entrepreneur = self.random.choice(
                UserProfile.objects.filter(company__type=Company.ENTREPRENEUR))

            categories = Category.objects.filter(group__slug='entrepreneurs')
            category_levels = []
            for category in categories:
                random_category_level = self.random.choice(
                    CategoryLevel.objects.filter(category=category))
                category_levels.append(random_category_level)

            viral_level = self._calculate_viral_level(category_levels)
            serializer = ViralLevelSerializer(category_levels, many=True)

            date_created = str(self.fake.date_time_between(start_date='-2y'))

            self.fixtures['assessments']['value'].append({
                "model": "grid.assessment",
                "pk": assessment_id,
                "fields": {
                    "level": viral_level.pk,
                    "data": serializer.data,
                    "user": entrepreneur.user.id,
                    "evaluated": entrepreneur.company.id,
                    "hash_token": self._get_random_hex_str(20),
                    "state": self.random.randrange(0, 2),
                    "created_at": date_created,
                    "updated_at": date_created,
                }
            })

    def _calculate_viral_level(self, levels):
        current_level = Level.objects.filter(
            group__slug='entrepreneurs').order_by('value').last()
        for viralLevel in levels:
            level = viralLevel.level
            if level is None:
                return Level.objects.filter(
                    group__slug='entrepreneurs').order_by('value').first()
            elif level.value < current_level.value:
                current_level = level
        return current_level
