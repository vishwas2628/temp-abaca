from rest_framework import serializers
from viral.models import Company
from company_lists.models import CompanyList

class SdgImpactItemSerializer(serializers.Serializer):
    sdg_target = serializers.FloatField(required=True)
    impact_net = serializers.IntegerField(required=True)
    impact_negative = serializers.IntegerField(required=True)
    impact_positive = serializers.IntegerField(required=True)

class SdgSaveSerializer(serializers.Serializer):
    company_id = serializers.IntegerField(required=True)
    company_list_id = serializers.IntegerField(required=True)

    # SdgRating fields
    impact_rating = serializers.CharField(max_length=255, required=True)
    impact_score = serializers.IntegerField(required=True)
    impact_negative = serializers.IntegerField(required=True)
    impact_positive = serializers.IntegerField(required=True)

    # List of SdgImpact items
    sdg_impacts = SdgImpactItemSerializer(many=True, required=True)
