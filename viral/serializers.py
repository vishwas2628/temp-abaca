import os
import tempfile
import time
import uuid
from datetime import datetime

import bugsnag
import requests
from allauth.account import app_settings as allauth_settings
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from allauth.utils import get_user_model
from django.apps import apps
from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.core import files, signing
from django.core.mail import EmailMessage
from django.db.models import Q
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from rest_auth.registration.serializers import RegisterSerializer
from rest_auth.serializers import LoginSerializer
from rest_framework import exceptions, serializers
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.utils import model_meta
from rest_framework.validators import UniqueValidator

from grid.models import Assessment, Category, LevelGroup
from grid.serializers import AssessmentSerializer, LevelSerializer, ViralLevelSerializer
from grid.utils import calculate_viral_level, generate_hash
from matching.models import Question, QuestionBundle, QuestionType
from matching.models import Response as MatchingResponse
from matching.models import Supporter
from shared.mailjet import (
    sendEntrepreneurCompletedAssessment,
    sendForgotPasswordEmail,
    sendNotificationToAffiliate,
    sendViralLevelRange,
)
from shared.mixins import TranslationsSerializerMixin
from viral.data.geo_countries_continents import GEO_COUNTRIES_CONTINENTS
from viral.mixins.affiliate_submission_in_company_lists_mixin import (
    AffiliateSubmissionInCompanyListsMixin,
)
from viral.models import (
    Affiliate,
    AffiliateProgramEntry,
    AffiliateSubmissionDraft,
    Company,
    Group,
    Location,
    LocationGroup,
    Network,
    Sector,
    Subscription,
    TeamMember,
    UserGuest,
    UserMetadata,
    UserProfile,
    UserVendor,
    Vendor,
)
from viral.signals import finished_affiliate_flow
from viral.utils import (
    add_affiliate_program_entry_to_google_sheet,
    fetch_google_location,
    save_assessment_to_spreadsheet,
    send_user_assessment_to_vendors,
    update_spreadsheet,
    run_new_user_webhook,
)
from shared.models import Logs


class LocationGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationGroup
        fields = '__all__'


class LocationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Location
        exclude = ('groups',)


class GroupSerializer(serializers.ModelSerializer):

    class Meta:
        model = Group
        fields = '__all__'


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ('id', 'uuid', 'name')


class SectorWithGroupsSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True)

    class Meta:
        model = Sector
        fields = '__all__'


class GroupWithSectorsSerializer(serializers.ModelSerializer):
    sectors = SectorSerializer(many=True)
    filtered_sectors = serializers.SerializerMethodField()

    def get_filtered_sectors(self, obj):
        if 'filtered_sectors' in self.context:
            filtered_sectors = self.context['filtered_sectors']

            if len(filtered_sectors):
                results = obj.sectors.filter(
                    pk__in=filtered_sectors).order_by('name')
                return SectorSerializer(results, many=True).data
        return []

    class Meta:
        model = Group
        fields = ('id', 'name', 'filtered_sectors', 'sectors')


class BasicLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ('id', 'formatted_address', 'latitude', 'longitude', 'city',
                  'region', 'region_abbreviation', 'country', 'continent')


class GroupedLocationSerializer(serializers.ModelSerializer):
    locations = BasicLocationSerializer(many=True)
    filtered_locations = serializers.SerializerMethodField()

    def get_filtered_locations(self, obj):
        if 'filtered_locations' in self.context:
            filtered_locations = self.context['filtered_locations']

            if len(filtered_locations):
                results = obj.locations.filter(
                    pk__in=filtered_locations).order_by('formatted_address')
                return BasicLocationSerializer(results, many=True).data
        return []

    class Meta:
        model = LocationGroup
        fields = ('id', 'name', 'filtered_locations', 'locations')


class GooglePlaceSerializer(serializers.Serializer):
    formatted_address = serializers.CharField()
    latitude = serializers.CharField(source='geometry.location.lat')
    longitude = serializers.CharField(source='geometry.location.lng')
    country = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    region_abbreviation = serializers.SerializerMethodField()
    continent = serializers.SerializerMethodField()

    def _get_location_attribute(self, location, meta, attr_value='long_name'):
        address_components = location['address_components']
        for value in address_components:
            if meta in value["types"]:
                return value[attr_value]

        return None

    def get_country(self, location):
        return self._get_location_attribute(location, 'country')

    def get_city(self, location):
        return self._get_location_attribute(location, 'locality')

    def get_region(self, location):
        return self._get_location_attribute(
            location, 'administrative_area_level_1') or self._get_location_attribute(
            location, 'administrative_area_level_2')

    def get_region_abbreviation(self, location):
        return self._get_location_attribute(
            location, 'administrative_area_level_1', 'short_name') or self._get_location_attribute(
            location, 'administrative_area_level_2', 'short_name')

    def get_continent(self, location):
        country_short_name = self._get_location_attribute(
            location, 'country', 'short_name')
        return GEO_COUNTRIES_CONTINENTS[country_short_name] if country_short_name and country_short_name in GEO_COUNTRIES_CONTINENTS else None


class GoogleAutocompleteSerializer(serializers.Serializer):
    description = serializers.CharField()
    place_id = serializers.CharField()


class LocationSearchSerializer(serializers.Serializer):
    grouped_locations = GroupedLocationSerializer(required=False, many=True)
    locations = GoogleAutocompleteSerializer(required=False, many=True)


class NetworkSerializer(serializers.ModelSerializer):
    locations = LocationSerializer(many=True)

    class Meta:
        model = Network
        fields = '__all__'


class AffiliateSerializer(TranslationsSerializerMixin, serializers.ModelSerializer):
    networks = NetworkSerializer(many=True)

    class Meta:
        model = Affiliate
        exclude = ('question_bundles',)

    class Translations:
        exclude = ['summary', 'disclaimer_heading', 'disclaimer_body', 
                   'self_assessment_step_description', 'self_assessment_step_note', 
                   'questions_step_description', 'questions_step_note', 
                   'team_members_step_description', 'team_members_step_note']

class AffiliateProgramEntrySerializer(serializers.Serializer):
    uid = serializers.CharField()
    affiliate = AffiliateSerializer()
    shared_info = serializers.SerializerMethodField()

    def get_shared_info(self, instance):

        shared_info = [1]

        if instance.affiliate.flow_type == Affiliate.PROGRAM:
            shared_info.append(2)
        
        if instance.affiliate.show_team_section:
            shared_info.append(3)
        
        return shared_info

    class Meta:
        model = AffiliateProgramEntry
        fields = '__all__'


class CompanySerializer(serializers.ModelSerializer):
    locations = LocationSerializer(many=True)
    sectors = SectorWithGroupsSerializer(many=True)
    networks = NetworkSerializer(many=True)

    class Meta:
        model = Company
        fields = '__all__'


class CompanySearchSerializer(serializers.ModelSerializer):
    # Needed for the Company Lists users reference:
    user_profile = serializers.CharField(source='company_profile.uid')
    
    class Meta:
        model = Company
        fields = ('uid', 'user_profile', 'name', 'logo')


class PartialCompanySerializer(serializers.ModelSerializer):
    locations = LocationSerializer(many=True)
    sectors = SectorWithGroupsSerializer(many=True)

    class Meta:
        model = Company
        fields = ('id', 'name', 'logo', 'about', 'website', 'email',
                  'founded_date', 'locations', 'sectors', 'type', 'access_hash')


class UserProfileSerializer(serializers.ModelSerializer):
    is_offline = serializers.BooleanField()
    source_type = serializers.IntegerField()

    class Meta:
        model = UserProfile
        fields = '__all__'


class AffiliateSubmissionSerializer(serializers.Serializer):
    uid = serializers.CharField()
    user_profile = UserProfileSerializer()
    affiliate = AffiliateSerializer()
    assessment = AssessmentSerializer()

    def __init__(self, *args, **kwargs):
        super(AffiliateSubmissionSerializer, self).__init__(*args, **kwargs)
        
        if self.instance.affiliate.show_team_section:
            self.fields['team_members'] = serializers.SerializerMethodField()
        if self.instance.affiliate.flow_type == self.instance.affiliate.PROGRAM:
            self.fields['responses'] = serializers.SerializerMethodField()

    def get_team_members(self, instance):
        from matching.serializers import AffiliateSupporterProgramSubmissionTeamMemberResponseSerializer
        
        user = self.context['request'].user
        team_members = instance.team_members or []

        for team_member in team_members:
            responses = []
            # If user is the owner of the submission, return all responses
            if user and instance.user_profile.user == user:
                for response in team_member.get('responses', []):
                    response = MatchingResponse.objects.get(id=response)
                    serializer = AffiliateSupporterProgramSubmissionTeamMemberResponseSerializer(response)
                    responses.append(serializer.data)
            team_member['responses'] = responses
        return team_members
    
    def get_responses(self, instance):
        """
        Order responses by their question's order on its corresponding question bundle

        TODO: Check if there's a way to order responses only through a queryset to improve performance
        """
        from matching.serializers import QuestionBundleResponseWithQuestionSerializer

        ordered_responses_by_question = []

        # Grab ordered questions bundles with its questions
        affiliate_question_bundles = instance.affiliate.question_bundles.prefetch_related(
            'questions').all()

        # Collect responses following the question bundle order
        for question_bundle in affiliate_question_bundles:
            ordered_questions = question_bundle.questions.all()

            for question in ordered_questions:
                question_response = next(
                    (response for response in instance.responses.all() if response.question == question), None)

                if question_response:
                    ordered_responses_by_question.append(question_response)

        return QuestionBundleResponseWithQuestionSerializer(ordered_responses_by_question, many=True).data


class AffiliateSubmissionsListSerializer(serializers.Serializer):
    affiliate = serializers.PrimaryKeyRelatedField(read_only=True)
    uid = serializers.CharField()
    user_profile = serializers.PrimaryKeyRelatedField(
        read_only=True, source='user_profile.uid')
    created_at = serializers.CharField()
    updated_at = serializers.CharField()


class UserProfileSerializerWithCompany(serializers.ModelSerializer):
    is_offline = serializers.BooleanField()
    company = CompanySerializer()

    class Meta:
        model = UserProfile
        fields = '__all__'


class AffiliateQuestionBundleSerializer(serializers.ModelSerializer):
    """
    To avoid a circular import issue:
    -> Added this serializer after the Location and Company serializers
    -> Imported inside this class the Question serializer
    TODO: Isolate serializers in separate files to avoid these problems
    """
    from matching.serializers import QuestionSerializer

    questions = QuestionSerializer(many=True)

    class Meta:
        model = QuestionBundle
        fields = '__all__'


class AffiliateWithQuestionBundleSerializer(serializers.ModelSerializer):
    question_bundles = AffiliateQuestionBundleSerializer(many=True)
    networks = NetworkSerializer(many=True)

    class Meta:
        model = Affiliate
        fields = '__all__'


class UpdateCompanySerializer(serializers.ModelSerializer):

    sectors = serializers.PrimaryKeyRelatedField(
        queryset=Sector.objects.all(), many=True)
    location = LocationSerializer(required=False)

    class Meta:
        model = Company
        fields = ('logo', 'name', 'website', 'sectors', 'location',
                  'email', 'founded_date', 'about', 'networks')

    def update(self, instance, validated_data):
        if 'logo' in validated_data:
            if instance.logo:
                try:
                    os.remove(os.path.join(
                        settings.MEDIA_ROOT, instance.logo.name))
                except FileNotFoundError:
                    pass
        if 'location' in validated_data:
            # Delete old locations
            for location in instance.locations.all():
                location.delete()

            # Replace with new location
            location = Location.objects.create(
                **validated_data.pop('location'))
            instance.locations.add(location)

        info = model_meta.get_field_info(instance)
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                field = getattr(instance, attr)
                field.set(value)
            else:
                setattr(instance, attr, value)
        instance.save()

        if settings.CHARGEBEE and instance.type == Company.SUPPORTER:
            # Update Company details in Chargebee
            try:
                subscription = Subscription.objects.get(user=instance.company_profile.user)
                subscription.update_company_details()
            except Subscription.DoesNotExist:
                pass

        return instance


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = get_user_model
        fields = ('id', 'email')


class UpdateEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128)

    default_error_messages = {
        'already_exists': _("This email is already being used."),
        'password_incorrect': _("Your old password was entered incorrectly. Please enter it again."),
    }

    def create(self, validated_data):
        email = validated_data.get('email')
        password = validated_data.get('password')
        user = self.context['request'].user

        if EmailAddress.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                self.default_error_messages['already_exists'], code='already_exists',)
        if not user.check_password(password):
            raise serializers.ValidationError(
                self.default_error_messages['password_incorrect'], code='password_incorrect',)

        new_email = EmailAddress.objects.create(
            email=email, user=user)
        new_email.send_confirmation()
        return new_email


class CreateCompanySerializer(serializers.ModelSerializer):
    sectors = serializers.PrimaryKeyRelatedField(
        queryset=Sector.objects.all(), many=True)
    location = LocationSerializer()

    class Meta:
        model = Company
        fields = ('name', 'sectors', 'location', 'website')

    def create(self, validated_data):
        company_hash = os.urandom(5).hex()
        company = Company.objects.create(
            name=validated_data['name'], website=validated_data['website'], type=0, access_hash=company_hash)
        company.sectors.set(validated_data.get('sectors'))
        location = Location.objects.create(**validated_data.get('location'))
        company.locations.add(location)
        return company


class RegisterUserSerializer(RegisterSerializer):
    email = serializers.EmailField(required=allauth_settings.EMAIL_REQUIRED, validators=[UniqueValidator(
        queryset=get_user_model().objects.values('email'), lookup='iexact')])
    company = CreateCompanySerializer()
    affiliate = serializers.PrimaryKeyRelatedField(
        queryset=Affiliate.objects.all())

    def save(self, request):
        validated_company = self.validated_data.pop('company')
        validated_affiliate = self.validated_data.pop('affiliate')
        user = super(RegisterUserSerializer, self).save(request)
        company = CreateCompanySerializer.create(
            CreateCompanySerializer(), validated_data=validated_company)
        user_profile = UserProfile.objects.create(
            user=user, company=company, source=validated_affiliate)
        
        if user_profile:
            run_new_user_webhook("New user registration", user_profile)
        
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=128)
    new_password1 = serializers.CharField(max_length=128)
    new_password2 = serializers.CharField(max_length=128)

    default_error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
        'password_incorrect': _("Your old password was entered incorrectly. Please enter it again."),
    }

    def create(self, validated_data):
        old_password = validated_data.get('old_password')
        password1 = validated_data.get('new_password1')
        password2 = validated_data.get('new_password2')
        user = self.context['request'].user

        if user.check_password(old_password):
            if password1 != password2:
                raise serializers.ValidationError(
                    self.default_error_messages['password_mismatch'], code='password_mismatch',)
            else:
                user.set_password(password2)
        else:
            raise serializers.ValidationError(
                self.default_error_messages['password_incorrect'], code='password_incorrect',)
        user.save()
        update_session_auth_hash(self.context['request'], user)
        return user


class SelfAssessmentRegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(validators=[UniqueValidator(
        queryset=get_user_model().objects.values('email'), lookup='iexact')])
    company = CreateCompanySerializer()
    levels = ViralLevelSerializer(many=True)
    group = serializers.PrimaryKeyRelatedField(
        queryset=LevelGroup.objects.all())
    affiliate = serializers.PrimaryKeyRelatedField(
        queryset=Affiliate.objects.all())

    def validate(self, data):
        requested_group = data['group']
        for viral_level in data['levels']:
            if viral_level['category'].group_id != requested_group.id:
                error_message = "Invalid category '{0}' for level group: {1}".format(
                    viral_level['category'].name, requested_group.slug)
                raise serializers.ValidationError(
                    error_message, code='invalid_category',)
        return data

    def create(self, validated_data):
        company_data = validated_data.get('company')
        email = validated_data.get('email')
        group = validated_data.get('group')
        levels = validated_data.get('levels')
        affiliate = validated_data.get('affiliate')

        user = get_user_model().objects.create_user(
            username=email, email=email)
        company = CreateCompanySerializer.create(
            CreateCompanySerializer(), validated_data=company_data)
        EmailAddress.objects.create(user=user, email=email, primary=True)
        UserProfile.objects.create(
            user=user, company=company, source=affiliate)
        level = calculate_viral_level(levels=levels, group=group)
        hash_token = generate_hash(time.time())
        Assessment.objects.create(
            level=level, data=self.initial_data['levels'], user=user.id, evaluated=company.id, hash_token=hash_token)
        base_url = os.getenv('APP_BASE_URL', 'viral.vilcap.com')
        link = 'https://%s/profile/%s' % (base_url, company.id)
        sendEntrepreneurCompletedAssessment(user.email, user, link, group)
        sendNotificationToAffiliate(affiliate.email, user, affiliate, link)
        save_assessment_to_spreadsheet(levels, company, email,
                                       level.value, affiliate, hash_token)
        return {}


class UserRegisterWithAssessmentSerializer(RegisterSerializer):
    email = serializers.EmailField(validators=[UniqueValidator(
        queryset=get_user_model().objects.values('email'), lookup='iexact')])
    company = CreateCompanySerializer()
    levels = ViralLevelSerializer(many=True)
    affiliate = serializers.PrimaryKeyRelatedField(
        queryset=Affiliate.objects.all())

    def save(self, request):
        email = self.validated_data.get('email')
        group = self.validated_data.get('group')
        validated_company = self.validated_data.get('company')
        levels = self.validated_data.get('levels')
        affiliate = self.validated_data.get('affiliate')
        user = super(UserRegisterWithAssessmentSerializer, self).save(request)
        company = CreateCompanySerializer.create(
            CreateCompanySerializer(), validated_data=validated_company)

        user_profile = UserProfile.objects.create(
            user=user, company=company, source=affiliate)
        level = calculate_viral_level(levels=levels)
        hash_token = generate_hash(time.time())
        Assessment.objects.create(
            level=level, data=self.initial_data['levels'], user=user.id, evaluated=company.id, hash_token=hash_token)
        base_url = os.getenv('APP_BASE_URL', 'viral.vilcap.com')
        link = 'https://' + base_url + '/profile/' + str(company.id)
        sendEntrepreneurCompletedAssessment(user.email, user, link, group)
        sendNotificationToAffiliate(affiliate.email, user, affiliate, link)
        save_assessment_to_spreadsheet(levels, company, email, level.value,
                                       affiliate, hash_token)

        if user_profile:
            run_new_user_webhook("New user registration", user_profile)
        
        return user


class CustomLoginSerializer(LoginSerializer):

    def validate(self, attrs):
        username = attrs.get('username')
        email = attrs.get('email')
        password = attrs.get('password')

        user = None

        if 'allauth' in settings.INSTALLED_APPS:
            from allauth.account import app_settings

            # Authentication through email
            if app_settings.AUTHENTICATION_METHOD == app_settings.AuthenticationMethod.EMAIL:
                user = self._validate_email(email, password)

            # Authentication through username
            elif app_settings.AUTHENTICATION_METHOD == app_settings.AuthenticationMethod.USERNAME:
                user = self._validate_username(username, password)

            # Authentication through either username or email
            else:
                user = self._validate_username_email(username, email, password)

        else:
            # Authentication without using allauth
            if email:
                try:
                    username = UserModel.objects.get(
                        email__iexact=email).get_username()
                except UserModel.DoesNotExist:
                    pass

            if username:
                user = self._validate_username_email(username, '', password)

        # Did we get back an active user?
        if user:
            if not user.is_active:
                msg = _('User account is disabled.')
                raise exceptions.ValidationError(msg)
        else:
            msg = _('Unable to log in with provided credentials.')
            raise exceptions.ValidationError(msg)

        # If required, is the email verified?
        if 'rest_auth.registration' in settings.INSTALLED_APPS:
            from allauth.account import app_settings
            if app_settings.EMAIL_VERIFICATION == app_settings.EmailVerificationMethod.MANDATORY:
                email_address = user.emailaddress_set.get(email__iexact=user.email)
                if not email_address.verified:
                    raise serializers.ValidationError(
                        _('E-mail is not verified.'), code='email_not_verified')

        attrs['user'] = user
        return attrs


class RecoverUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password1 = serializers.CharField()
    password2 = serializers.CharField()
    key = serializers.CharField()

    default_error_messages = {
        'key_invalid': _("Invalid key."),
        'password_mismatch': _("The two password fields didn't match."),
    }

    def create(self, validated_data):
        email = validated_data.get('email')
        password1 = validated_data.get('password1')
        password2 = validated_data.get('password2')
        key = validated_data.get('key')

        emailConfirmation = EmailConfirmationHMAC.from_key(key)
        if not emailConfirmation:
            raise serializers.ValidationError(
                self.default_error_messages['key_invalid'], code='key_invalid',)
        if password1 != password2:
            raise serializers.ValidationError(
                self.default_error_messages['password_mismatch'], code='password_mismatch',)

        emailConfirmation.confirm(self.context['request'])
        user = get_user_model().objects.get(email__iexact=emailConfirmation.email_address.email)

        if email != emailConfirmation.email_address.email:
            emailAddress = EmailAddress.objects.create(
                user=user, email=email, verified=True, )
            emailAddress.set_as_primary()
            emailConfirmation.email_address.delete()

        user.set_password(password2)
        user.save()

        return user


class RetrieveUserFromKeySerializer(serializers.Serializer):

    default_error_messages = {
        'key_invalid': _("Invalid key."),
        'no_assessment': _("No assessment for this user was found."),
    }

    def retrieve(self, validated_data):
        key = self.context['key']

        emailConfirmation = EmailConfirmationHMAC.from_key(key)
        if not emailConfirmation:
            raise serializers.ValidationError(
                self.default_error_messages['key_invalid'], code='key_invalid',)

        user = get_user_model().objects.get(email__iexact=emailConfirmation.email_address.email)
        try:
            assessment = Assessment.objects.get(user=user.id)
        except Assessment.DoesNotExist:
            raise serializers.ValidationError(
                self.default_error_messages['no_assessment'], code='no_assessment',)
        levelSerializer = LevelSerializer(assessment.level)
        return {
            'email': user.email,
            'level': levelSerializer.data
        }


class SendResetPasswordEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def create(self, validated_data):
        email = validated_data.get('email')

        try:
            user = get_user_model().objects.get(email__iexact=email)
        except get_user_model().DoesNotExist:
            # Not raising an exception for security reasons
            # as that would tell which users exist on the database
            return email

        key = signing.dumps(obj=user.id)
        link = 'https://' + os.getenv('APP_BASE_URL', 'viral.vilcap.com') + \
            '/auth/reset-password/' + str(user.id) + '/' + key
        sendForgotPasswordEmail(email, user, link)
        return email


class ResetPasswordSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all())
    key = serializers.CharField()
    password1 = serializers.CharField()
    password2 = serializers.CharField()

    default_error_messages = {
        'key_invalid': _("Invalid key."),
        'key_does_not_match': _("Invalid key for the given user."),
        'password_mismatch': _("The two password fields didn't match."),
    }

    def create(self, validated_data):
        user = validated_data.get('user')
        key = validated_data.get('key')
        password1 = validated_data.get('password1')
        password2 = validated_data.get('password2')

        try:
            pk = signing.loads(key)
        except signing.BadSignature:
            raise serializers.ValidationError(
                self.default_error_messages['key_invalid'], code='key_invalid',)
        if user.id != pk:
            raise serializers.ValidationError(
                self.default_error_messages['key_does_not_match'], code='key_does_not_match',)

        if password1 != password2:
            raise serializers.ValidationError(
                self.default_error_messages['password_mismatch'], code='password_mismatch',)
        else:
            user.set_password(password2)
            user.save()

        return user


class ResendEmailVerificationSerializer(serializers.Serializer):
    email = serializers.CharField()

    def create(self, validated_data):
        email = validated_data.get("email")
        email_address = EmailAddress.objects.get(email__iexact=email)
        email_address.send_confirmation(request=self.context['request'])

        return {}


class UserMetadataSerializer(serializers.ModelSerializer):
    user_profile = serializers.PrimaryKeyRelatedField(
        queryset=UserProfile.objects.all())
    key = serializers.CharField()
    value = serializers.CharField()

    class Meta:
        model = UserMetadata
        fields = '__all__'


class VerifyResetPasswordSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all())
    key = serializers.CharField()

    default_error_messages = {
        'key_invalid': _("Invalid key."),
        'key_does_not_match': _("Invalid key for the given user."),
    }

    def create(self, validated_data):
        user = validated_data.get('user')
        key = validated_data.get('key')

        try:
            pk = signing.loads(key)
        except signing.BadSignature:
            raise serializers.ValidationError(
                self.default_error_messages['key_invalid'], code='key_invalid',)
        if user.id != pk:
            raise serializers.ValidationError(
                self.default_error_messages['key_does_not_match'], code='key_does_not_match',)

        return user


class SupportersLevelRangeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    viral_level_range = serializers.CharField()

    def create(self, validated_data):
        email = validated_data.get('email')
        levelRange = validated_data.get('viral_level_range')
        sendViralLevelRange(email, levelRange)
        return {}


class PrimaryRegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(validators=[UniqueValidator(
        queryset=get_user_model().objects.values('email'), lookup='iexact')])
    company = CreateCompanySerializer()
    levels = ViralLevelSerializer(many=True)
    affiliate = serializers.PrimaryKeyRelatedField(
        queryset=Affiliate.objects.all())

    def create(self, validated_data):
        company_data = validated_data.get('company')
        email = validated_data.get('email')
        group = self.validated_data.get('group')
        levels = validated_data.get('levels')
        affiliate = validated_data.get('affiliate')

        user = get_user_model().objects.create_user(
            username=email, email=email)
        company = CreateCompanySerializer.create(
            CreateCompanySerializer(), validated_data=company_data)
        company.email = email
        company.save()
        EmailAddress.objects.create(user=user, email=email, primary=True)
        user_profile= UserProfile.objects.create(
            user=user, company=company, source=affiliate)
        level = calculate_viral_level(levels=levels)
        hash_token = generate_hash(time.time())
        Assessment.objects.create(
            level=level, data=self.initial_data['levels'],
            user=user.id, evaluated=company.id, hash_token=hash_token, state=Assessment.BEGAN_STATE)
        save_assessment_to_spreadsheet(levels, company, email,
                                       level.value, affiliate, hash_token, state=Assessment.BEGAN_STATE)
        
        if user_profile:
            run_new_user_webhook("New user registration", user_profile)
        
        return user


class PendingUserUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    company = UpdateCompanySerializer()
    token = serializers.CharField(max_length=10)

    default_error_messages = {
        'no_user': _("User is not valid."),
        # TODO: Add UniqueValidator for checking the unique email condition
        'unique': {
            'email': [_("This field must be unique.")],
        }
    }

    def update(self, validated_data):
        new_email = validated_data.get('email')
        token = validated_data.get('token')
        company_data = validated_data.get('company')

        try:
            company = Company.objects.get(access_hash=token)
        except Company.DoesNotExist:
            raise serializers.ValidationError(
                self.default_error_messages['no_user'], code='no_user',)

        try:
            user = get_user_model().objects.get(email__iexact=company.email)
            if user.has_usable_password():
                raise serializers.ValidationError(
                    self.default_error_messages['no_user'], code='no_user',)
        except get_user_model().DoesNotExist:
            raise serializers.ValidationError(
                self.default_error_messages['no_user'], code='no_user',)

        updated_company = UpdateCompanySerializer.update(
            UpdateCompanySerializer(), company, validated_data=company_data)

        if new_email != company.email:
            if get_user_model().objects.filter(email__iexact=new_email).exists():
                raise serializers.ValidationError(
                    self.default_error_messages['unique'], code='unique',)

            # Delete previous email
            current_email = EmailAddress.objects.get(
                email__iexact=company.email, user=user)
            current_email.delete()

            # Perform user email change
            email_address = EmailAddress.objects.create(
                email=new_email, user=user)
            email_address.change(
                request=self.context['request'], new_email=new_email)
            email_address.set_as_primary()
            email = email_address.email
            # Save user email
            user.username = email
            user.save()
            # Save company email
            updated_company.email = email
            updated_company.save()

        return user


class PendingUserAssessmentSerializer(serializers.Serializer):
    email = serializers.EmailField()
    levels = ViralLevelSerializer(many=True)
    group = serializers.PrimaryKeyRelatedField(
        queryset=LevelGroup.objects.all())
    affiliate = serializers.PrimaryKeyRelatedField(
        queryset=Affiliate.objects.all())

    default_error_messages = {
        'no_user': _("User is not valid."),
        'invalid_category': _("Invalid category '{0}' for level group: {1}"),
    }

    def validate(self, data):
        requested_group = data['group']
        for viral_level in data['levels']:
            if viral_level['category'].group_id != requested_group.id:
                error_message = self.default_error_messages['invalid_category'].format(
                    viral_level['category'].name, requested_group.slug)
                raise serializers.ValidationError(
                    error_message, code='invalid_category',)
        return data

    def create(self, validated_data):
        self.email = validated_data.get('email')
        self.levels = validated_data.get('levels')
        self.group = validated_data.get('group')
        self.affiliate = validated_data.get('affiliate')

        self.check_if_valid_pending_user()
        self.update_or_create_assessment()

    def check_if_valid_pending_user(self):
        try:
            self.user = self.context['request'].user
            self.user_profile = UserProfile.objects.get(user=self.user)
            self.company = self.user_profile.company

            if self.user.has_usable_password():
                raise serializers.ValidationError(
                    self.default_error_messages['no_user'], code='no_user',)
        except get_user_model().DoesNotExist:
            raise serializers.ValidationError(
                self.default_error_messages['no_user'], code='no_user',)

    def update_or_create_assessment(self):
        self.level = calculate_viral_level(levels=self.levels)

        try:
            self._pending_assessment_update()
        except Assessment.DoesNotExist:
            self._pending_assessment_create()

    def _pending_assessment_update(self):
        pending_assessment = Assessment.objects.get(state=Assessment.BEGAN_STATE, user=self.user.id)
        pending_assessment.level = self.level
        pending_assessment.data = self.initial_data['levels']
        pending_assessment.state = Assessment.FINISHED_STATE

        pending_assessment.save()
        if bool(self.affiliate.spreadsheet):
            update_spreadsheet(self.affiliate, pending_assessment.hash_token, scores=self.levels,
                               viral_level=self.level.value, state=pending_assessment.state)
        else:
            level = calculate_viral_level(levels=self.levels)
            hash_token = generate_hash(time.time())
            save_assessment_to_spreadsheet(self.levels, self.company, self.user.email,
                                           level.value, self.affiliate, hash_token, state=Assessment.FINISHED_STATE)

    def _pending_assessment_create(self):
        level = calculate_viral_level(levels=self.levels)
        hash_token = generate_hash(time.time())
        Assessment.objects.create(
            level=self.level, data=self.initial_data['levels'],
            user=self.user.id, evaluated=self.company.id, hash_token=hash_token, state=Assessment.FINISHED_STATE)
        save_assessment_to_spreadsheet(self.levels, self.company, self.user.email,
                                        level.value, self.affiliate, hash_token, state=Assessment.FINISHED_STATE)


class PendingUserSelfAssessmentSerializer(PendingUserAssessmentSerializer):
    def create(self, validated_data):
        super().create(validated_data)

        self.thank_user()
        self.notify_affiliate()
        self.feed_vendors()
        return {'email': self.user.email, }

    def thank_user(self):
        base_url = os.getenv('APP_BASE_URL', 'viral.vilcap.com')
        link = 'https://%s/profile/%s' % (base_url, self.company.id)
        sendEntrepreneurCompletedAssessment(
            self.user.email, self.user, link, self.group)

    def notify_affiliate(self):
        base_url = os.getenv('APP_BASE_URL', 'viral.vilcap.com')
        link = 'https://%s/profile/v/%s' % (base_url, self.company.access_hash)
        sendNotificationToAffiliate(
            self.affiliate.email, self.user, self.affiliate, link)

    def feed_vendors(self):
        user_vendors = UserVendor.objects.filter(
            user_profile=self.user_profile)

        if user_vendors.count():
            try:
                latest_assessment = Assessment.objects.get(
                    state=Assessment.FINISHED_STATE, user=self.user.id)

                send_user_assessment_to_vendors(
                    self.user_profile, user_vendors, self.levels, latest_assessment)
            except (UserVendor.DoesNotExist, Assessment.DoesNotExist) as error:
                raise error


class PendingUserAssessmentProgramSerializer(PendingUserAssessmentSerializer):
    def create(self, validated_data):
        super().create(validated_data)
        return {'email': self.user.email, }


class PendingUserQuestionBundlesProgramSerializer(AffiliateSubmissionInCompanyListsMixin, serializers.Serializer):
    from matching.serializers import QuestionBundleResponseSerializer

    email = serializers.EmailField()
    responses = QuestionBundleResponseSerializer(many=True)
    affiliate = serializers.PrimaryKeyRelatedField(
        queryset=Affiliate.objects.all())

    default_error_messages = {
        'no_user': _("User is not valid."),
        'invalid_user': _("Invalid user."),
        'missing_assessment': _("Missing self-assessment."),
    }

    def create(self, validated_data):
        self.email = validated_data.get('email')
        self.responses = validated_data.get('responses')
        self.affiliate = validated_data.get('affiliate')

        self._check_if_valid_pending_user()
        self._save_responses()
        self._update_profile_fields()
        self._add_program_entry()
        self._finish_program()
        return {}

    def _check_if_valid_pending_user(self):
        try:
            self.user = get_user_model().objects.get(email__iexact=self.email)
            self.user_profile = UserProfile.objects.get(user=self.user)
            self.company = self.user_profile.company

            if self.user.has_usable_password():
                bugsnag.notify(Exception("Registered user tried to submit a program for pending users."),
                               meta_data={"context": {"email": self.email}})
                raise serializers.ValidationError(
                    self.default_error_messages['invalid_user'], code='invalid_user',)
        except (get_user_model().DoesNotExist, UserProfile.DoesNotExist, Company.DoesNotExist):
            bugsnag.notify(Exception("Unexisting user tried to submit a program for pending users."),
                           meta_data={"context": {"email": self.email}})
            raise serializers.ValidationError(
                self.default_error_messages['no_user'], code='no_user',)

    def _save_responses(self):
        self.matching_responses = []
        for response in self.responses:
            new_response = MatchingResponse.objects.create(
                question=response['question'], user_profile=self.user_profile)
            is_valid_value = 'value' in response and response['value'] and isinstance(
                response['value'], dict) and bool(response['value'])
            is_valid_answers = 'answers' in response and isinstance(
                response['answers'], list) and len(response['answers'])

            if is_valid_value:
                new_response.value = response['value']
            elif is_valid_answers:
                new_response.answers.set(response['answers'])
            new_response.save()
            self.matching_responses.append(new_response)

    def _update_profile_fields(self):
        for response in self.matching_responses:
            profile_field = response.question.profile_field
            has_profile_field_associated = profile_field != None

            if has_profile_field_associated:
                source_model = apps.get_model(
                    app_label=profile_field.app_label, model_name=profile_field.model_name)
                relation_to_profile = profile_field.user_profile_relation
                by_user_profile = {relation_to_profile: self.user_profile}

                try:
                    # Find user's model instance
                    model_instance = source_model.objects.get(
                        **by_user_profile)

                    # TEMP: For now, only text & date values are supported
                    question_type = response.question.question_type.type

                    if response.value:
                        if question_type == QuestionType.FREE_RESPONSE:
                            text_value = str(response.value.get('text', ''))
                            setattr(model_instance, profile_field.field_name, text_value)
                        elif question_type == QuestionType.DATE:
                            date_value = response.value.get('date', datetime.now())
                            date_value = datetime.strptime(date_value, "%Y-%m-%d").date()
                            setattr(model_instance, profile_field.field_name, date_value)
                    elif response.answers.exists():
                        setattr(model_instance, profile_field.field_name, response.answers.all())
                    model_instance.save()
                except Exception as e:
                    bugsnag.notify(Exception("Could not sync profile field."),
                                   meta_data={"context": {"error": e}}
                                   )

    def _add_program_entry(self):
        latest_assessment = Assessment.objects.filter(
            user=self.user.id).order_by('-created_at').first()

        if not latest_assessment:
            raise serializers.ValidationError(
                self.default_error_messages['missing_assessment'], code='missing_assessment',)

        try:
            AffiliateProgramEntry.objects.get(
                affiliate=self.affiliate, assessment=latest_assessment)
        except AffiliateProgramEntry.DoesNotExist:
            program_entry = AffiliateProgramEntry.objects.create(
                affiliate=self.affiliate, user_profile=self.user_profile, assessment=latest_assessment)
            program_entry.responses.set(self.matching_responses)
            program_entry.save()
            self.program_entry = program_entry

    def _finish_program(self):
        """ 
        Emit event of a affiliate flow finished after 
        saving the responses for question bundles
        """
        # TODO: Drop signal usage in favor of mixins
        finished_affiliate_flow.send(sender=self.__class__, user_profile=self.user_profile,
                                     affiliate=self.affiliate, entrepreneur_company=self.company)
        if hasattr(self, "program_entry"):
            add_affiliate_program_entry_to_google_sheet(self.program_entry)
        # TODO: Fix type hinting for affiliate property:
        self.populate_affiliate_company_lists(self.affiliate, self.company)


class PendingUserCreatePasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_email = serializers.EmailField(allow_blank=True)
    new_password1 = serializers.CharField(max_length=128)
    new_password2 = serializers.CharField(max_length=128)

    default_error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
        'no_user': {
            'email': [_("User is not valid.")],
        },
        'already_exists': {
            'email': [_("This email is already being used.")],
        },
        'already_requested': {
            'email': [_("Account awaiting confirmation. Please check your email.")],
        }
    }

    def create(self, validated_data):
        self.email = validated_data.get('email')
        self.new_email = validated_data.get('new_email')
        self.password1 = validated_data.get('new_password1')
        self.password2 = validated_data.get('new_password2')

        self._check_if_valid_pending_user()
        self._update_email_if_changed()
        self._set_password()
        self._update_assessment_state()
        self._send_email_confirmation()

        self.user.save()
        
        return self.user.email

    def _check_if_valid_pending_user(self):
        try:
            self.user = get_user_model().objects.get(email__iexact=self.email)
            self.user_profile = UserProfile.objects.get(user=self.user.id)
            affiliate_id = self.user_profile.source.id if self.user_profile.source else 1
            self.affiliate = Affiliate.objects.get(pk=affiliate_id)
            email_address = self.user.emailaddress_set.get(
                email__iexact=self.user.email)

            if self.user.has_usable_password() and not email_address.verified:
                raise serializers.ValidationError(
                    self.default_error_messages['already_requested'], code='already_requested',)
        except (get_user_model().DoesNotExist, UserProfile.DoesNotExist, Affiliate.DoesNotExist, EmailAddress.DoesNotExist) as error:
            raise serializers.ValidationError(
                self.default_error_messages['no_user'], code='no_user',)

    def _update_email_if_changed(self):
        if len(self.new_email):
            if EmailAddress.objects.filter(email__iexact=self.new_email).exists():
                raise serializers.ValidationError(
                    self.default_error_messages['already_exists'], code='already_exists',)
            else:
                # Delete previous email
                current_email = EmailAddress.objects.get(
                    email=self.email, user=self.user)
                current_email.delete()
                # Perform user email change
                email_address = EmailAddress.objects.create(
                    email=self.new_email, user=self.user)
                email_address.change(
                    request=self.context['request'], new_email=self.new_email)
                email_address.set_as_primary()
                self.email = email_address.email
                self.user.username = email_address.email

    def _set_password(self):
        if self.password1 != self.password2:
            raise serializers.ValidationError(
                self.default_error_messages['password_mismatch'], code='password_mismatch',)
        else:
            self.user.set_password(self.password2)

    def _update_assessment_state(self):
        self.latest_assessment = Assessment.objects.filter(
            state=Assessment.FINISHED_STATE, user=self.user.id).order_by('-created_at').first()

        if self.latest_assessment:
            self.latest_assessment.state = Assessment.REGISTERED_USER_STATE
            self.latest_assessment.save()
            update_spreadsheet(self.affiliate, self.latest_assessment.hash_token,
                               state=self.latest_assessment.state)

    def _send_email_confirmation(self):
        email_address = EmailAddress.objects.get(email__iexact=self.email)
        email_address.send_confirmation(request=self.context['request'])


class CreateVendorCompanySerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    about = serializers.CharField(default=None, required=None)
    website = serializers.URLField(default=None, required=None)

    class Meta:
        model = Company
        fields = ('name', 'website', 'about')

    def create(self, validated_data):
        company_hash = os.urandom(5).hex()
        company = Company.objects.create(
            name=validated_data['name'],
            website=validated_data['website'],
            about=validated_data['about'],
            type=0, access_hash=company_hash)
        return company


class VendorRegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    company = CreateVendorCompanySerializer()
    logo = serializers.URLField(default=None, required=None)
    address = serializers.CharField(
        max_length=512, default=None, required=None)
    vendor_uuid = serializers.IntegerField()
    vendor_user_id = serializers.CharField()
    affiliate = serializers.PrimaryKeyRelatedField(
        queryset=Affiliate.objects.all())

    default_error_messages = {
        'invalid_vendor': _("Vendor is not valid."),
        'unique': {
            'email': [_("This field must be unique.")],
        },
        'invalid_logo': _("Logo is not valid."),
    }

    def create(self, validated_data):
        company_data = validated_data.get('company')
        email = validated_data.get('email')
        affiliate = validated_data.get('affiliate')
        address = validated_data.get('address')
        logo_url = validated_data.get('logo')

        vendor_uuid = validated_data.get('vendor_uuid')
        vendor_user_id = validated_data.get('vendor_user_id')

        response_data = {}

        # Check if Vendor is valid
        try:
            requested_vendor = Vendor.objects.get(uuid=vendor_uuid)
        except Vendor.DoesNotExist:
            raise serializers.ValidationError(
                self.default_error_messages['invalid_vendor'], code='invalid_vendor',)

        # Check if is existing User vendor
        try:
            existing_user_vendor = UserVendor.objects.get(
                user_id=vendor_user_id, user_vendor=requested_vendor)
            existing_profile = existing_user_vendor.user_profile

            if existing_profile.user.has_usable_password():
                response_data['path'] = '/auth/login'
                response_data['params'] = {
                    'email': existing_profile.user.email
                }
            else:
                response_data['path'] = '/entrepreneurs'
                response_data['params'] = {
                    'a': affiliate.id,
                    'token': existing_profile.company.access_hash,
                    'l': 1
                }
            return response_data
        except UserVendor.DoesNotExist:
            pass

        # Check if vendor user exists by email
        try:
            user = get_user_model().objects.filter(email__iexact=email).first()
            user_profile = UserProfile.objects.get(user=user)
            user_vendors = UserVendor.objects.filter(user_profile=user_profile)

            if user_vendors.count():
                # Check if user comes from a new vendor
                if user_vendors.exclude(user_id=vendor_user_id).count():
                    UserVendor.objects.create(
                        user_id=vendor_user_id, user_vendor=requested_vendor, user_profile=user_profile)
                response_data['path'] = '/auth/login'
                response_data['params'] = {
                    'email': email
                }
                return response_data
            else:
                raise serializers.ValidationError(
                    self.default_error_messages['unique'], code='unique',)

        except (get_user_model().DoesNotExist, UserProfile.DoesNotExist):
            # Can proceed to creating new vendor user after previous checks
            pass

        company = CreateVendorCompanySerializer.create(
            CreateVendorCompanySerializer(), validated_data=company_data)

        if logo_url:
            response = requests.head(logo_url, allow_redirects=True)
            filesize = str(response.headers.get('content-length', -1))
            has_valid_filesize = filesize.isnumeric() and int(filesize) <= settings.SAFE_EXTERNAL_FILE_SIZE
            mimetype = response.headers.get('content-type', '')
            has_valid_mimetype = 'image' in mimetype

            if not has_valid_mimetype or not has_valid_filesize:
                self.fail('invalid_logo')

            response = requests.get(logo_url, stream=True)

            if response.status_code == requests.codes.ok:
                file_name = f'{str(uuid.uuid4())}.jpeg'
                tmp_file = tempfile.NamedTemporaryFile()

                for block in response.iter_content(1024 * 100):
                    # If no more file then stop
                    if not block:
                        break
                    # Write image block to temporary file
                    tmp_file.write(block)
                # Save file on company logo
                company.logo.save(file_name, files.File(tmp_file))
            else:
                bugsnag.notify(Exception("Could not fetch vendor users' logo"),
                               meta_data={"context": {
                                   "logo_url": logo_url, "company_id": company.id}}
                               )

        if address and len(address):
            found_location = fetch_google_location(address)

            if found_location:
                location_address = found_location[0]
                location = Location.objects.create(
                    latitude=location_address['geometry']['location']['lat'],
                    longitude=location_address['geometry']['location']['lng'],
                    formatted_address=location_address['formatted_address'])
                company.locations.add(location)
            else:
                bugsnag.notify(Exception("Could not fetch vendor users' address"),
                               meta_data={"context": {
                                   "address": address, "company_id": company.id}}
                               )

        user = get_user_model().objects.create_user(
            username=email, email=email)
        EmailAddress.objects.create(user=user, email=email, primary=True)
        user_profile = UserProfile.objects.create(
            user=user, company=company, source=affiliate)
        user_vendor = UserVendor.objects.create(
            user_id=vendor_user_id, user_vendor=requested_vendor, user_profile=user_profile)

        company.email = email
        company.save()

        response_data['path'] = '/entrepreneurs'
        response_data['params'] = {
            'a': affiliate.id,
            'token': company.access_hash,
            'l': 1
        }

        return response_data


class ProgramAssessmentSerializer(serializers.Serializer):
    levels = ViralLevelSerializer(many=True)
    group = serializers.PrimaryKeyRelatedField(
        queryset=LevelGroup.objects.all())
    affiliate = serializers.PrimaryKeyRelatedField(
        queryset=Affiliate.objects.all())

    default_error_messages = {
        'no_user': _("User is not valid."),
        'invalid_category': _("Invalid category '{0}' for level group: {1}"),
    }

    def validate(self, data):
        requested_group = data['group']
        for viral_level in data['levels']:
            if viral_level['category'].group_id != requested_group.id:
                error_message = self.default_error_messages['invalid_category'].format(
                    viral_level['category'].name, requested_group.slug)
                raise serializers.ValidationError(
                    error_message, code='invalid_category',)
        return data

    def create(self, validated_data):
        self.affiliate = validated_data.get('affiliate')
        self.user = self.context['request'].user
        self._find_user_profile()

        self.levels = validated_data.get('levels')
        self._create_assessment()
        return {}

    def _find_user_profile(self):
        try:
            self.user_profile = UserProfile.objects.get(user=self.user)
            self.company = self.user_profile.company
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError(
                self.default_error_messages['no_user'], code='no_user',)

    def _create_assessment(self):
        level = calculate_viral_level(levels=self.levels)
        hash_token = generate_hash(time.time())
        new_assessment = Assessment.objects.create(
            level=level, data=self.initial_data['levels'],
            user=self.user.id, evaluated=self.company.id, hash_token=hash_token)
        save_assessment_to_spreadsheet(self.levels, self.company, self.user.email,
                                       level.value, self.affiliate, hash_token)


class ProgramQuestionBundlesSerializer(AffiliateSubmissionInCompanyListsMixin, serializers.Serializer):
    from matching.serializers import QuestionBundleResponseSerializer

    responses = QuestionBundleResponseSerializer(many=True)
    affiliate = serializers.PrimaryKeyRelatedField(
        queryset=Affiliate.objects.all())

    team_members = serializers.JSONField(required=False)

    default_error_messages = {
        'no_user': _("User is not valid."),
    }

    def create(self, validated_data):
        self.affiliate = validated_data.get('affiliate')
        self.user = self.context['request'].user
        self._find_user_profile()

        self.responses = validated_data.get('responses')
        self._save_responses()
        self._update_profile_fields()
        self.team_members = validated_data.get('team_members')
        self._add_program_entry()
        self._finish_program()
        return {}

    def _find_user_profile(self):
        try:
            self.user_profile = UserProfile.objects.get(user=self.user)
            self.company = self.user_profile.company
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError(
                self.default_error_messages['no_user'], code='no_user',)

    def _save_responses(self):
        self.matching_responses = []
        for response in self.responses:
            new_response = MatchingResponse.objects.create(
                question=response['question'],
                user_profile=self.user_profile,
                team_member=response.get('team_member', None)
            )
            is_valid_value = 'value' in response and response['value'] and isinstance(
                response['value'], dict) and bool(response['value'])
            is_valid_answers = 'answers' in response and isinstance(
                response['answers'], list) and len(response['answers'])

            if is_valid_value:
                new_response.value = response['value']
            elif is_valid_answers:
                new_response.answers.set(response['answers'])
            new_response.save()
            self.matching_responses.append(new_response)

    def _update_profile_fields(self):
        for response in self.matching_responses:
            profile_field = response.question.profile_field
            has_profile_field_associated = profile_field != None

            if has_profile_field_associated:
                source_model = apps.get_model(
                    app_label=profile_field.app_label, model_name=profile_field.model_name)
                relation_to_profile = profile_field.user_profile_relation
                by_user_profile = {relation_to_profile: self.user_profile}

                try:
                    # Find user's model instance
                    model_instance = source_model.objects.get(
                        **by_user_profile)

                    # TEMP: For now, only text and date values are supported
                    question_type = response.question.question_type.type

                    if response.value:
                        if question_type == QuestionType.FREE_RESPONSE:
                            text_value = str(response.value.get('text', ''))
                            setattr(model_instance,
                                    profile_field.field_name, text_value)
                        elif question_type == QuestionType.DATE:
                            date_value = response.value.get(
                                'date', datetime.now())
                            date_value = datetime.strptime(
                                date_value, "%Y-%m-%d").date()
                            setattr(model_instance,
                                    profile_field.field_name, date_value)
                    elif response.answers.exists():
                        setattr(model_instance,
                                profile_field.field_name, response.answers.all())
                    model_instance.save()
                except Exception as e:
                    bugsnag.notify(Exception("Could not sync profile field."),
                                   meta_data={"context": {"error": e}}
                                   )

    def _add_program_entry(self):
        latest_assessment = Assessment.objects.filter(
            user=self.user.id).order_by('-created_at').first()
        try:
            AffiliateProgramEntry.objects.get(affiliate=self.affiliate, assessment=latest_assessment)
        except AffiliateProgramEntry.DoesNotExist:
            program_entry = AffiliateProgramEntry.objects.create(
                affiliate=self.affiliate,
                user_profile=self.user_profile,
                assessment=latest_assessment,
                team_members=self.team_members,
            )
            program_entry.responses.set(self.matching_responses)
            program_entry.save()
            self.program_entry = program_entry

    def _finish_program(self):
        """ 
        Emit event of a affiliate flow finished after 
        saving the responses for question bundles
        """
        # TODO: Drop signal usage in favor of mixins
        finished_affiliate_flow.send(sender=self.__class__, user_profile=self.user_profile,
                                     affiliate=self.affiliate, entrepreneur_company=self.company)
        if hasattr(self, "program_entry"):
            add_affiliate_program_entry_to_google_sheet(self.program_entry)
        # TODO: Fix type hinting for affiliate property:
        self.populate_affiliate_company_lists(self.affiliate, self.company)


class VendorCompanySerializer(serializers.Serializer):
    Abaca_ID = serializers.IntegerField(source='company.id')
    uid = serializers.CharField(source='company.uid')
    company_name = serializers.CharField(source='company.name')
    email = serializers.CharField(source='company.email')
    website = serializers.CharField(source='company.website')
    description = serializers.CharField(source='company.about')
    logo = serializers.ImageField(
        source='company.logo', use_url=True, allow_null=True, required=False)
    location = serializers.SerializerMethodField(
        method_name='get_first_location')
    created_at = serializers.DateTimeField(source='company.created_at')
    registration_date = serializers.DateTimeField(source='user.date_joined')
    last_session = serializers.DateTimeField(source='user.last_login')

    def get_first_location(self, obj):
        first_location = obj.company.locations.first()

        if first_location is None:
            return ""

        serializer = LocationSerializer(instance=first_location)
        return serializer.data


class VendorEntrepreneurSerializer(VendorCompanySerializer):
    sectors = serializers.SerializerMethodField()
    assessments = serializers.SerializerMethodField()

    def get_sectors(self, obj):
        if not obj.company.sectors.count():
            return None

        return list(
            map(lambda sector: sector.name, obj.company.sectors.all()))

    def get_assessments(self, obj):
        latest_assessment = Assessment.objects.filter(
            user=obj.id).order_by('-created_at').first()

        assessments = {}
        assessment_key = 'Venture Investment Level'
        assessment_level = latest_assessment.level.value if latest_assessment else 0

        if latest_assessment:
            assessments[assessment_key] = {
                'created_at': latest_assessment.created_at,
                'Level': assessment_level
            }
            for value in latest_assessment.data:
                level = value.get('level') or 0
                category = Category.objects.get(
                    pk=value.get('category'))

                if level != None and category:
                    assessments[assessment_key][category.name] = level
        return assessments


class VendorSupporterSerializer(VendorCompanySerializer):
    supporter = serializers.SerializerMethodField()

    def get_supporter(self, obj):
        try:
            supporter = Supporter.objects.get(user_profile=obj.id)

            investing_level_range = [
                supporter.investing_level_range.lower, supporter.investing_level_range.upper]
            locations = LocationSerializer(supporter.locations, many=True)
            sectors = list(
                map(lambda sector: sector.name, supporter.sectors.all()))

            return {
                'investing_level_range': investing_level_range,
                'sectors_of_interest': sectors,
                'locations_of_interest': locations.data,
            }
        except Supporter.DoesNotExist:
            return None


class UserGuestSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)

    class Meta:
        model = UserGuest
        fields = ('uid', 'name', 'email')

    def create(self, validated_data):
        user, created = UserGuest.objects.get_or_create(
            email__iexact=validated_data.get('email'),
            defaults={
                'email': validated_data.get('email'),
                'name': validated_data.get('name')
            }
        )

        return user


class TeamMemberResponseSerializer(serializers.ModelSerializer):

    class Meta:
        model = MatchingResponse
        exclude = ['user_profile', 'created_at', 'updated_at', 'team_member']


class TeamMemberSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    responses = TeamMemberResponseSerializer(many=True, required=False)

    class Meta:
        model = TeamMember
        exclude = ['company']

    def create(self, validated_data):
        team_member, created = TeamMember.objects.update_or_create(
            id=validated_data.get('id'),
            defaults={
                'company': validated_data.get('user_profile').company,
                'first_name': validated_data.get('first_name'),
                'last_name': validated_data.get('last_name'),
                'email': validated_data.get('email'),
                'position': validated_data.get('position'),
                'is_active': True,
            }
        )

        for response_data in validated_data.get('responses', []):
            response = MatchingResponse.objects.create(
                team_member=team_member,
                user_profile=validated_data.get('user_profile'),
                question=response_data.get('question'),
                value=response_data.get('value'),
            )
            response.answers.set(response_data.get('answers', []))

        return team_member

class AffiliateSubmissionDraftSerializer(serializers.ModelSerializer):
    affiliate_id = serializers.IntegerField(required=True)
    
    class Meta:
        model = AffiliateSubmissionDraft
        fields = ['id', 'affiliate_id', 'data', 'created_at', 'updated_at']

    def _run_webhook(self, draft):
        try:
            affiliate = draft.affiliate
            company = draft.user.userprofile.company

            data = {
                'draft_id': str(draft.id),
                'submitted_at': str(draft.created_at),
                'Abaca_ID': company.id,
                'Abaca_profile': 'https://' + os.getenv('APP_BASE_URL', 'my.abaca.app') + '/profile/v/' + company.access_hash,
                'affiliate_id': affiliate.id,
                'affiliate_name': affiliate.name,
                'company_uid': company.uid,
                'company_name': company.name,
                'email': company.email,
                'website': company.website,
                'location': company.locations.values(
                    'formatted_address', 'latitude', 'longitude', 'city', 'region',
                    'region_abbreviation', 'country', 'continent').first(),
                'sectors': list(map(lambda sector: sector.name, company.sectors.all())),
                'data': draft.data
            }

            # Hardcoded URL as requested by the client
            # https://pixelmatters.slack.com/archives/CAGP5U9NV/p1681891699527809?thread_ts=1681490912.738599&cid=CAGP5U9NV
            webhook_response = requests.post('https://hook.us1.make.com/66fvzcw6a412rica59d2r1dfc963c43u', json=data)
            log_data = {
                'status': webhook_response.status_code,
                'headers': webhook_response.headers,
                'request': {
                    'url': webhook_response.request.url,
                    'headers': webhook_response.request.headers,
                    'method': webhook_response.request.method,
                    'body': webhook_response.request.body
                }
            }

            Logs.objects.create(
                slug='webhook',
                level='info' if webhook_response.ok else 'error',
                log=log_data
            )
        except Exception as exception:
            bugsnag.notify(
                Exception("Failed running affiliate draft webhook."),
                metadata={"draft": draft, "exception": exception}
            )


    def create(self, validated_data):
        draft, created = AffiliateSubmissionDraft.objects.update_or_create(
            user=validated_data.get('user', None),
            affiliate_id=validated_data.get('affiliate_id', None),
            defaults={'data': validated_data.get('data', None)})
        
        if created:
            self._run_webhook(draft)

        return draft
    

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['customer_id', 'subscription_id', 'plan_id', 'start_date', 'renewal_date']