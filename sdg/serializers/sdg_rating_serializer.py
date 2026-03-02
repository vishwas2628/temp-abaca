from rest_framework import serializers
from sdg.models.sdg_rating import SdgRating

class SdgRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SdgRating
        fields = '__all__'