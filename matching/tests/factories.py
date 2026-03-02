import factory
import random
from psycopg2.extras import NumericRange

from grid.models import Category, CategoryLevel
from matching.models import Supporter, Question, QuestionBundle, Response, Criteria, CriteriaWeight
from viral.models import Company
from viral.tests.factories import UserProfileFactory


class SupporterFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Supporter

    name = factory.Faker('name')
    email = factory.LazyAttribute(lambda supporter: '%s@example.com' % supporter.name)
    user_profile = factory.SubFactory(UserProfileFactory, company__type=Company.SUPPORTER)

    @factory.lazy_attribute
    def investing_level_range(self):
        # Generate random level range
        random_min_level = random.randrange(1, 5)
        random_max_level = random.randrange(6, 9)
        return NumericRange(random_min_level, random_max_level)


class ResponseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Response

    question = factory.Iterator(Question.objects.all())
    user_profile = factory.SubFactory(UserProfileFactory)


class QuestionBundleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = QuestionBundle

    class Params:
        with_category = False
        with_category_level = False

    name = factory.Faker('name')
    supporter = factory.SubFactory(SupporterFactory)

    @factory.lazy_attribute
    def category(self):
        if self.with_category:
            return random.choice(list(Category.objects.all()))
        return None

    @factory.lazy_attribute
    def category_level(self):
        if self.with_category_level:
            return random.choice(list(CategoryLevel.objects.all()))
        return None

    @factory.post_generation
    def questions(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of questions were passed in, use them
            for question in extracted:
                self.questions.add(question)


class CriteriaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Criteria

    name = factory.Faker('name')
    description = factory.Faker('catch_phrase')
    question = factory.Iterator(Question.objects.all())
    supporter = factory.SubFactory(SupporterFactory)
    criteria_weight = factory.Iterator(CriteriaWeight.objects.all())
