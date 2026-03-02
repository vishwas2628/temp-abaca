from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from sdg.models.sdg_impact import SdgImpact
from sdg.models.sdg_rating import SdgRating
from sdg.models.sdg_reports import SdgReport
from sdg.serializers.sdg_impact_serializer import SdgImpactSerializer
from sdg.serializers.sdg_rating_serializer import SdgRatingSerializer
from sdg.serializers.dg_report_serializer import SdgReportSerializer
from viral.models.affiliate import Affiliate


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getReport(request):
    try:
        param_type = request.query_params.get('type')
        if param_type not in ['affiliate', 'company']:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        

        if param_type == 'affiliate':
            affiliate_id = request.query_params.get('affiliate_id')
            affiliate = Affiliate.objects.get(id=affiliate_id)  # pyright: ignore[reportAttributeAccessIssue]
            return Response(status=status.HTTP_200_OK)
        
        if param_type == 'company':
            company_id = request.query_params.get('companyId')

            report = SdgReport.objects.filter(company_id=company_id).order_by('-created_at').first()  # pyright: ignore[reportAttributeAccessIssue]
            ratings = SdgRating.objects.filter(company_id=company_id).order_by('-created_at').first()  # pyright: ignore[reportAttributeAccessIssue]
            # For each unique sdg_target, pick the latest by updated_at (then created_at)
            impacts = (
                SdgImpact.objects  # pyright: ignore[reportAttributeAccessIssue]
                .filter(company_id=company_id)
                .order_by('sdg_target', '-updated_at', '-created_at')
                .distinct('sdg_target')
            )  # pyright: ignore[reportAttributeAccessIssue]

            report_serializer = SdgReportSerializer(report)
            ratings_serializer = SdgRatingSerializer(ratings)
            impacts_serializer = SdgImpactSerializer(impacts, many=True)
            return Response(
                status=status.HTTP_200_OK,
                data={
                    "report": report_serializer.data if report else None,
                    "ratings": ratings_serializer.data if ratings else None,
                    "impact_scores": impacts_serializer.data,
                },
            )

    except Exception as e:
        print("error: ", e)
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": str(e)})