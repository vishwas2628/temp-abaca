import os
import settings
import urllib.parse

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from grid.models import Category, CategoryLevel, Assessment, Level
from viral.models import Company
from grid.serializers import CategoryLevelSerializer, CategorySerializer, ViralLevelListSerializer, AssessmentSerializer, LevelSerializer, CreateAssessmentSerializer
from django.http import Http404
from django.shortcuts import render

from django.views.generic.base import TemplateView
from django.utils import timezone
from django.utils.translation import gettext as _
from django_weasyprint import WeasyTemplateResponseMixin


class CategoryList(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_queryset(self):
        """
        Optionally restricts the returned categories list
        by filtering against the following fields:
        - group
        """
        queryset = self.queryset.select_related('group').prefetch_related(
            'categorylevel_set', 'categorylevel_set__level').all()

        # Filter by group id
        group_id = self.request.query_params.get('group', None)
        if group_id is not None:
            queryset = queryset.filter(group__id=group_id)

        return queryset

    def get(self, request, *args, **kwargs):
        response = []
        categories = self.get_queryset()

        for category in categories:
            category_dict = CategorySerializer(category).data
            category_dict['categoryDetails'] = CategoryLevelSerializer(category.categorylevel_set, many=True).data
            response.append(category_dict)
        return Response(response)


class LevelList(generics.ListAPIView):
    queryset = Level.objects.all()
    serializer_class = LevelSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        """
        Optionally restricts the returned levels list
        by filtering against the following fields:
        - group
        """
        queryset = self.queryset.all()

        # Filter by group id
        group_id = self.request.query_params.get('group', None)
        if group_id is not None:
            queryset = queryset.filter(group__id=group_id)

        return queryset


class ViralLevelCalculator(generics.CreateAPIView):
    serializer_class = ViralLevelListSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = serializer.create(validated_data=serializer.validated_data)
        return Response(response, status=status.HTTP_200_OK)


class AssessmentToken(APIView):

    def get(self, request, *args, **kwargs):
        token = kwargs['token']
        try:
            assessment = Assessment.objects.get(hash_token=token)
        except Assessment.DoesNotExist:
            return Response({'error': _('Not found')}, status=status.HTTP_404_NOT_FOUND)
        serializer = AssessmentSerializer(assessment)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LatestAssessmentView(generics.RetrieveAPIView):
    serializer_class = AssessmentSerializer
    queryset = Company.objects.all()

    def get(self, request, *args, **kwargs):
        pk = kwargs['pk']
        try:
            company = Company.objects.get(pk=pk)
        except Company.DoesNotExist:
            return Response(
                {'error': _('Company not found'), 'code': 'company_not_found'},
                status=status.HTTP_404_NOT_FOUND)
        try:
            assessment = Assessment.objects.filter(
                evaluated=pk).order_by('-created_at')[0:1].get()
        except Assessment.DoesNotExist:
            return Response(
                {'error': _('Assessment not found'), 'code': 'assessment_not_found'},
                status=status.HTTP_404_NOT_FOUND)
        serializer = AssessmentSerializer(assessment)
        return Response(serializer.data)


class CreateAssessmentView(generics.CreateAPIView):
    serializer_class = CreateAssessmentSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success', True})


class PdfGridView(TemplateView):
    template_name = "milestone-grid.html"

    entrepreneurs_group = 2
    category_params = ["team_level", "prob_level", "val_level",
                       "prod_level", "mkt_level", "bizm_level", "scale_level", "exit_level"]
    levels_classes = ["team", "prob", "val",
                      "prod", "mkt", "bizm", "scale", "exit"]
    levels_funding = ['Friends & Family, Personal Credit', 'Friends & Family, Personal Credit',
                      'Angel, Friends & Family, Personal Credit', 'Angel, Friends & Family', 'VC: Seed, Angel',
                      'VC: Series A, Debt', 'VC: Series B, C', 'VC: Series C, D+', 'Acquirers, IPO']

    def render_to_response(self, context, **response_kwargs):
        # TODO:
        # Get each level with all category_level achievements
        # instead of duplicated levels with each category_level achievements
        descending_levels = Level.objects.filter(group=self.entrepreneurs_group) \
            .select_related('category_level_set') \
            .values('pk', 'value', 'title', 'categorylevel__achievements') \
            .order_by('-value', 'categorylevel__category')

        categories_with_levels = []

        for level in descending_levels:
            # Skip iteration if level was already added to categories_with_levels
            if any(cat_level['level']['value'] == level['value'] for cat_level in categories_with_levels):
                continue

            # Grab all other duplicated levels with different achievements
            same_levels = [same_level for same_level in descending_levels if level['value'] == same_level['value']]
            category_levels = []

            # Populate category levels
            for (index, same_level) in enumerate(same_levels):
                category_levels.append({
                    'achievements': same_level['categorylevel__achievements'],
                    'level': {'value': same_level['value']},
                    'level_class': self.levels_classes[index],
                    'param_value': int(context[self.category_params[index]])
                    if self.category_params[index] in context else 0
                })

            categories_with_levels.append({
                "level": level,
                "level_funding": self.levels_funding[level['value'] - 1],
                "category_levels": category_levels,
            })

        if len(categories_with_levels):
            context['categories_levels'] = categories_with_levels

        return super(PdfGridView, self).render_to_response(context, **response_kwargs)

    def get_context_data(self, **kwargs):
        kwargs['company'] = urllib.parse.unquote(kwargs['company'])
        kwargs['overall_level'] = int(kwargs['overall_level'])
        kwargs['last_updated'] = timezone.now().strftime(
            '%b %d, %Y %-I:%M%p')
        context = super(PdfGridView, self).get_context_data(**kwargs)
        context['base_url'] = os.getenv('API_DOMAIN', 'https://api.abaca.app')
        return context


class PdfGrid(WeasyTemplateResponseMixin, PdfGridView):
    # output rendered as PDF with hardcoded CSS
    pdf_stylesheets = [
        settings.STATICFILES_DIRS[0] + '/css/milestone-grid.print.css',
    ]
    # show pdf in-line (default: True, show download dialog)
    pdf_attachment = False
    # dynamically generate filename using datetime

    def get_pdf_filename(self):
        return 'abaca-{at}.pdf'.format(
            at=timezone.now().strftime('%m%d%Y-%H%M'),
        )
