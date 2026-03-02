from rest_framework import serializers
from sdg.models.sdg_reports import SdgReport

class SdgReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SdgReport
        fields = '__all__'