from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from sdg.models.sdg_affiliate_program_entry import SDGAffiliateProgramEntry
from sdg.serializers.sdg_affiliate_program_entry_serializer import \
    SDGAffiliateProgramEntrySerializer
from viral.models.affiliate import Affiliate


class SDGAffiliateProgramEntryListAPIView(generics.ListAPIView):
    serializer_class = SDGAffiliateProgramEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        request = self.request

        affiliate_id = (
            self.kwargs.get('affiliate_id')
            or request.query_params.get('affiliate_id')
        )

        company_id = (
            self.kwargs.get('company_id')
            or request.query_params.get('company_id')
        )

        queryset = (
            SDGAffiliateProgramEntry.objects
            .filter(affiliate_id=affiliate_id)
            .select_related(
                'affiliate',
                'affiliate__company',
                'user_profile',
                'user_profile__user',
                'user_profile__company',
            )
            .prefetch_related(
                'responses',
                'responses__question',
                'responses__answers',
            )
            .order_by('-created_at')
        )

        if company_id:
            queryset = queryset.filter(user_profile__company_id=company_id)

        return queryset

    def list(self, request, *args, **kwargs):
        affiliate_id = (
            kwargs.get('affiliate_id')
            or request.query_params.get('affiliate_id')
        )

        if not affiliate_id:
            raise ValidationError({"affiliate_id": "This field is required."})

        try:
            affiliate = Affiliate.objects.only(
                "id", "sdg_reports_enabled"
            ).get(pk=affiliate_id)
        except Affiliate.DoesNotExist:
            raise ValidationError({"affiliate_id": "Invalid affiliate id."})

        if not affiliate.sdg_reports_enabled:
            return Response(
                {
                    "sdg_reports_enabled": False,
                    "message": "SDG reports are disabled for this affiliate."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        return super().list(request, *args, **kwargs)
