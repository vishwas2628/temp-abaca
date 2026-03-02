import bugsnag
import json
import settings

from django.http import HttpResponseForbidden

from viral.models import Vendor


class VendorMiddleware:
    """
    Check if a request submitting data on a vendor
    endpoint has the appropriate credentials (uuid, origin).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        is_vendor_endpoint = request.path.startswith("/vendor/")

        if is_vendor_endpoint and request.method == 'POST' and request.body:
            origin = request.headers.get('Origin', None)
            payload = request.POST or json.loads(request.body)
            vendor_uuid = payload.get('vendor_uuid', None)

            try:
                vendor = Vendor.objects.get(uuid=vendor_uuid)
                # Ensure that on the live environment we have a valid origin:
                if settings.IS_LIVE_ENVIRONMENT:
                    assert origin in vendor.cors_origins
            except Vendor.DoesNotExist:
                bugsnag.notify(Exception("Request from a unexisting vendor."),
                               meta_data={"context": {"vendor_uuid": vendor_uuid}})
                return HttpResponseForbidden()
            except Exception:
                bugsnag.notify(Exception("Request from an invalid origin."),
                               meta_data={"context": {"vendor_uuid": vendor_uuid, "origin": origin}})
                return HttpResponseForbidden()

        return None
