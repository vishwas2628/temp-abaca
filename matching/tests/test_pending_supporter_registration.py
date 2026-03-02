from os import urandom
from random import choice
from unittest import mock

from allauth.account.models import EmailAddress
from allauth.utils import get_user_model
from django.apps import apps
from django.db.models import Count, Q
from django.urls import reverse
from matching.models import (Criteria, CriteriaWeight, Question,
                             QuestionBundle, QuestionType, Supporter)
from psycopg2.extras import NumericRange
from rest_framework import status
from shared.models import PendingRegistration
from shared.utils import AbacaAPITestCase
from viral.models import (Affiliate, AffiliateProgramSupporterSubmission,
                          Company, UserProfile)


class TestPendingSupporterRegistration(AbacaAPITestCase):
    """
    Test pending supporter registration:
    * 1 - Without payload
    * 2 - Token:
    * 2.1 - With unexisting token
    * 2.2 - Only with existing token
    * 3 - Affiliate:
    * 3.1 - Start with missing default affiliate
    * 3.2 - Start with default affiliate
    * 3.3 - Start with an existing affiliate
    * 4 - Email:
    * 4.1 - Start with invalid email
    * 4.2 - Start with valid email
    * 4.3 - Start with existing email
    * 4.4 - Update existing email
    * 5 - Password:
    * 5.1 - With invalid values
    * 5.2 - With missing confirmation field
    * 5.3 - With invalid confirmation value
    * 5.4 - With valid values
    * 5.5 - Update existing password
    * 6 - Supporter Data (default affiliate):
    * 6.1 - Start with incomplete data
    * 6.2 - Start with invalid data
    * 6.3 - Start with valid data
    * 6.4 - Update existing Supporter
    * 7 - Supporter Data (existing affiliate / inactive supporter):
    * 7.1 - Start with valid data
    * 7.2 - Update inactive Supporter
    * 7.3 - With Company
    * 8 - Questionary:
    * 8.1 - With invalid criteria
    * 8.2 - With wrong question bundle questions
    * 8.3 - With valid criteria
    * 8.4 - With updated criteria
    * 8.5 - With inactive supporter
    * 9 - Interests:
    * 9.1 - With invalid criteria
    * 9.2 - With valid criteria
    * 9.3 - With updated criteria
    * 9.4 - With inactive supporter
    * 10 - Importances:
    * 10.1 - With invalid weights
    * 10.2 - With valid weights
    * 10.3 - With inactive supporter
    * 11 - Pending Registration status:
    * 11.1 - With incomplete submission
    * 11.2 - With complete submission
    """
    fixtures = ['supporter_types', 'networks', 'location_groups', 'locations', 'profile_id_fields',
                'question_types', 'question_categories', 'questions', 'answers', 'criteria_weights']

    ENDPOINT = reverse('register_pending_supporter')
    NEW_EMAIL = 'new@supporter.com'
    UPDATED_EMAIL = 'updated@supporter.com'
    EXISTING_EMAIL = 'existing@supporter.com'
    NEW_PASSWORD = '1a2@34*5'
    UPDATED_PASSWORD = '1p(j3h1b'
    NEW_SUPPORTER_NAME = 'New Supporter'
    UPDATED_SUPPORTER_NAME = 'Updated Supporter'
    NEW_OTHER_TYPE = 'Custom Supporter Type'
    UPDATED_OTHER_TYPE = 'Custom Updated Supporter Type'
    NEW_INVESTING_RANGE = [2, 4]
    UPDATED_INVESTING_RANGE = [3, 6]
    SUPPORTER_NEW_LOCATION = {
        'formatted_address': 'Neverland',
        'latitude': 0.0,
        'longitude': 0.0
    }
    SUPPORTER_UPDATED_LOCATION = {
        'formatted_address': 'Hogwarts',
        'latitude': 0.0,
        'longitude': 0.0
    }
    NEW_CRITERIA_DESIRED_VALUE = 50
    UPDATED_CRITERIA_DESIRED_VALUE = 100

    def _create_question_bundle(self):
        supporter_user, supporter_email = self._create_new_user(name='QB Supporter', email='qb@mail.com')
        supporter, supporter_company = self._create_existing_supporter(supporter_user)

        question_types = [QuestionType.NUMERIC, QuestionType.SINGLE_SELECT,
                          QuestionType.FREE_RESPONSE, QuestionType.RANGE, QuestionType.DATE]
        questions = Question.objects.filter(question_type__type__in=question_types).order_by(
            'question_type__type').distinct('question_type__type')

        question_bundle = QuestionBundle.objects.create(**{
            'name': 'Supporter QB',
            'supporter': supporter
        })
        question_bundle.questions.set(questions)
        question_bundle.save()

        return question_bundle

    def _create_supporter_affiliate(self, is_default=True):
        supporter_affiliate = Affiliate.objects.create(**{
            'name': 'Supporter Affiliate',
            'shortcode': 'sa',
            'email': 'sa@mail.com',
            'flow_type': Affiliate.PROGRAM,
            'flow_target': Company.SUPPORTER,
            'default_flow': is_default
        })
        question_bundle = self._create_question_bundle()
        supporter_affiliate.question_bundles.add(question_bundle)
        supporter_affiliate.save()

        return supporter_affiliate

    def _create_existing_user(self):
        user_payload = ['existing_user', self.EXISTING_EMAIL]
        existing_user = get_user_model().objects.create_user(*user_payload)
        existing_email = EmailAddress.objects.create(
            user=existing_user,
            email=self.EXISTING_EMAIL, primary=True,
            verified=True)
        return existing_user, existing_email

    def _create_new_user(self, name='new_user', email=None, set_password=False):
        user_email = email or self.NEW_EMAIL
        user_payload = [name, user_email]
        new_user = get_user_model().objects.create_user(*user_payload)
        if set_password:
            new_user.set_password(self.NEW_PASSWORD)
            new_user.save()
        new_email = EmailAddress.objects.create(
            user=new_user,
            email=new_user.email, primary=True,
            verified=True)
        return new_user, new_email

    def _create_existing_supporter(self, user, as_inactive=False):
        supporter_company = Company.objects.create(**{
            'name': 'Supporter Company',
            'about': 'A cool company',
            'website': 'https://supporter-company.com',
            'type': Company.SUPPORTER,
            'access_hash': urandom(5).hex()
        })
        supporter_user_profile = UserProfile.objects.create(
            user=user, company=supporter_company) if not as_inactive else None
        existing_supporter = Supporter.objects.create(**{
            'name': 'Testing Supporter',
            'about': 'A cool Supporter',
            'email': self.NEW_EMAIL,
            'investing_level_range': self.NEW_INVESTING_RANGE,
            'user_profile': supporter_user_profile,
        })

        if as_inactive:
            return existing_supporter

        return existing_supporter, supporter_company

    def _create_existing_criteria(self, supporter, affiliate):
        default_criteria_weight = CriteriaWeight.objects.order_by('value').first()
        question_bundle = affiliate.question_bundles.first()
        question_bundle_questions_pk = question_bundle.questions.values_list('pk', flat=True)
        numeric_question = Question.objects.filter(
            pk__in=question_bundle_questions_pk, question_type__type=QuestionType.NUMERIC).first()
        existing_criteria = Criteria.objects.create(**{
            'name': 'Existing Criteria',
            'question': numeric_question,
            'desired': {'value': self.NEW_CRITERIA_DESIRED_VALUE},
            'supporter': supporter,
            'criteria_weight': default_criteria_weight
        })

        # Create/update supporter submission
        submission, created = AffiliateProgramSupporterSubmission.objects.get_or_create(
            supporter=supporter, affiliate=affiliate)
        submission.criteria.set([existing_criteria])
        submission.save()

        return existing_criteria

    def _create_existing_additional_criteria(self, supporter, affiliate):
        default_criteria_weight = CriteriaWeight.objects.order_by('value').first()
        numeric_question = Question.objects.filter(question_type__type=QuestionType.NUMERIC).first()
        existing_criteria = Criteria.objects.create(**{
            'name': 'Existing Criteria',
            'question': numeric_question,
            'desired': {'value': self.NEW_CRITERIA_DESIRED_VALUE},
            'supporter': supporter,
            'criteria_weight': default_criteria_weight
        })

        # Create/update supporter submission
        submission, created = AffiliateProgramSupporterSubmission.objects.get_or_create(
            supporter=supporter, affiliate=affiliate)
        submission.additional_criteria.set([existing_criteria])
        submission.save()

        return existing_criteria

    def _create_pending_registration(
            self, with_default_affiliate=True, with_password=False,
            with_supporter=False, with_inactive_supporter=False, with_criteria=False, with_additional_criteria=False):
        created_instances = []

        affiliate = self._create_supporter_affiliate(is_default=with_default_affiliate)
        new_user, new_email = self._create_new_user(set_password=with_password)
        pending_registration = PendingRegistration.objects.create(user=new_user, affiliate=affiliate)

        created_instances.extend([pending_registration, new_user, new_email, affiliate])

        supporter = None
        if with_supporter:
            supporter, company = self._create_existing_supporter(new_user)
            created_instances.insert(0, supporter)
            created_instances.insert(1, company)
        elif with_inactive_supporter:
            supporter = self._create_existing_supporter(new_user, as_inactive=True)
            created_instances.insert(0, supporter)

        if with_criteria and supporter:
            criteria = self._create_existing_criteria(supporter, affiliate)
            created_instances.insert(1, criteria)

        if with_additional_criteria and supporter:
            additional_criteria = self._create_existing_additional_criteria(supporter, affiliate)
            created_instances.insert(1, additional_criteria)

        return tuple(created_instances)

    def _get_random_model_instance(self, app, model):
        model_class = apps.get_model(app, model)
        pks = model_class.objects.values_list('pk', flat=True)
        random_pk = choice(pks)
        return model_class.objects.get(pk=random_pk)

    def _get_mocked_google_location(self, place_id=None):
        return [{
            'formatted_address': 'Portugal',
            'address_components': [{
                'long_name': 'Portugal',
                'short_name': 'PT',
                'types': ['country']
            }],
            'geometry': {
                'location': {'lat': 0.0, 'lng': 0.0}
            }
        }]

    def _generate_random_supporter_data(self):
        random = {
            'type': self._get_random_model_instance('matching', 'SupporterType'),
            'sector': self._get_random_model_instance('viral', 'Sector'),
            'sector_group': self._get_random_model_instance('viral', 'Group'),
            'location_group': self._get_random_model_instance('viral', 'LocationGroup')
        }
        random['sectors_from_group'] = apps.get_model(
            'viral', 'Sector').objects.filter(
            groups=random['sector_group'])
        random['locations_from_group'] = apps.get_model(
            'viral', 'Location').objects.filter(
            groups=random['location_group'])

        return random

    def _payload_with_token(self, payload, value=None):
        payload['token'] = value or 'invalid-token'
        return payload

    def _payload_with_affiliate(self, payload, value):
        payload['affiliate'] = value
        return payload

    def _payload_with_email(self, payload, valid=True, updated=False, existing=False):
        if existing:
            payload['email'] = self.EXISTING_EMAIL
        elif updated:
            payload['email'] = self.UPDATED_EMAIL
        else:
            payload['email'] = self.NEW_EMAIL if valid else 'invalid-email'

        return payload

    def _payload_with_password(
            self, payload, valid=True, updated=False, with_confirmation=True, valid_confirmation=True):
        if valid:
            valid_password = self.UPDATED_PASSWORD if updated else self.NEW_PASSWORD
            payload['password1'] = valid_password

            if with_confirmation:
                payload['password2'] = valid_password if valid_confirmation \
                    else 'invalid-confirmation'
        else:
            payload['password1'] = 0.0
            payload['password2'] = 0.0

        return payload

    def _payload_with_supporter_data(self, payload, with_supporter=True, with_company=True, valid=True, existing=False):
        if with_supporter:
            if existing:
                self.random_supporter = self._generate_random_supporter_data()

                payload['supporter'] = {
                    'types': [self.random_supporter['type'].pk],
                    'other_type': self.UPDATED_OTHER_TYPE,
                    'investing_level_range': self.UPDATED_INVESTING_RANGE,
                    'sectors': [self.random_supporter['sector'].pk],
                    'grouped_sectors': [{
                        'group': self.random_supporter['sector_group'].pk,
                        'sectors': self.random_supporter['sectors_from_group'].values_list('pk', flat=True)
                    }],
                    'grouped_locations': [{
                        'group': self.random_supporter['location_group'].pk,
                        'locations': self.random_supporter['locations_from_group'].values_list('pk', flat=True)
                    }],
                    'places': ['valid_google_place_id']
                }
            elif valid:
                self.random_supporter = self._generate_random_supporter_data()

                payload['supporter'] = {
                    'types': [self.random_supporter['type'].pk],
                    'other_type': self.NEW_OTHER_TYPE,
                    'investing_level_range': self.NEW_INVESTING_RANGE,
                    'sectors': [self.random_supporter['sector'].pk],
                    'grouped_sectors': [{
                        'group': self.random_supporter['sector_group'].pk,
                        'sectors': self.random_supporter['sectors_from_group'].values_list('pk', flat=True)
                    }],
                    'grouped_locations': [{
                        'group': self.random_supporter['location_group'].pk,
                        'locations': self.random_supporter['locations_from_group'].values_list('pk', flat=True)
                    }],
                    'places': ['valid_google_place_id']
                }
            else:
                payload['supporter'] = {
                    'types': [0, 'invalid-types', False],
                    'other_type': '',
                    'investing_level_range': 100,
                    'sectors': [0, 'invalid-sectors', False],
                    'grouped_sectors': ['invalid-grouped-sectors', 0, {'group': 0, 'sectors': [0]}],
                    'grouped_locations': ['invalid-locations', 0, {'group': 0, 'locations': [0]}],
                    'places': [{'invalid': True}, None],
                }

        if with_company:
            if existing:
                self.random_network = self._get_random_model_instance('viral', 'Network')

                payload['company'] = {
                    'name': self.UPDATED_SUPPORTER_NAME,
                    'networks': [self.random_network.pk],
                    'location': self.SUPPORTER_UPDATED_LOCATION
                }
            elif valid:
                self.random_network = self._get_random_model_instance('viral', 'Network')

                payload['company'] = {
                    'name': self.NEW_SUPPORTER_NAME,
                    'networks': [self.random_network.pk],
                    'location': self.SUPPORTER_NEW_LOCATION
                }
            else:
                payload['company'] = {
                    'name': ['invalid-name'],
                    'location': 'invalid-location',
                    'networks': [0, 'invalid-networks'],
                }

        return payload

    def _payload_with_criteria(self, payload, affiliate, valid=True, with_wrong_questions=False, updated=False):
        question_bundle = affiliate.question_bundles.first()

        if updated:
            question_bundle_questions_pk = question_bundle.questions.values_list('pk', flat=True)
            updated_desired_question = {
                'question': Question.objects.filter(
                    pk__in=question_bundle_questions_pk, question_type__type=QuestionType.NUMERIC).first().pk,
                'desired': {'value': self.UPDATED_CRITERIA_DESIRED_VALUE}}
            payload['criteria'] = [
                updated_desired_question
            ]
        elif with_wrong_questions:
            question_bundle_questions_pk = question_bundle.questions.values_list('pk', flat=True)
            wrong_desired_question = {
                'question': Question.objects.exclude(pk__in=question_bundle_questions_pk).filter(
                    question_type__type=QuestionType.NUMERIC).first().pk,
                'desired': {'value': 1}
            }
            select_question = Question.objects.exclude(pk__in=question_bundle_questions_pk).filter(
                question_type__type=QuestionType.MULTI_SELECT).first()
            wrong_answers_question = {
                'question': select_question.pk,
                'answers': select_question.answer_set.values_list('pk', flat=True)
            }

            payload['criteria'] = [
                wrong_desired_question,
                wrong_answers_question
            ]
        elif valid:
            question_bundle_questions_pk = question_bundle.questions.values_list('pk', flat=True)
            valid_desired_question = {
                'question': Question.objects.filter(
                    pk__in=question_bundle_questions_pk, question_type__type=QuestionType.NUMERIC).first().pk,
                'desired': {'value': self.NEW_CRITERIA_DESIRED_VALUE}}
            select_question = Question.objects.filter(
                pk__in=question_bundle_questions_pk, question_type__type=QuestionType.SINGLE_SELECT).first()
            valid_answers_question = {
                'question': select_question.pk,
                'answers': select_question.answer_set.values_list('pk', flat=True)
            }

            payload['criteria'] = [
                valid_desired_question,
                valid_answers_question
            ]
        else:
            invalid_question = {'question': 0, 'desired': {'value': 0}}
            invalid_desired = {
                'question': question_bundle.questions.filter(question_type__type=QuestionType.NUMERIC).first().pk,
                'desired': 1
            }
            invalid_answers = {
                'question': question_bundle.questions.filter(question_type__type=QuestionType.SINGLE_SELECT).first().pk,
                'answers': [999]
            }

            payload['criteria'] = [
                invalid_question,
                invalid_desired,
                invalid_answers
            ]

        return payload

    def _payload_with_additional_criteria(self, payload, valid=True, updated=False):
        if updated:
            updated_desired_question = {
                'question': Question.objects.filter(question_type__type=QuestionType.NUMERIC).first().pk,
                'desired': {'value': self.UPDATED_CRITERIA_DESIRED_VALUE}}
            payload['additional_criteria'] = [
                updated_desired_question
            ]
        elif valid:
            valid_desired_question = {
                'question': Question.objects.filter(question_type__type=QuestionType.NUMERIC).first().pk,
                'desired': {'value': self.NEW_CRITERIA_DESIRED_VALUE}}
            select_question = Question.objects.filter(question_type__type=QuestionType.SINGLE_SELECT).first()
            valid_answers_question = {
                'question': select_question.pk,
                'answers': select_question.answer_set.values_list('pk', flat=True)
            }

            payload['additional_criteria'] = [
                valid_desired_question,
                valid_answers_question
            ]
        else:
            invalid_question = {'question': 0, 'desired': {'value': 0}}
            invalid_desired = {
                'question': Question.objects.filter(question_type__type=QuestionType.NUMERIC).first().pk,
                'desired': 1
            }
            invalid_answers = {
                'question': Question.objects.filter(question_type__type=QuestionType.SINGLE_SELECT).first().pk,
                'answers': [999]
            }

            payload['additional_criteria'] = [
                invalid_question,
                invalid_desired,
                invalid_answers
            ]

        return payload

    def _payload_with_importances(self, payload, questions=[], valid=True):
        if valid:
            random_weight = self._get_random_model_instance('matching', 'CriteriaWeight')

            payload['importances'] = {
                'level_weight': random_weight.pk,
                'locations_weight': random_weight.pk,
                'sectors_weight': random_weight.pk,
                'questions': [
                    {'question': questions[0].pk, 'criteria_weight': random_weight.pk}
                ]
            }
        else:
            payload['importances'] = {
                'level_weight': 0,
                'locations_weight': False,
                'sectors_weight': None,
                'questions': [
                    {'question': 0, 'criteria_weight': 1},
                    {'question': 1, 'criteria_weight': None}
                ]
            }

        return payload

    def _get_payload(self, selected_options={}):
        """
        Helper method that builds the payload by calling
        a payload method that correspond to the options' key:
        * selected_options: {'with_token': options}
        * calls method: _payload_with_token(options)
        """
        payload = {}

        if len(selected_options):
            for selected_option, option_settings in selected_options.items():
                payload_method_name = '_payload_' + selected_option

                if hasattr(self, payload_method_name):
                    payload_method = getattr(self, payload_method_name)
                    payload = payload_method(
                        payload, **option_settings) if isinstance(option_settings, dict) else payload_method(payload)

        return payload

    def test_pending_registration_without_payload(self):
        # 1 - Test without payload
        response = self.client.post(self.ENDPOINT, format='json')
        errors = response.json()['errors']
        is_missing_email = 'email' in errors and errors['email'][0]['code'] == 'required'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(is_missing_email)

    def test_pending_registration_with_unexisting_token(self):
        # 2.1 - Test with unexisting token
        payload = self._get_payload({'with_email': True, 'with_token': {'value': None}})
        response = self.client.post(self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']
        has_invalid_token = 'token' in errors and errors['token'][0]['code'] == 'invalid_token'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(has_invalid_token)

    def test_pending_registration_only_with_existing_token(self):
        # 2.2 - Test only with existing token
        pending_registration, *created = self._create_pending_registration()
        payload = self._get_payload({'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']
        is_missing_data = errors[0]['code'] == 'missing_data'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(is_missing_data)

    def test_pending_registration_start_with_missing_default_affiliate(self):
        # 3.1 - Test start with missing default affiliate
        payload = self._get_payload({'with_email': True})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        errors = response.json()['errors']
        missing_default_affiliate = errors[0]['code'] == 'missing_default_affiliate'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(missing_default_affiliate)

    def test_pending_registration_start_with_default_affiliate(self):
        # 3.2 - Test start with default affiliate
        default_affiliate = self._create_supporter_affiliate()
        payload = self._get_payload({'with_email': True})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        created_registration_with_default_affiliate = PendingRegistration.objects.filter(
            uid=response.data['token'], affiliate=default_affiliate).exists()
        self.assertTrue(created_registration_with_default_affiliate)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_pending_registration_start_with_existing_affiliate(self):
        # 3.3 - Test start with existing affiliate
        existing_affiliate = self._create_supporter_affiliate(is_default=False)
        payload = self._get_payload({'with_email': True, 'with_affiliate': {'value': existing_affiliate.pk}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        created_registration_with_existing_affiliate = PendingRegistration.objects.filter(
            uid=response.data['token'], affiliate=existing_affiliate).exists()
        self.assertTrue(created_registration_with_existing_affiliate)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_pending_registration_start_with_invalid_email(self):
        # 4.1 - Test start with invalid email
        payload = self._get_payload({'with_email': {'valid': False}})
        response = self.client.post(self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']
        has_invalid_email = 'email' in errors and errors['email'][0]['code'] == 'invalid'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(has_invalid_email)

    def test_pending_registration_start_with_valid_email(self):
        # 4.2 - Test start only with valid email
        self._create_supporter_affiliate()
        payload = self._get_payload({'with_email': True})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        has_registration_token = 'token' in response.data and type(response.data['token']) == str
        self.assertTrue(has_registration_token)

        is_valid_token = PendingRegistration.objects.filter(uid=response.data['token']).exists()
        self.assertTrue(is_valid_token)

        has_created_pending_account = EmailAddress.objects.filter(
            email=self.NEW_EMAIL, user__email=self.NEW_EMAIL).exists()
        self.assertTrue(has_created_pending_account)

    def test_pending_registration_start_with_existing_email(self):
        # 4.3 - Test start with existing email
        self._create_existing_user()
        self._create_supporter_affiliate()
        payload = self._get_payload({'with_email': {'existing': True}})
        response = self.client.post(self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']
        email_already_exists = 'email' in errors and errors['email'][0]['code'] == 'unique'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(email_already_exists)

    def test_pending_registration_update_existing_email(self):
        # 4.4 - Test update existing email
        pending_registration, new_user, new_email, *created = self._create_pending_registration()
        payload = self._get_payload({'with_email': {'updated': True}, 'with_token': {
                                    'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')

        # Reload the updated versions of the new user and email
        new_user.refresh_from_db()
        new_email.refresh_from_db()

        has_updated_user = new_user.email == self.UPDATED_EMAIL and new_user.username == self.UPDATED_EMAIL
        has_updated_email = new_email.email == self.UPDATED_EMAIL

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertTrue(has_updated_user)
        self.assertTrue(has_updated_email)

    def test_pending_registration_password_with_invalid_values(self):
        # 5.1 - Test with invalid password values
        pending_registration, *created = self._create_pending_registration()
        payload = self._get_payload(
            {'with_password': {'valid': False},
             'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']
        has_invalid_password = 'password1' in errors and errors['password1'][0]['code'] == 'invalid'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(has_invalid_password)

    def test_pending_registration_password_with_missing_confirmation(self):
        # 5.2 - Test with missing confirmation
        pending_registration, *created = self._create_pending_registration()
        payload = self._get_payload(
            {'with_password': {'with_confirmation': False},
             'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']
        has_password_mismatch = 'non_field_errors' in errors and \
            errors['non_field_errors'][0]['code'] == 'password_missing_confirmation'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(has_password_mismatch)

    def test_pending_registration_password_with_invalid_confirmation(self):
        # 5.3 - Test with missing confirmation
        pending_registration, *created = self._create_pending_registration()
        payload = self._get_payload(
            {'with_password': {'valid_confirmation': False},
             'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')

        errors = response.json()['errors']
        has_password_mismatch = 'non_field_errors' in errors and \
            errors['non_field_errors'][0]['code'] == 'password_mismatch'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(has_password_mismatch)

    def test_pending_registration_password_with_valid_values(self):
        # 5.4 - Test with valid values
        pending_registration, new_user, *created = self._create_pending_registration()
        payload = self._get_payload(
            {'with_password': True,
             'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        new_user.refresh_from_db()
        self.assertTrue(new_user.check_password(self.NEW_PASSWORD))

    def test_pending_registration_update_existing_password(self):
        # 5.5 - Test updating existing password
        pending_registration, new_user, *created = self._create_pending_registration(with_password=True)
        payload = self._get_payload({'with_password': {'updated': True},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        new_user.refresh_from_db()
        self.assertTrue(new_user.check_password(self.UPDATED_PASSWORD))

    def test_pending_registration_supporter_start_with_incomplete_data(self):
        # 6.1 - Test Supporter start with incomplete data
        pending_registration, *created = self._create_pending_registration()
        payload = self._get_payload({'with_supporter_data': {'with_company': False},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        errors = response.json()['errors']
        missing_data = errors[0]['code'] == 'missing_data'

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(missing_data)

    def test_pending_registration_supporter_start_with_invalid_data(self):
        # 6.2 - Test Supporter start with invalid data
        pending_registration, *created = self._create_pending_registration()
        payload = self._get_payload({'with_supporter_data': {'valid': False},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

        errors = response.json()['errors']

        supporter_errors = errors['supporter']
        supporter_has_invalid_data = {
            # TODO: Add helper method to build these conditions dynamically
            'types_do_not_exist': supporter_errors['types'][0]['code'] == 'does_not_exist',
            'missing_other_type_value': supporter_errors['other_type'][0]['code'] == 'blank',
            'has_invalid_investing_range': supporter_errors['investing_level_range'][0]['code'] == 'invalid',
            'has_invalid_places': supporter_errors['places']['0'][0]['code'] == 'invalid',
            'has_null_places': supporter_errors['places']['1'][0]['code'] == 'null',
            'has_invalid_locations': supporter_errors['grouped_locations'][0]['non_field_errors'][0]['code'] == 'invalid',
            'locations_do_not_exist': supporter_errors['grouped_locations'][2]['locations'][0]['code'] == 'does_not_exist',
            'locations_group_doesnt_exist': supporter_errors['grouped_locations'][2]['group'][0]['code'] == 'does_not_exist',
            'sectors_do_not_exist': supporter_errors['sectors'][0]['code'] == 'does_not_exist',
            'has_invalid_grouped_sectors': supporter_errors['grouped_sectors'][0]['non_field_errors'][0]['code'] == 'invalid',
            'grouped_sectors_do_not_exist': supporter_errors['grouped_sectors'][2]['sectors'][0]['code'] == 'does_not_exist',
            'sectors_group_doesnt_exist': supporter_errors['grouped_sectors'][2]['group'][0]['code'] == 'does_not_exist'
        }
        self.assertTrue(all(bool(condition) for condition in supporter_has_invalid_data.values()))

        company_errors = errors['company']
        company_has_invalid_data = {
            'invalid_name': company_errors['name'][0]['code'] == 'invalid',
            'has_invalid_location': company_errors['location']['non_field_errors'][0]['code'] == 'invalid',
            'networks_do_not_exist': company_errors['networks'][0]['code'] == 'does_not_exist',
        }
        self.assertTrue(all(bool(condition) for condition in company_has_invalid_data.values()))

    @mock.patch('matching.serializers.fetch_google_location')
    def test_pending_registration_supporter_start_with_valid_data(self, location_mock):
        # 6.3 - Test Supporter start with valid data
        location_mock.side_effect = self._get_mocked_google_location
        pending_registration, new_user, new_email, affiliate = self._create_pending_registration()
        payload = self._get_payload({'with_supporter_data': True,
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        has_registration_token = 'token' in response.data and type(response.data['token']) == str
        self.assertTrue(has_registration_token)

        # Check if created Company with network and location
        created_company = apps.get_model('viral', 'Company').objects.get(
            name=self.NEW_SUPPORTER_NAME, networks=self.random_network)
        self.assertEqual(created_company.locations.first().formatted_address,
                         self.SUPPORTER_NEW_LOCATION['formatted_address'])

        # Check if created User Profile with user, company and source
        created_user_profile = apps.get_model(
            'viral', 'UserProfile').objects.get(
            user__email=self.NEW_EMAIL, company=created_company)
        self.assertEqual(created_user_profile.user.pk, pending_registration.user.pk)
        self.assertEqual(created_user_profile.source.pk, affiliate.pk)

        # Check if created Supporter with company name and investing level range
        created_supporter = apps.get_model(
            'matching', 'Supporter').objects.get(
            user_profile__user__email=self.NEW_EMAIL)
        self.assertEqual(created_supporter.name, created_company.name)
        self.assertEqual(created_supporter.investing_level_range, NumericRange(*self.NEW_INVESTING_RANGE))

        # Check if added Supporter Types
        created_type_pk = self.random_supporter['type'].pk
        has_supporter_type = created_supporter.types.filter(pk=created_type_pk).exists()
        has_other_supporter_type = created_supporter.types.filter(name=self.NEW_OTHER_TYPE).exists()
        self.assertTrue(has_supporter_type)
        self.assertTrue(has_other_supporter_type)

        # Check if added Supporter Sectors of Interest
        created_sectors_pks = [self.random_supporter['sector'].pk, *self.random_supporter
                               ['sectors_from_group'].values_list('pk', flat=True)]
        has_sectors_of_interest = created_supporter.sectors.filter(pk__in=created_sectors_pks).exists()
        self.assertTrue(has_sectors_of_interest)

        # Check if added Supporter Locations of Interest
        created_locations_addresses = [location_mock()[0]['formatted_address'], *self.random_supporter
                                       ['locations_from_group'].values_list('formatted_address', flat=True)]
        has_locations_of_interest = created_supporter.locations.filter(
            formatted_address__in=created_locations_addresses).exists()
        self.assertTrue(has_locations_of_interest)

        # Check if created Affiliate Submission with investing level range
        created_submission_with_investing_range = apps.get_model(
            'viral', 'AffiliateProgramSupporterSubmission').objects.filter(
            supporter=created_supporter, affiliate=affiliate,
            investing_level_range=created_supporter.investing_level_range).exists()
        self.assertTrue(created_submission_with_investing_range)

    @mock.patch('matching.serializers.fetch_google_location')
    def test_pending_registration_update_existing_supporter(self, location_mock):
        # 6.4 - Test update existing Supporter data
        location_mock.side_effect = self._get_mocked_google_location
        supporter, company, pending_registration, new_user, new_email, affiliate = self._create_pending_registration(
            with_supporter=True)

        payload = self._get_payload({'with_supporter_data': {'existing': True},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        # Check if updated Company with Network and Location
        company.refresh_from_db()
        self.assertTrue(company.networks.filter(pk=self.random_network.pk).exists())
        self.assertEqual(company.locations.first().formatted_address,
                         self.SUPPORTER_UPDATED_LOCATION['formatted_address'])

        # Check if updated Supporter with company name and investing level range
        supporter.refresh_from_db()
        self.assertEqual(supporter.name, company.name)
        self.assertEqual(supporter.investing_level_range, NumericRange(*self.UPDATED_INVESTING_RANGE))

        # Check if updated Supporter Types
        created_type_pk = self.random_supporter['type'].pk
        has_supporter_type = supporter.types.filter(pk=created_type_pk).exists()
        has_updated_other_type = supporter.types.filter(name=self.UPDATED_OTHER_TYPE).exists()
        has_previous_type = supporter.types.filter(name=self.NEW_OTHER_TYPE).exists()
        self.assertTrue(has_supporter_type)
        self.assertTrue(has_updated_other_type)
        self.assertFalse(has_previous_type)

        # Check if updated Supporter Sectors of Interest
        created_sectors_pks = [self.random_supporter['sector'].pk, *self.random_supporter
                               ['sectors_from_group'].values_list('pk', flat=True)]
        has_sectors_of_interest = supporter.sectors.filter(pk__in=created_sectors_pks).exists()
        has_previous_sectors = supporter.sectors.exclude(pk__in=created_sectors_pks).exists()
        self.assertTrue(has_sectors_of_interest)
        self.assertFalse(has_previous_sectors)

        # Check if updated Supporter Locations of Interest
        created_locations_addresses = [location_mock()[0]['formatted_address'], *self.random_supporter
                                       ['locations_from_group'].values_list('formatted_address', flat=True)]
        has_locations_of_interest = supporter.locations.filter(
            formatted_address__in=created_locations_addresses).exists()
        has_previous_locations = supporter.locations.exclude(
            formatted_address__in=created_locations_addresses).exists()
        self.assertTrue(has_locations_of_interest)
        self.assertFalse(has_previous_locations)

        # Check if updated Affiliate Submission with investing level range
        updated_submission_with_investing_range = apps.get_model(
            'viral', 'AffiliateProgramSupporterSubmission').objects.filter(
            supporter=supporter, affiliate=affiliate,
            investing_level_range=supporter.investing_level_range).exists()
        self.assertTrue(updated_submission_with_investing_range)

    @mock.patch('matching.serializers.fetch_google_location')
    def test_pending_registration_inactive_supporter_start_with_valid_data(self, location_mock):
        # 7.1 - Test inactive Supporter start with valid data
        location_mock.side_effect = self._get_mocked_google_location
        pending_registration, new_user, new_email, affiliate = self._create_pending_registration(
            with_default_affiliate=False)
        payload = self._get_payload({'with_supporter_data': {'with_company': False},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        has_registration_token = 'token' in response.data and type(response.data['token']) == str
        self.assertTrue(has_registration_token)

        # Check if created inactive Supporter with investing level range
        inactive_supporter = apps.get_model(
            'matching', 'Supporter').all_supporters.get(user_profile__isnull=True, email=self.NEW_EMAIL)
        self.assertEqual(inactive_supporter.investing_level_range, NumericRange(*self.NEW_INVESTING_RANGE))

        # Check if added Supporter Types
        created_type_pk = self.random_supporter['type'].pk
        has_supporter_type = inactive_supporter.types.filter(pk=created_type_pk).exists()
        has_other_supporter_type = inactive_supporter.types.filter(name=self.NEW_OTHER_TYPE).exists()
        self.assertTrue(has_supporter_type)
        self.assertTrue(has_other_supporter_type)

        # Check if added Supporter Sectors of Interest
        created_sectors_pks = [self.random_supporter['sector'].pk, *self.random_supporter
                               ['sectors_from_group'].values_list('pk', flat=True)]
        has_sectors_of_interest = inactive_supporter.sectors.filter(pk__in=created_sectors_pks).exists()
        self.assertTrue(has_sectors_of_interest)

        # Check if added Supporter Locations of Interest
        created_locations_addresses = [location_mock()[0]['formatted_address'], *self.random_supporter
                                       ['locations_from_group'].values_list('formatted_address', flat=True)]
        has_locations_of_interest = inactive_supporter.locations.filter(
            formatted_address__in=created_locations_addresses).exists()
        self.assertTrue(has_locations_of_interest)

        # Check if created Affiliate Submission with investing level range
        created_submission_with_investing_range = apps.get_model(
            'viral', 'AffiliateProgramSupporterSubmission').objects.filter(
            supporter=inactive_supporter, affiliate=affiliate,
            investing_level_range=inactive_supporter.investing_level_range).exists()
        self.assertTrue(created_submission_with_investing_range)

    @mock.patch('matching.serializers.fetch_google_location')
    def test_pending_registration_inactive_supporter_update(self, location_mock):
        # 7.2 - Test update inactive Supporter
        location_mock.side_effect = self._get_mocked_google_location
        inactive_supporter, pending_registration, new_user, new_email, affiliate = self._create_pending_registration(
            with_default_affiliate=False,
            with_inactive_supporter=True)

        payload = self._get_payload({'with_supporter_data': {'existing': True, 'with_company': False},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        # Check if updated Supporter with company name and investing level range
        inactive_supporter.refresh_from_db()
        self.assertEqual(inactive_supporter.investing_level_range, NumericRange(*self.UPDATED_INVESTING_RANGE))

        # Check if updated Supporter Types
        created_type_pk = self.random_supporter['type'].pk
        has_supporter_type = inactive_supporter.types.filter(pk=created_type_pk).exists()
        has_updated_other_type = inactive_supporter.types.filter(name=self.UPDATED_OTHER_TYPE).exists()
        has_previous_type = inactive_supporter.types.filter(name=self.NEW_OTHER_TYPE).exists()
        self.assertTrue(has_supporter_type)
        self.assertTrue(has_updated_other_type)
        self.assertFalse(has_previous_type)

        # Check if updated Supporter Sectors of Interest
        created_sectors_pks = [self.random_supporter['sector'].pk, *self.random_supporter
                               ['sectors_from_group'].values_list('pk', flat=True)]
        has_sectors_of_interest = inactive_supporter.sectors.filter(pk__in=created_sectors_pks).exists()
        has_previous_sectors = inactive_supporter.sectors.exclude(pk__in=created_sectors_pks).exists()
        self.assertTrue(has_sectors_of_interest)
        self.assertFalse(has_previous_sectors)

        # Check if updated Supporter Locations of Interest
        created_locations_addresses = [location_mock()[0]['formatted_address'], *self.random_supporter
                                       ['locations_from_group'].values_list('formatted_address', flat=True)]
        has_locations_of_interest = inactive_supporter.locations.filter(
            formatted_address__in=created_locations_addresses).exists()
        has_previous_locations = inactive_supporter.locations.exclude(
            formatted_address__in=created_locations_addresses).exists()
        self.assertTrue(has_locations_of_interest)
        self.assertFalse(has_previous_locations)

        # Check if updated Affiliate Submission with investing level range
        updated_submission_with_investing_range = apps.get_model(
            'viral', 'AffiliateProgramSupporterSubmission').objects.filter(
            supporter=inactive_supporter, affiliate=affiliate,
            investing_level_range=inactive_supporter.investing_level_range).exists()
        self.assertTrue(updated_submission_with_investing_range)

    def test_pending_registration_inactive_supporter_with_company(self):
        # 7.3 - Test submitting inactive Supporter with company
        inactive_supporter, pending_registration, new_user, new_email, affiliate = self._create_pending_registration(
            with_default_affiliate=False,
            with_inactive_supporter=True)

        payload = self._get_payload({'with_supporter_data': {'existing': True},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        # Check if created Company with Network and Location
        created_company = apps.get_model('viral', 'Company').objects.get(
            name=self.UPDATED_SUPPORTER_NAME, networks=self.random_network)
        self.assertTrue(created_company.networks.filter(pk=self.random_network.pk).exists())
        self.assertEqual(created_company.locations.first().formatted_address,
                         self.SUPPORTER_UPDATED_LOCATION['formatted_address'])

        # Check if created User Profile with user, company and source
        created_user_profile = apps.get_model(
            'viral', 'UserProfile').objects.get(
            user__email=self.NEW_EMAIL, company=created_company)
        self.assertEqual(created_user_profile.user.pk, pending_registration.user.pk)
        self.assertEqual(created_user_profile.source.pk, affiliate.pk)

        # Check if updated Supporter with user profile, company name and investing level range
        inactive_supporter.refresh_from_db()
        self.assertEqual(inactive_supporter.user_profile.pk, created_user_profile.pk)
        self.assertEqual(inactive_supporter.name, created_company.name)
        self.assertEqual(inactive_supporter.investing_level_range, NumericRange(*self.UPDATED_INVESTING_RANGE))

        # Check if updated Affiliate Submission with investing level range
        updated_submission_with_investing_range = apps.get_model(
            'viral', 'AffiliateProgramSupporterSubmission').objects.filter(
            supporter=inactive_supporter, affiliate=affiliate,
            investing_level_range=inactive_supporter.investing_level_range).exists()
        self.assertTrue(updated_submission_with_investing_range)

    def test_pending_registration_questionary_with_invalid_criteria(self):
        # 8.1 - Test questionary with invalid criteria
        pending_registration, new_user, new_email, affiliate = self._create_pending_registration()
        payload = self._get_payload({'with_criteria': {'affiliate': affiliate, 'valid': False},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

        errors = response.json()['errors']
        has_invalid_question = any(
            'question' in error and error['question'][0]['code'] == 'does_not_exist' for error in errors['criteria'])
        has_invalid_desired = any('desired' in error and error['desired']
                                  [0]['code'] == 'invalid' for error in errors['criteria'])
        has_invalid_answers = any('answers' in error and error['answers']
                                  [0]['code'] == 'does_not_exist' for error in errors['criteria'])

        self.assertTrue(has_invalid_question)
        self.assertTrue(has_invalid_desired)
        self.assertTrue(has_invalid_answers)

    def test_pending_registration_questionary_with_wrong_question_bundle_questions(self):
        # 8.2 - Test questionary with wrong question bundle questions
        supporter, company, pending_registration, new_user, new_email, affiliate = \
            self._create_pending_registration(with_supporter=True)
        payload = self._get_payload({'with_criteria': {'affiliate': affiliate, 'with_wrong_questions': True},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

        errors = response.json()['errors']
        has_wrong_questions = errors[0]['code'] == 'invalid_questions'
        self.assertTrue(has_wrong_questions)

    def test_pending_registration_questionary_with_valid_criteria(self):
        # 8.3 - Test questionary with valid criteria
        supporter, company, pending_registration, new_user, new_email, affiliate = \
            self._create_pending_registration(with_supporter=True)
        payload = self._get_payload({'with_criteria': {'affiliate': affiliate},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        # Check if created Supporter criteria
        submitted_criteria_filters = Q()
        for criterion in payload['criteria']:
            submitted_criteria_filters |= Q(
                question__pk=criterion['question'],
                desired=criterion['desired']) if 'desired' in criterion else Q(
                question__pk=criterion['question'],
                answers__in=criterion['answers'])
        has_created_criteria = apps.get_model(
            'matching', 'Criteria').objects.filter(
            supporter=supporter).filter(
            submitted_criteria_filters).annotate(
            num_questions=Count('question')).filter(
            num_questions=len(submitted_criteria_filters)).exists()
        self.assertTrue(has_created_criteria)

        # Check if created Affiliate submission
        has_created_submission = apps.get_model(
            'viral', 'AffiliateProgramSupporterSubmission').objects.filter(
            supporter=supporter, affiliate=affiliate, criteria__isnull=False)
        self.assertTrue(has_created_submission)

        # Check if called for profile fields update
        # TODO: Create fixtures of profile fields

    def test_pending_registration_questionary_with_updated_criteria(self):
        # 8.4 - Test questionary with updated criteria
        supporter, criteria, company, pending_registration, new_user, new_email, affiliate = \
            self._create_pending_registration(with_supporter=True, with_criteria=True)
        payload = self._get_payload({'with_criteria': {'affiliate': affiliate, 'updated': True},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        # Check if deleted previous criteria
        previous_criteria_count = Criteria.objects.filter(pk=criteria.pk).count()
        has_deleted_previous_criteria = previous_criteria_count == 0
        self.assertTrue(has_deleted_previous_criteria)

        # Check if created new Supporter criteria
        submitted_criteria_filters = Q()
        for criterion in payload['criteria']:
            submitted_criteria_filters |= Q(
                question__pk=criterion['question'],
                desired=criterion['desired']) if 'desired' in criterion else Q(
                question__pk=criterion['question'],
                answers__in=criterion['answers'])
        has_created_criteria = apps.get_model(
            'matching', 'Criteria').objects.filter(
            supporter=supporter).filter(
            submitted_criteria_filters).annotate(
            num_questions=Count('question')).filter(
            num_questions=len(payload['criteria'])).exists()
        self.assertTrue(has_created_criteria)

        # Check if updated Affiliate submission
        has_created_submission = apps.get_model(
            'viral', 'AffiliateProgramSupporterSubmission').objects.filter(
            supporter=supporter, affiliate=affiliate, criteria__isnull=False)
        self.assertTrue(has_created_submission)

        # Check if called for profile fields update
        # TODO: Create fixtures of profile fields

    def test_pending_registration_questionary_criteria_with_inactive_supporter(self):
        # 8.5 - Test questionary criteria with inactive supporter
        inactive_supporter, pending_registration, new_user, new_email, affiliate = \
            self._create_pending_registration(with_default_affiliate=False, with_inactive_supporter=True)
        payload = self._get_payload({'with_criteria': {'affiliate': affiliate},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        # Check if created Supporter criteria
        submitted_criteria_filters = Q()
        for criterion in payload['criteria']:
            submitted_criteria_filters |= Q(
                question__pk=criterion['question'],
                desired=criterion['desired']) if 'desired' in criterion else Q(
                question__pk=criterion['question'],
                answers__in=criterion['answers'])
        has_created_criteria = apps.get_model(
            'matching', 'Criteria').objects.filter(
            supporter=inactive_supporter).filter(
            submitted_criteria_filters).annotate(
            num_questions=Count('question')).filter(
            num_questions=len(submitted_criteria_filters)).exists()
        self.assertTrue(has_created_criteria)

        # Check if created Affiliate submission
        has_created_submission = apps.get_model(
            'viral', 'AffiliateProgramSupporterSubmission').objects.filter(
            supporter=inactive_supporter, affiliate=affiliate, criteria__isnull=False)
        self.assertTrue(has_created_submission)

        # Check if called for profile fields update
        # TODO: Create fixtures of profile fields

    def test_pending_registration_interests_with_invalid_criteria(self):
        # 9.1 - Test interests with invalid criteria
        pending_registration, new_user, new_email, affiliate = self._create_pending_registration()
        payload = self._get_payload({'with_additional_criteria': {'valid': False},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

        errors = response.json()['errors']
        has_invalid_question = any(
            'question' in error and error['question'][0]['code'] == 'does_not_exist'
            for error in errors['additional_criteria'])
        has_invalid_desired = any('desired' in error and error['desired']
                                  [0]['code'] == 'invalid' for error in errors['additional_criteria'])
        has_invalid_answers = any('answers' in error and error['answers']
                                  [0]['code'] == 'does_not_exist' for error in errors['additional_criteria'])

        self.assertTrue(has_invalid_question)
        self.assertTrue(has_invalid_desired)
        self.assertTrue(has_invalid_answers)

    def test_pending_registration_interests_with_valid_criteria(self):
        # 9.2 - Test interests with valid criteria
        supporter, company, pending_registration, new_user, new_email, affiliate = \
            self._create_pending_registration(with_supporter=True)
        payload = self._get_payload({'with_additional_criteria': True,
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        # Check if created Supporter criteria
        submitted_criteria_filters = Q()
        for criterion in payload['additional_criteria']:
            submitted_criteria_filters |= Q(
                question__pk=criterion['question'],
                desired=criterion['desired']) if 'desired' in criterion else Q(
                question__pk=criterion['question'],
                answers__in=criterion['answers'])
        has_created_criteria = apps.get_model(
            'matching', 'Criteria').objects.filter(
            supporter=supporter).filter(
            submitted_criteria_filters).annotate(
            num_questions=Count('question')).filter(
            num_questions=len(payload['additional_criteria'])).exists()
        self.assertTrue(has_created_criteria)

        # Check if created Affiliate submission
        has_created_submission = apps.get_model(
            'viral', 'AffiliateProgramSupporterSubmission').objects.filter(
            supporter=supporter, affiliate=affiliate, additional_criteria__isnull=False)
        self.assertTrue(has_created_submission)

    def test_pending_registration_interests_with_updated_criteria(self):
        # 9.3 - Test interests with updated criteria
        supporter, additional_criteria, company, pending_registration, new_user, new_email, affiliate = \
            self._create_pending_registration(with_supporter=True, with_additional_criteria=True)
        payload = self._get_payload({'with_additional_criteria': {'updated': True},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        # Check if deleted previous criteria
        previous_criteria_count = Criteria.objects.filter(pk=additional_criteria.pk).count()
        has_deleted_previous_criteria = previous_criteria_count == 0
        self.assertTrue(has_deleted_previous_criteria)

        # Check if created new Supporter criteria
        submitted_criteria_filters = Q()
        for criterion in payload['additional_criteria']:
            submitted_criteria_filters |= Q(
                question__pk=criterion['question'],
                desired=criterion['desired']) if 'desired' in criterion else Q(
                question__pk=criterion['question'],
                answers__in=criterion['answers'])
        has_created_criteria = apps.get_model(
            'matching', 'Criteria').objects.filter(
            supporter=supporter).filter(
            submitted_criteria_filters).annotate(
            num_questions=Count('question')).filter(
            num_questions=len(payload['additional_criteria'])).exists()
        self.assertTrue(has_created_criteria)

        # Check if updated Affiliate submission
        has_created_submission = apps.get_model(
            'viral', 'AffiliateProgramSupporterSubmission').objects.filter(
            supporter=supporter, affiliate=affiliate, additional_criteria__isnull=False)
        self.assertTrue(has_created_submission)

    def test_pending_registration_interests_with_inactive_supporter(self):
        # 9.4 - Test interests criteria with inactive supporter
        inactive_supporter, pending_registration, new_user, new_email, affiliate = \
            self._create_pending_registration(with_default_affiliate=False, with_inactive_supporter=True)
        payload = self._get_payload({'with_additional_criteria': True,
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        # Check if created Supporter criteria
        submitted_criteria_filters = Q()
        for criterion in payload['additional_criteria']:
            submitted_criteria_filters |= Q(
                question__pk=criterion['question'],
                desired=criterion['desired']) if 'desired' in criterion else Q(
                question__pk=criterion['question'],
                answers__in=criterion['answers'])
        has_created_criteria = apps.get_model(
            'matching', 'Criteria').objects.filter(
            supporter=inactive_supporter).filter(
            submitted_criteria_filters).annotate(
            num_questions=Count('question')).filter(
            num_questions=len(payload['additional_criteria'])).exists()
        self.assertTrue(has_created_criteria)

        # Check if created Affiliate submission
        has_created_submission = apps.get_model(
            'viral', 'AffiliateProgramSupporterSubmission').objects.filter(
            supporter=inactive_supporter, affiliate=affiliate, additional_criteria__isnull=False)
        self.assertTrue(has_created_submission)

    def test_pending_registration_importances_with_invalid_weights(self):
        # 10.1 - Test importances with invalid weights
        pending_registration, new_user, new_email, affiliate = self._create_pending_registration()
        payload = self._get_payload({'with_importances': {'valid': False},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

        errors = response.json()['errors']
        has_invalid_level_weight = errors['importances']['level_weight'][0]['code'] == 'does_not_exist'
        has_invalid_locations_weight = errors['importances']['locations_weight'][0]['code'] == 'does_not_exist'
        has_invalid_sectors_weight = errors['importances']['sectors_weight'][0]['code'] == 'null'
        has_invalid_questions_weights = any(
            'question' in error and error['question'][0]['code'] == 'does_not_exist'
            for error in errors['importances']['questions']) and any(
            'criteria_weight' in error and error['criteria_weight'][0]['code'] == 'null'
            for error in errors['importances']['questions'])

        self.assertTrue(has_invalid_level_weight)
        self.assertTrue(has_invalid_locations_weight)
        self.assertTrue(has_invalid_sectors_weight)
        self.assertTrue(has_invalid_questions_weights)

    def test_pending_registration_importances_with_valid_weights(self):
        # 10.2 - Test importances with valid weights
        supporter, criteria, company, pending_registration, new_user, new_email, affiliate = \
            self._create_pending_registration(with_supporter=True, with_criteria=True)
        payload = self._get_payload({'with_importances': {'questions': [criteria.question]},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        # Check if assigned Supporter weights
        supporter.refresh_from_db()
        has_assigned_level_weight = supporter.level_weight.pk == payload['importances']['level_weight']
        has_assigned_locations_weight = supporter.locations_weight.pk == payload['importances']['locations_weight']
        has_assigned_sectors_weight = supporter.sectors_weight.pk == payload['importances']['sectors_weight']
        self.assertTrue(has_assigned_level_weight)
        self.assertTrue(has_assigned_locations_weight)
        self.assertTrue(has_assigned_sectors_weight)

        # Check if assigned Criteria weights
        submitted_importances_filters = Q()
        for criterion in payload['importances']['questions']:
            submitted_importances_filters |= Q(
                question__pk=criterion['question'],
                criteria_weight__pk=criterion['criteria_weight'])
        has_assigned_criteria_weights = apps.get_model(
            'matching', 'Criteria').objects.filter(
            supporter=supporter).filter(
            submitted_importances_filters).annotate(
            num_questions=Count('question')).filter(
            num_questions=len(payload['importances']['questions'])).exists()
        self.assertTrue(has_assigned_criteria_weights)

    def test_pending_registration_importances_with_inactive_supporter(self):
        # 10.3 - Test importances with inactive supporter
        inactive_supporter, criteria, pending_registration, new_user, new_email, affiliate = \
            self._create_pending_registration(with_default_affiliate=False,
                                              with_inactive_supporter=True, with_criteria=True)
        payload = self._get_payload({'with_importances': {'questions': [criteria.question]},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        # Check if assigned Supporter weights
        inactive_supporter.refresh_from_db()
        has_assigned_level_weight = inactive_supporter.level_weight.pk == payload['importances']['level_weight']
        has_assigned_locations_weight = inactive_supporter.locations_weight.pk == payload['importances'][
            'locations_weight']
        has_assigned_sectors_weight = inactive_supporter.sectors_weight.pk == payload['importances']['sectors_weight']
        self.assertTrue(has_assigned_level_weight)
        self.assertTrue(has_assigned_locations_weight)
        self.assertTrue(has_assigned_sectors_weight)

        # Check if assigned Criteria weights
        submitted_importances_filters = Q()
        for criterion in payload['importances']['questions']:
            submitted_importances_filters |= Q(
                question__pk=criterion['question'],
                criteria_weight__pk=criterion['criteria_weight'])
        has_assigned_criteria_weights = apps.get_model(
            'matching', 'Criteria').objects.filter(
            supporter=inactive_supporter).filter(
            submitted_importances_filters).annotate(
            num_questions=Count('question')).filter(
            num_questions=len(payload['importances']['questions'])).exists()
        self.assertTrue(has_assigned_criteria_weights)

    def test_pending_registration_status_with_incomplete_submission(self):
        # 11.1 - Test status with incomplete submission (missing criteria and importances)
        supporter, company, pending_registration, new_user, new_email, affiliate = \
            self._create_pending_registration(with_supporter=True, with_password=True)
        payload = self._get_payload({'with_additional_criteria': True,
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        pending_registration.refresh_from_db()
        self.assertFalse(pending_registration.is_complete)

    def test_pending_registration_status_with_complete_submission(self):
        # 11.2 - Test status with complete submission
        supporter, criteria, company, pending_registration, new_user, new_email, affiliate = \
            self._create_pending_registration(with_supporter=True, with_criteria=True, with_password=True)
        payload = self._get_payload({'with_supporter_data': {'existing': True},
                                     'with_importances': {'questions': [criteria.question]},
                                     'with_token': {'value': pending_registration.uid}})
        response = self.client.post(self.ENDPOINT, payload, format='json')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        pending_registration.refresh_from_db()
        self.assertTrue(pending_registration.is_complete)
