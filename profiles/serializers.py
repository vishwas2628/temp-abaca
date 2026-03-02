from rest_framework import serializers


class ProfileIDFieldSerializer(serializers.Serializer):
    name = serializers.CharField()
    value = serializers.SerializerMethodField()

    def get_value(self, obj):
        return self.initial_data['value']
