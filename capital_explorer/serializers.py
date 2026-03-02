from rest_framework.fields import ReadOnlyField
from rest_framework.serializers import ModelSerializer
from capital_explorer.models import CompanyStage, FundingCriteria, FundingSource, FundingStage, FundingType, Submission
from shared.serializers import InvitedGuestSerializer, InvitedUserSerializer
from shared.utils import UIDRelatedFieldSerializer
from viral.models import Company, UserGuest, UserProfile


class FundingTypeSerializer(ModelSerializer):
    class Meta:
        model = FundingType
        fields = ['id', 'name']


class FundingStageSerializer(ModelSerializer):
    class Meta:
        model = FundingStage
        fields = ['id', 'name']


class CompanyStageSerializer(ModelSerializer):
    class Meta:
        model = CompanyStage
        fields = ['id', 'name']


class FundingCriteriaSerializer(ModelSerializer):
    question_type = ReadOnlyField(source='question.question_type.type')

    class Meta:
        model = FundingCriteria
        exclude = ['funding_source', 'created_at', 'updated_at']


class FundingSourceSerializer(ModelSerializer):
    funding_types = FundingTypeSerializer(many=True)
    funding_stages = FundingStageSerializer(many=True)
    company_stages = CompanyStageSerializer(many=True)
    funding_criteria = FundingCriteriaSerializer(many=True, source='fundingcriteria_set')

    class Meta:
        model = FundingSource
        exclude = ['created_at', 'updated_at']


class OwnerSubmissionSerializer(ModelSerializer):
    invited_users = UIDRelatedFieldSerializer(
        many=True,
        serializer=InvitedUserSerializer,
        queryset=UserProfile.objects.all(),
    )
    invited_guests = UIDRelatedFieldSerializer(
        many=True,
        serializer=InvitedGuestSerializer,
        queryset=UserGuest.objects.all(),
    )

    class Meta:
        model = Submission
        fields = ['id', 'uid', 'passcode', 'responses', 'invited_users', 'invited_guests']
        read_only_fields = ['id', 'uid', 'invited_users', 'invited_guests']


class SubmissionCompanySerializer(ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'uid', 'name', 'logo']


class ViewerSubmissionSerializer(ModelSerializer):
    company = SubmissionCompanySerializer(read_only=True)

    class Meta:
        model = Submission
        fields = ['company', 'responses']
        read_only_fields = ['company', 'responses']
