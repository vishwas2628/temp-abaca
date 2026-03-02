from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction, DataError, IntegrityError
from sdg.serializers.sdg_save_serializer import SdgSaveSerializer
from sdg.models.sdg_impact import SdgImpact
from sdg.models.sdg_rating import SdgRating

class SaveImpactAndRatingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = SdgSaveSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            company_id = data['company_id']
            company_list_id = data['company_list_id']
            sdg_impacts_data = data['sdg_impacts']

            try:
                with transaction.atomic():
                    # Save Rating
                    SdgRating.objects.create(
                        company_id=company_id,
                        company_list_id=company_list_id,
                        impact_rating=data['impact_rating'],
                        impact_score=data['impact_score'],
                        impact_negative=data['impact_negative'],
                        impact_positive=data['impact_positive'],
                    )

                    # Save Impacts (Loop)
                    impact_objects = [
                        SdgImpact(
                            company_id=company_id,
                            company_list_id=company_list_id,
                            sdg_target=item['sdg_target'],
                            impact_net=item['impact_net'],
                            impact_negative=item['impact_negative'],
                            impact_positive=item['impact_positive'],
                        )
                        for item in sdg_impacts_data
                    ]
                    SdgImpact.objects.bulk_create(impact_objects)

            except DataError:
                return Response(
                    {'error': 'Invalid data format. Please check if your values match the expected data types/length.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except IntegrityError as e:
                return Response(
                    {'error': 'Database integrity error. Check for duplicate entries or missing dependencies.', 'details': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                return Response({'error': 'An unexpected error occurred.', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({'message': 'Impact and rating saved successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)