import factory

from company_lists.models import CompanyList
from viral.tests.factories import UserProfileFactory


class CompanyListFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CompanyList

    title = factory.Faker("catch_phrase")
    owner = factory.SubFactory(UserProfileFactory)
