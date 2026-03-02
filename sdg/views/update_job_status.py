import os
import datetime
import requests
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAdminUser
from sdg.models.sdg_reports import SdgReport

base_url = os.getenv('SDG_REPORT_SERVICE_ENDPOINT')
check_job_status_endpoint = "/job/{}" # /job/{job_id}
generate_report_url_endpoint = "/generateReportUrl/{}" # /generateReportUrl/{job_id}
default_headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {os.getenv("SDG_REPORT_SERVICE_TOKEN")}',
}

@api_view(['POST'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAdminUser])
def update_job_status(request, *args, **kwargs):
    try:
        param_job_id = request.query_params.get('job_id')
        if not param_job_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        status_endpoint = f"{base_url}{check_job_status_endpoint.format(param_job_id)}"
        status_response = requests.get(status_endpoint, headers=default_headers)
        if status_response.status_code != 200:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        status_response = status_response.json()
        print("status_response: ", status_response)
        if status_response.get('status') == 'completed':
            report_url_endpoint = f"{base_url}{generate_report_url_endpoint.format(param_job_id)}"
            report_url_response = requests.get(report_url_endpoint, headers=default_headers)
            if report_url_response.status_code != 200:
                return Response(status=status.HTTP_400_BAD_REQUEST)

            report_url_response = report_url_response.json()
            print("report_url_response: ", report_url_response)
            report_pdf_url = report_url_response.get('pdfUrl')
            report_xlsx_url = report_url_response.get('excelUel', "")

            print("report_pdf_url: ", report_pdf_url)
            print("report_xlsx_url: ", report_xlsx_url)

            SdgReport.objects.filter(job_id=param_job_id).update( # pyright: ignore[reportAttributeAccessIssue]
                job_status='completed',
                report_pdf_url=report_pdf_url,
                report_xlsx_url=report_xlsx_url,
            )
        else:
            SdgReport.objects.filter(job_id=param_job_id).update( # pyright: ignore[reportAttributeAccessIssue]
                job_status=status_response.get('status'),
                report_pdf_url="",
                report_xlsx_url="",
                report_date=datetime.datetime.now(),
            )

        return Response(status=status.HTTP_200_OK)
    except Exception as e:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": str(e)})
