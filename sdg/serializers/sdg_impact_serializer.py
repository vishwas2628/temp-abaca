from rest_framework import serializers
from sdg.models.sdg_impact import SdgImpact

class SdgImpactSerializer(serializers.ModelSerializer):
    class Meta:
        model = SdgImpact
        fields = '__all__'