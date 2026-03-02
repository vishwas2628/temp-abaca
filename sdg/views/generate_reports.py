import datetime
import os
import requests
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from viral.models.company import Company
from viral.models.affiliate import Affiliate
from sdg.models.sdg_reports import SdgReport

base_url = os.getenv('SDG_REPORT_SERVICE_ENDPOINT')

generate_report_affiliate_endpoint = "/generateReport/{}"  # /generateReport/{affiliate_id}
generate_report_company_endpoint = "/generateReport/{}/{}"  # /generateReport/{affiliate_id}/{company_id}
default_headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {os.getenv("SDG_REPORT_SERVICE_TOKEN")}',
}


@api_view(['POST'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAdminUser])
def generate_reports(request, *args, **kwargs):
    try:
        print("request: ", request.query_params)
        param_type = request.query_params.get('type')
        if param_type not in ['affiliate', 'company']:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if param_type == 'affiliate':
            affiliate_id = request.query_params.get('affiliate_id')
            affiliate = Affiliate.objects.get(id=affiliate_id)  # pyright: ignore[reportAttributeAccessIssue]
            if not affiliate.sdg_reports_enabled:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST, data={"error": "SDG reports are not enabled for this affiliate"}
                )

            endpoint = f"{base_url}{generate_report_affiliate_endpoint.format(affiliate_id)}"
            r = requests.post(endpoint, headers=default_headers)
            print(r.json())

            if r.status_code != 202 and r.status_code != 200:
                print("error generating affiliate report")
                return Response(status=status.HTTP_400_BAD_REQUEST)

            response = r.json()
            if r.status_code == 200:
                report_status = response.get('status')
                if report_status == 'exists':
                    return Response(status=status.HTTP_200_OK)

            job_id = response.get('jobId')
            SdgReport.objects.create(  # pyright: ignore[reportAttributeAccessIssue]
                affiliate=affiliate,
                job_id=job_id,
                job_status='active',
                report_date=datetime.datetime.now(),
                report_type='affiliate',
                report_pdf_url="",
                report_xlsx_url="",
            )

            return Response(status=status.HTTP_200_OK)

        elif param_type == 'company':
            company_id = request.query_params.get('company_id')
            affiliate_id = request.query_params.get('affiliate_id')

            company = Company.objects.get(id=company_id)  # pyright: ignore[reportAttributeAccessIssue]
            if not company.sdg_reports_enabled:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            endpoint = f"{base_url}{generate_report_company_endpoint.format(affiliate_id, company_id)}"
            r = requests.post(endpoint, headers=default_headers)
            if r.status_code != 202:
                return Response(status=status.HTTP_400_BAD_REQUEST)

            response = r.json()
            job_id = response.get('job_id')

            SdgReport.objects.create(  # pyright: ignore[reportAttributeAccessIssue]
                company=company,
                job_id=job_id,
                job_status='active',
                report_date=datetime.datetime.now(),
                report_type='company',
                report_pdf_url="",
                report_xlsx_url="",
            )

            return Response(status=status.HTTP_200_OK)

    except Exception as e:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": str(e)})
