import factory
import random

from django.contrib.auth import get_user_model

from grid.models import Assessment, CategoryLevel, Category, Level
from viral.models.company import Company
from viral.models.user_profile import UserProfile
from viral.tests.factories import UserFactory, UserProfileFactory, CompanyFactory


class AssessmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Assessment

    class Params:
        with_user_profile = False

    user = factory.SubFactory(UserFactory)
    evaluated = factory.SubFactory(CompanyFactory)
    level = factory.Iterator(Level.objects.filter(group=2))
    hash_token = factory.Faker('md5')

    @factory.lazy_attribute
    def data(self):
        return [{
            'category': category.pk,
            'level': random.choice(CategoryLevel.objects.filter(category=category).values_list('level__value', flat=True))
        } for category in Category.objects.filter(group=2)]

    @factory.post_generation
    def user_profile(instance, create, extracted, **kwargs):
        # Create a linkable user profile
        already_has_user_profile = UserProfile.objects.filter(
            user__pk=instance.user, company__pk=instance.evaluated).exists()
        if already_has_user_profile or not create:
            return
        user = get_user_model().objects.get(pk=instance.user)
        company = Company.objects.get(pk=instance.evaluated)
        return UserProfileFactory(user=user, company=company)

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        # Setting the pk directly due to unexisting ForeignKey in these fields:
        kwargs['user'] = kwargs['user'].pk
        kwargs['evaluated'] = kwargs['evaluated'].pk
        return kwargs
