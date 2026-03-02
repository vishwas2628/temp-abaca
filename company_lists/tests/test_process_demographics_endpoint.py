from django.core import management
from django.urls import reverse
from allauth.utils import get_user_model
from jsonschema import validate
from rest_framework.status import HTTP_200_OK
from matching.models import Question, QuestionType
from matching.models.answer import Answer
from shared.utils import AbacaAPITestCase
from company_lists.tests.schemas.process_demographics_schema import process_demographics_schema
from viral.models import Company, UserProfile
from viral.tests.factories import UserProfileFactory


class TestProcessDemographicsEndpoint(AbacaAPITestCase):
    def setUp(self):
        super().setUp()
        user_profile = UserProfileFactory(company__name='Lopez-Ruiz')
        self._create_mock_questions()
        management.call_command('mock-demographic-data')
        self.process = user_profile.company.process_set.first()
        self.client.force_authenticate(user=user_profile.user)

    def _create_mock_questions(self):
        single_select = QuestionType.objects.create(name='Single Select', type='single_select')
        
        sexual_orientation = Question.objects.create(
            slug='Individual_Sexual_Orientation',
            ttl='10000 days',
            is_team_member_question=True,
            question_type=single_select,
        )
        Answer.objects.bulk_create(
            [
                Answer(question_id=sexual_orientation.pk, value='Bisexual'),
                Answer(question_id=sexual_orientation.pk, value='Heterosexual or straight'),
                Answer(question_id=sexual_orientation.pk, value='Homosexual or lesbian/gay'),
                Answer(question_id=sexual_orientation.pk, value='Queer, questioning, asexual, or a sexuality not listed'),
                Answer(question_id=sexual_orientation.pk, value='Prefer not to say'),
            ]
        )

        gender_identity = Question.objects.create(
            slug='Individual_Gender_Identity',
            ttl='10000 days',
            is_team_member_question=True,
            question_type=single_select,
        )
        Answer.objects.bulk_create(
            [
                Answer(question_id=gender_identity.pk, value='Man'),
                Answer(question_id=gender_identity.pk, value='Woman'),
                Answer(question_id=gender_identity.pk, value='Non-binary'),
                Answer(question_id=gender_identity.pk, value='LGBT'),
                Answer(question_id=gender_identity.pk, value='Prefer not to say'),
            ]
        )

        race_ethnicity = Question.objects.create(
            slug='Individual_Race_Ethnicity',
            ttl='10000 days',
            is_team_member_question=True,
            question_type=single_select,
        )
        Answer.objects.bulk_create(
            [
                Answer(question_id=race_ethnicity.pk, value='Hispanic, Latino or Spanish Origin'),
                Answer(question_id=race_ethnicity.pk, value='Middle Eastern or North African'),
                Answer(question_id=race_ethnicity.pk, value='South Asian'),
                Answer(question_id=race_ethnicity.pk, value='Southeast Asian'),
                Answer(question_id=race_ethnicity.pk, value='White or European'),
                Answer(question_id=race_ethnicity.pk, value='Some other race, ethicity, or origin'),
            ]
        )

    def test_response_schema(self):
        response = self.client.get(
            reverse('process_demographic_stats', kwargs={'process_id': self.process.id}),
            data={'question_slug': 'Individual_Sexual_Orientation'},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        validate(instance=response.data, schema=process_demographics_schema)
