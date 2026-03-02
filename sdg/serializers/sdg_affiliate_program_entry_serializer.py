from rest_framework import serializers

from viral.models import Affiliate, Company, UserProfile
from sdg.models.sdg_affiliate_program_entry import SDGAffiliateProgramEntry
from sdg.models.sdg_response import Response as SDGResponse
from matching.models import Question, Answer


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'id',
            'name',
            'about',
        ]


class AffiliateSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)

    class Meta:
        model = Affiliate
        fields = [
            'id',
            'name',
            'slug',
            'sdg_reports_enabled',
            'company',
            'shortcode',
            'email',
            'company_lists'
        ]


class UserLiteSerializer(serializers.Serializer):
    id = serializers.IntegerField()


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserLiteSerializer(read_only=True)
    company = CompanySerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'id',
            'user',
            'company',
        ]


class SDGQuestionSerializer(serializers.ModelSerializer):
    text = serializers.CharField(
        source='entrepreneur_question',
        read_only=True
    )

    class Meta:
        model = Question
        fields = [
            'id',
            'text',
            'slug',
            'short_name',
        ]


class SDGAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = [
            'id',
            'value',
        ]


class SDGResponseSerializer(serializers.ModelSerializer):
    question = SDGQuestionSerializer(read_only=True)
    answers = SDGAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = SDGResponse
        fields = [
            'id',
            'value',
            'question',
            'answers',
        ]


class SDGAffiliateProgramEntrySerializer(serializers.ModelSerializer):
    affiliate = AffiliateSerializer(read_only=True)
    user_profile = UserProfileSerializer(read_only=True)
    sdg_responses = SDGResponseSerializer(
        source='responses',
        many=True,
        read_only=True
    )

    class Meta:
        model = SDGAffiliateProgramEntry
        fields = [
            'id',
            'affiliate',
            'user_profile',
            'sdg_responses',
            'created_at',
            'updated_at',
        ]