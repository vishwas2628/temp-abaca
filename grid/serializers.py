import os
import time
from rest_framework import serializers

from shared.mixins import TranslationsSerializerMixin
from grid.models import Category, CategoryLevel, Level, LevelGroup, Assessment
from grid.utils import calculate_viral_level, generate_hash
from viral.utils import save_assessment_to_spreadsheet, send_user_assessment_to_vendors
from viral.models import Company, Affiliate, UserProfile, UserVendor
from rest_framework.exceptions import PermissionDenied


class LevelSerializer(serializers.ModelSerializer):

    class Meta:
        model = Level
        fields = '__all__'


class LevelGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = LevelGroup
        fields = '__all__'


class CategorySerializer(TranslationsSerializerMixin, serializers.ModelSerializer):
    group = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field='slug'
    )

    class Meta:
        model = Category
        fields = '__all__'

    class Translations:
        exclude = ['name', 'description', 'requirements_title', 'abbreviation']


class CategoryLevelSerializer(serializers.ModelSerializer):
    level = LevelSerializer()

    class Meta:
        model = CategoryLevel
        fields = '__all__'


class LevelSerializerField(serializers.SlugRelatedField):
    level = serializers.PrimaryKeyRelatedField(
        queryset=LevelGroup.objects.all())

    def get_queryset(self):
        queryset = self.queryset
        if 'group' in self.root.initial_data:
            group = self.root.initial_data['group']
            queryset = queryset.filter(group__id=group)

        return queryset


class ViralLevelSerializer(serializers.Serializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all())
    level = LevelSerializerField(
        queryset=Level.objects.filter(group=2),
        slug_field='value',
        allow_null=True)


class ViralLevelListSerializer(serializers.Serializer):
    levels = ViralLevelSerializer(many=True)
    group = serializers.PrimaryKeyRelatedField(
        queryset=LevelGroup.objects.all())

    def create(self, validated_data):
        category_group = validated_data.pop('group')
        levels = validated_data.pop('levels')
        level = calculate_viral_level(levels=levels, group=category_group)
        serializer = LevelSerializer(level)
        return {"level": serializer.data}


class AssessmentSerializer(serializers.ModelSerializer):
    level = LevelSerializer()

    class Meta:
        model = Assessment
        fields = '__all__'


class CreateAssessmentSerializer(serializers.Serializer):
    levels = ViralLevelSerializer(many=True)

    def create(self, validated_data):
        levels = validated_data.pop('levels')
        user = self.context['request'].user

        # Get company and affiliate from the logged user
        try:
            user_profile = UserProfile.objects.get(user=user)
            company = user_profile.company
            affiliate = user_profile.source
            if affiliate == None:
                affiliate = Affiliate.objects.get(pk=1)
        except (UserProfile.DoesNotExist, Affiliate.DoesNotExist):
            raise PermissionDenied()
        level = calculate_viral_level(levels=levels)
        hash_token = generate_hash(time.time())
        new_assessment = Assessment.objects.create(
            level=level, data=self.initial_data['levels'], user=user.id, evaluated=company.id, hash_token=hash_token)
        save_assessment_to_spreadsheet(levels, company, user.email,
                                       level.value, affiliate, hash_token)

        user_vendors = UserVendor.objects.filter(user_profile=user_profile)

        if user_vendors.count():
            send_user_assessment_to_vendors(
                user_profile, user_vendors, levels, new_assessment)

        return {}
