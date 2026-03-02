from django.contrib.auth import authenticate

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token

from matching.models import QuestionBundle
from viral.models.network import Network
from viral.models.affiliate import Affiliate
from matching.models.supporter import Supporter


class CustomAdminAuth(APIView):
  authentication_classes = [TokenAuthentication]

  def post(self, request):
    user = authenticate(username=request.data.get('username'), password=request.data.get('password'))

    if user is not None:
      token, created = Token.objects.get_or_create(user=user)
      return Response({ 
        'token': token.key, 
        'created': created 
      })

    return Response(
      {'error': 'Invalid credentials'},
      status=status.HTTP_401_UNAUTHORIZED,
    )


class AffiliateView(APIView):
  permission_classes = [IsAuthenticated]
  authentication_classes = [TokenAuthentication]

  def validate_request(self, data):
    if not data.get('name'):
      return Response({'error': 'Name is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not data.get('shortcode'):
      return Response({'error': 'Shortcode is required'}, status=status.HTTP_400_BAD_REQUEST)

    return True

  def post(self, request):
    try:
      data = request.data

      if not self.validate_request(data):
        return Response(
          {'error': 'Invalid request'},
          status=status.HTTP_400_BAD_REQUEST
        )

      networks = Network.objects.filter(id__in=data.get('network_ids'))
      supporters = Supporter.objects.filter(id__in=data.get('supporter_ids'))
      question_bundles = QuestionBundle.objects.filter(id__in=data.get('question_bundle_ids'))

      affiliate = Affiliate.objects.create(
        name=data.get('name'),
        email=data.get('email'),
        shortcode=data.get('shortcode'),
        website=data.get('website'),
        logo=data.get('logo'),
        spreadsheet=data.get('spreadsheet'),
      )

      for network in networks:
        affiliate.networks.add(network)

      for supporter in supporters:
        affiliate.supporters.add(supporter)

      for question_bundle in question_bundles:
        affiliate.question_bundles.add(question_bundle)

      return Response({
        'status': 'success',
        'message': 'Affiliate created successfully',
        'data': {
          'id': affiliate.id,
          'name': affiliate.name,
          'shortcode': affiliate.shortcode,
          'email': affiliate.email,
          'website': affiliate.website,
          'logo': affiliate.logo,
          'spreadsheet': affiliate.spreadsheet,
          'networks': [network.id for network in affiliate.networks.all()],
          'supporters': [supporter.id for supporter in affiliate.supporters.all()],
        }
      })

    except Exception as e:
      return Response(
        {'error': str(e)},
        status=status.HTTP_400_BAD_REQUEST
      )
