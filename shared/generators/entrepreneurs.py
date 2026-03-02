from allauth.account.models import EmailAddress
from allauth.utils import get_user_model
from django.apps import apps

from viral.models import Company

from .base import BaseGenerator


class EntrepreneursGenerator(BaseGenerator):
    """
    Generator for Entrepreneur Companies
    """
    fixtures = {
        'users': {
            'model': get_user_model(),
            'value': []
        },
        'email_addresses': {
            'model': EmailAddress,
            'value': []
        },
        'companies': {
            'model': apps.get_model('viral', 'Company'),
            'value': []
        },
        'user_profiles': {
            'model': apps.get_model('viral', 'UserProfile'),
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
            user_id = index + self.fixtures['users']['count']
            company_id = index + self.fixtures['companies']['count']
            email_id = index + self.fixtures['email_addresses']['count']
            userprofile_id = index + self.fixtures['users']['count']

            # Reusable data
            company_type = Company.ENTREPRENEUR
            company_name = self.fake.company()
            company_slug = self.slugify(company_name)
            company_email = "abaca-dev+%s@pixelmatters.com" % company_slug
            company_website = self.fake.domain_name()
            company_about = self.fake.paragraph()
            date_created = str(self.fake.date_time_between(start_date='-2y'))

            self.fixtures['users']['value'].append({
                "model": "auth.user",
                "pk": user_id,
                "fields": {
                    "password": "pbkdf2_sha256$100000$IDdw62PCinq2$dXx3hw2BjzitvfKrgPpppD1IAqEnQpLZg2haav1rp20=",
                    "last_login": str(self.fake.date_time_this_year()),
                    "is_superuser": False,
                    "username": company_slug,
                    "first_name": "",
                    "last_name": "",
                    "email": company_email,
                    "is_staff": False,
                    "is_active": True,
                    "date_joined": date_created,
                    "groups": [],
                    "user_permissions": []
                }
            })

            self.fixtures['email_addresses']['value'].append({
                "model": "account.emailaddress",
                "pk": email_id,
                "fields": {
                    "user": user_id,
                    "email": company_email,
                    "verified": True,
                    "primary": True
                }
            })

            self.fixtures['companies']['value'].append({
                "model": "viral.company",
                "pk": company_id,
                "fields": {
                    "created_at": date_created,
                    "updated_at": date_created,
                    "uid": self.random_uid(),
                    "type": company_type,
                    "name": company_name,
                    "slug": company_slug,
                    "logo": "",
                    "cover": "",
                    "about": company_about,
                    "website": company_website,
                    "email": company_email,
                    "founded_date": str(self.fake.date()),
                    "crunchbase_id": self.random.choice([self.fake.ean(length=8), None]),
                    "access_hash": self._get_random_hex_str(5),
                    "sectors": [
                        self.random.randrange(1, 680),
                        self.random.randrange(1, 680),
                        self.random.randrange(1, 680),
                    ],
                    "locations": [
                        self.random.randrange(1, 50)
                    ],
                    "networks":
                        self.random.choice([
                            [self.random.randrange(1, 6)],
                            []
                        ])

                }
            })

            self.fixtures['user_profiles']['value'].append({
                "model": "viral.userprofile",
                "pk": userprofile_id,
                "fields": {
                    "created_at": date_created,
                    "updated_at": date_created,
                    "uid": self.random_uid(),
                    "user": user_id,
                    "company": company_id,
                    "source": self.random.choice([1, 2, None])
                }
            })
