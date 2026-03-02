import factory
import faker

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

from viral.models import Affiliate, Company, Location, Sector, UserGuest, UserProfile, TeamMember


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda index: '%s-%d' % (factory.Faker('first_name'), index))
    email = factory.Faker('email')
    password = make_password("12345678")


class UserGuestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserGuest

    name = factory.Faker('name')
    email = factory.Faker('email')


class EmailAddressFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EmailAddress

    user = factory.RelatedFactory(UserFactory)
    email = factory.Faker('email')

    # By default it will be primary and already verified.
    primary = True
    verified = True


class AffiliateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Affiliate

    name = factory.Faker('company')
    shortcode = factory.Faker('company_suffix')
    email = factory.Faker('email')
    website = factory.Faker('domain_name')
    logo = factory.Faker('image_url')

    # Defaults to the self-assessment flow
    flow_type = Affiliate.SELF_ASSESSMENT


class LocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Location

    formatted_address = factory.Faker('street_address')
    latitude = factory.Faker('latitude')
    longitude = factory.Faker('longitude')


class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company

    name = factory.Faker('company')
    about = factory.Faker('paragraph')
    website = factory.Faker('domain_name')

    # Defaults to Entrepreneur
    type = Company.ENTREPRENEUR

    @factory.post_generation
    def locations(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of custom locations were passed in, use them
            for location in extracted:
                self.locations.add(location)
        else:
            # Append a default location
            default_location = LocationFactory()
            self.locations.add(default_location)


class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
    company = factory.SubFactory(CompanyFactory)
    source = factory.SubFactory(AffiliateFactory)


class SectorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Sector

    name = factory.LazyAttribute(lambda attr: faker.Faker().job()[:50])
    uuid = factory.Faker('uuid4')


class TeamMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TeamMember

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Faker('email')
    position = factory.Faker('job')
    is_active = True