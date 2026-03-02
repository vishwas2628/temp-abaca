import faker
from factory import Sequence
from random import choice, randint, random
from django.core.management import BaseCommand
from django.db import transaction
from django.conf import settings

from allauth.account.models import EmailAddress
from matching.models import Question, Response
from company_lists.models import CompanyList, Process, ProcessStep
from viral.models import Affiliate, UserProfile
from viral.tests.factories import TeamMemberFactory, UserProfileFactory


class Command(BaseCommand):
    help = 'Generates mock demographic data'
    faker = faker.Factory.create()

    def handle(self, *args, **options):
        if settings.IS_LIVE_ENVIRONMENT:
            print("Cannot generate mock demographic data in production.")
            return

        questions = {
            'gender': Question.objects.get(slug='Individual_Gender_Identity'),
            'ethnicity': Question.objects.get(slug='Individual_Race_Ethnicity'),
            'sexual_orientation': Question.objects.get(slug='Individual_Sexual_Orientation'),
        }

        answers = {slug: question.answer_set.all() for slug, question in questions.items()}

        user_profile = UserProfile.objects.get(company__name='Lopez-Ruiz')

        team_members = []
        responses = []

        with transaction.atomic():
            process = Process.objects.create(title='Demographic Mock', company_id=user_profile.company_id)

            pipeline_list = CompanyList.objects.create(title='Pipeline', owner=user_profile)
            screen_list = CompanyList.objects.create(title='Screen', owner=user_profile)
            meet_list = CompanyList.objects.create(title='Meet', owner=user_profile)
            due_diligence_list = CompanyList.objects.create(title='Due Diligence', owner=user_profile)
            invest_list = CompanyList.objects.create(title='Invest', owner=user_profile)

            process_steps = ProcessStep.objects.bulk_create([
                ProcessStep(process=process, company_list=pipeline_list, title='Pipeline', order=1),
                ProcessStep(process=process, company_list=screen_list, title='Screen', order=2),
                ProcessStep(process=process, company_list=meet_list, title='Meet', order=3),
                ProcessStep(process=process, company_list=due_diligence_list, title='Due Diligence', order=4),
                ProcessStep(process=process, company_list=invest_list, title='Invest', order=5),
            ])

            profiles = UserProfileFactory.create_batch(
                100,
                user__email=Sequence(lambda n: f'demographic-mock-{n + 1}@abaca.test'),
                user__username=Sequence(lambda n: f'demographic-mock-{n + 1}'),
                company__name=Sequence(lambda n: f'Demographic Mock {n + 1}'),
                source=Affiliate.objects.get(id=1),
            )

            for profile in profiles:
                EmailAddress.objects.create(user=profile.user, email=profile.user.email, primary=True, verified=True)
                choice(process_steps).company_list.companies.add(profile.company)
                if random() > 0.1:
                    team_members.extend(TeamMemberFactory.create_batch(randint(5, 10), company=profile.company))

            for team_member in team_members:
                if random() > 0.2:
                    for slug, question in questions.items():
                        response = Response.objects.create(
                            user_profile=team_member.company.company_profile,
                            team_member=team_member,
                            question=question,
                        )
                        response.answers.add(choice(answers[slug]))
                        responses.append(response)

