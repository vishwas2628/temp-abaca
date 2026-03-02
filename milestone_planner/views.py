from django.apps import apps
from django.utils.translation import gettext_lazy as _

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.validators import ValidationError

from shared.models import random_uid
from viral.models import UserGuest

from milestone_planner.models import Milestone, MilestonePlanner
from milestone_planner.permissions import (
    IsMilestoneOwnerOrReadOnly,
    IsMilestonePlannerOwnerOrUserWithPermissionsToRead)
from milestone_planner.serializers import (
    CreateMilestoneSerializer, GuestRetrieveMilestonePlannerSerializer,
    ListMilestonePlannersSerializer, ListMilestonesSerializer,
    RetrieveOrUpdateMilestonePlannerSerializer, UpdateMilestoneSerializer)


class ListOrCreateMilestonesView(generics.ListCreateAPIView):
    """
    List or Create Milestones.
    For the moment, this is restricted to entrepreneurs and accessing their own milestones.
    """
    permission_classes = (IsAuthenticated, IsMilestoneOwnerOrReadOnly,)
    queryset = Milestone.objects.select_related(
        'user_profile', 'category_level__category', 'category_level__level', 'category_level__category__group'
    ).prefetch_related('evidence__question', 'evidence__answers').all()

    def get_serializer_class(self):
        if self.request and self.request.method == 'POST':
            return CreateMilestoneSerializer
        return ListMilestonesSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(user_profile__user=self.request.user)

    def perform_create(self, serializer):
        return serializer.save()

    def create(self, request, *args, **kwargs):
        """
        Customize response to use the ListMilestoneSerializer:
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        instance_serializer = ListMilestonesSerializer(instance)
        headers = self.get_success_headers(serializer.data)
        return Response(instance_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class RetrieveUpdateOrDeleteMilestoneView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete Milestone.
    For the moment, this is restricted to entrepreneurs and accessing/editing their own milestones.
    """
    lookup_field = 'uid'
    serializer_class = ListMilestonesSerializer
    permission_classes = (IsAuthenticated, IsMilestoneOwnerOrReadOnly,)
    queryset = Milestone.objects.select_related(
        'user_profile', 'category_level__category', 'category_level__level', 'category_level__category__group'
    ).prefetch_related('evidence__question', 'evidence__answers').all()

    def get_serializer_class(self):
        # Temporary fix for API Docs:
        if not self.request:
            return super().get_serializer_class()

        if self.request.method == 'GET':
            return ListMilestonesSerializer
        return UpdateMilestoneSerializer

    def perform_update(self, serializer):
        return serializer.save()

    def perform_destroy(self, instance):
        if instance.has_milestones_completed_above:
            raise ValidationError(_("You are not allowed to delete this milestone."))
        instance.delete()
        # Sync Assessment with recently deleted milestone:
        apps.get_model('grid', 'Assessment').objects.sync_with_milestone(milestone=instance, created=False)

    def update(self, request, *args, **kwargs):
        """
        Customize response to use the ListMilestoneSerializer:
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_instance = self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        instance_serializer = ListMilestonesSerializer(updated_instance)
        return Response(instance_serializer.data)


class ListMilestonePlannersView(generics.ListAPIView):
    """
    Retrieve all Milestone Planners of the authenticated user.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = ListMilestonePlannersSerializer

    def get_queryset(self):
        return MilestonePlanner.objects.prefetch_related(
            'invited_users', 'invited_guests').filter(
            company__company_profile__user=self.request.user)


class RetrieveOrUpdateMilestonePlannerView(generics.RetrieveUpdateAPIView):
    """
    Retrieve a Milestone Planner (with milestones)
    """
    lookup_field = 'uid'
    permission_classes = (IsMilestonePlannerOwnerOrUserWithPermissionsToRead,)
    queryset = MilestonePlanner.objects.select_related('company').all()

    def _is_owner(self, request):
        milestone_planner = self.get_object() if self._is_logged_user(request) else None
        return bool(milestone_planner) and milestone_planner.company.company_profile.pk == request.user.userprofile.pk

    def _is_logged_user(self, request):
        return hasattr(request, 'user') and request.user.is_authenticated

    def _is_new_invited_user(self, request, milestone_planner):
        return self._is_logged_user(request) and \
            self._is_owner(request) is False and \
            milestone_planner.invited_users.filter(user__pk=request.user.pk).exists() is False

    def _is_guest(self, request):
        guest_email = request.query_params.get('email', None) if hasattr(request, 'query_params') else None
        return not self._is_logged_user(request) and bool(guest_email) and UserGuest.objects.filter(
            email__iexact=guest_email).exists()

    def _is_new_invited_guest(self, request, milestone_planner):
        return self._is_guest(request) and milestone_planner.invited_guests.filter(
            email__iexact=request.query_params.get('email')).exists() is False

    def get_serializer_class(self):
        if self._is_owner(self.request):
            return RetrieveOrUpdateMilestonePlannerSerializer
        return GuestRetrieveMilestonePlannerSerializer

    def retrieve(self, request, *args, **kwargs):
        milestone_planner = self.get_object()

        if self._is_new_invited_user(request, milestone_planner):
            milestone_planner.invited_users.add(request.user.userprofile)
        elif self._is_new_invited_guest(request, milestone_planner):
            user_guest = UserGuest.objects.get(email__iexact=request.query_params.get('email'))
            milestone_planner.invited_guests.add(user_guest)

        serializer = self.get_serializer(milestone_planner)
        return Response(serializer.data)

    def _reset_link(self):
        milestone_planner = self.get_object()

        # Generate a new list UID
        milestone_planner.uid = random_uid()
        self.kwargs[self.lookup_field] = milestone_planner.uid

        # Remove invited users & guests (as they'll loose access to the milestone planner)
        milestone_planner.invited_users.clear()
        milestone_planner.invited_guests.clear()
        milestone_planner.save()

    def _reset_passcode(self):
        milestone_planner = self.get_object()
        milestone_planner.passcode = random_uid()
        milestone_planner.save()

    def patch(self, request, *args, **kwargs):
        with_reset_link = request.query_params.get('reset', False) == 'link'
        with_reset_passcode = request.query_params.get('reset', False) == 'passcode'

        if with_reset_link:
            self._reset_link()

        if with_reset_passcode:
            self._reset_passcode()

        return self.partial_update(request, *args, **kwargs)
