import urllib.parse
import requests
import os

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes

base_url = os.getenv('VESTED_IMPACT_API_ENDPOINT')

activities_endpoint = os.getenv('VESTED_IMPACT_ACTIVITIES_ENDPOINT')
industries_endpoint = os.getenv('VESTED_IMPACT_INDUSTRIES_ENDPOINT')
default_headers = {
    'Content-Type': 'application/json',
    'api-key': os.getenv('VESTED_IMPACT_API_TOKEN'),
}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sdg_data(request):
    data_point = request.query_params.get('question_type')
    try:
        endpoint = base_url
        if data_point == 'industries':
            endpoint = f'{endpoint}{industries_endpoint}'

        if data_point == 'activities':
            industry = request.query_params.get('industry')
            endpoint = f'{endpoint}{activities_endpoint}/{urllib.parse.quote(industry)}'

        r = requests.get(endpoint if endpoint else '', headers=default_headers)
        data = r.json()

        if data_point == 'industries':
            return Response(data['industries'])
        if data_point == 'activities':
            return Response(data['activities'])
    except Exception as e:
        print(e)
        pass
