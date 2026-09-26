"""Authenticated, allowlisted proxy from the web UI to the PDU API (ttne).

The browser cannot always reach the API directly, and the API has no
authentication of its own, so pages talk to it through this view. Only the
method + path combinations in ALLOWED are forwarded.

CSRF: the project runs without Django's CSRF middleware, so state changing
requests must carry the ``X-Requested-With: XMLHttpRequest`` header. A page on
another origin cannot add that header without a CORS preflight, which this
site does not answer, so cross-site form posts are rejected.
"""
import re

import requests
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from app.views import get_pdu_base_urls

_ID = r"\d{1,3}"
_MAC = r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}"

ALLOWED = (
    ("GET", r"outputs"),
    ("GET", r"outputs/data"),
    ("GET", r"outputs/switch-status"),
    ("GET", rf"outputs/{_ID}/data"),
    ("GET", rf"outputs/{_ID}/switch-status"),
    ("PUT", rf"outputs/{_ID}/switch-status"),
    ("GET", r"alarms"),
    ("POST", r"alarms/ack"),
    ("POST", r"alarms/ack-all"),
    ("GET", r"display-config"),
    ("PUT", r"display-config"),
    ("GET", r"settings/license"),
    ("GET", r"settings/pdu-info"),
    ("PUT", r"settings/pdu-info"),
    ("GET", r"settings/system-info"),
    ("GET", r"settings/ntp"),
    ("PUT", r"settings/ntp"),
    ("GET", r"settings/bluetooth"),
    ("PUT", r"settings/bluetooth"),
    ("POST", r"settings/bluetooth/scan/(?:start|stop)"),
    ("POST", rf"settings/bluetooth/devices/{_MAC}/[a-z-]{{1,20}}"),
    ("POST", r"settings/bluetooth/pairing/(?:accept|refuse)"),
    ("GET", r"settings/update-status"),
    ("PUT", r"settings/update-settings"),
    ("POST", r"settings/update-confirm"),
    ("POST", r"settings/ota-check-now"),
    ("GET", r"network/info"),
    ("GET", r"network/services"),
    ("GET", r"network/snmp/display-settings"),
    ("PUT", r"network/snmp/display-settings"),
    ("GET", r"settings/modbus"),
    ("PUT", r"settings/modbus"),
    ("POST", r"settings/(?:start|stop)-modbus"),
    ("GET", r"inputs"),
    ("GET", r"inputs/switches"),
    ("GET", rf"inputs/{_ID}/data"),
)
_COMPILED = tuple((m, re.compile(rf"^{p}$")) for m, p in ALLOWED)

READ_METHODS = ("GET", "HEAD")
TIMEOUT_S = 8
# Only these query parameters are forwarded.
QUERY_ALLOWED = {"refresh"}


def is_allowed(method, path):
    return any(m == method and rx.match(path) for m, rx in _COMPILED)


# The API registers these two collection routes with a trailing slash.
TRAILING_SLASH = {"outputs", "inputs"}


@csrf_exempt
def pdu_proxy(request, path):
    if not request.user.is_authenticated:
        # JSON instead of the login page redirect so scripts can react
        return JsonResponse({"result": "error", "message": "Unauthorized"},
                            status=401)
    path = path.strip("/")
    method = request.method
    if method == "HEAD":
        method = "GET"

    if not is_allowed(method, path):
        return JsonResponse({"result": "error", "message": "Not allowed"},
                            status=404)
    if request.method not in READ_METHODS and \
            request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return JsonResponse({"result": "error", "message": "Forbidden"},
                            status=403)

    params = {k: v for k, v in request.GET.items() if k in QUERY_ALLOWED}
    kwargs = {"params": params, "timeout": TIMEOUT_S, "verify": False}
    if method in ("POST", "PUT") and request.body:
        kwargs["data"] = request.body
        kwargs["headers"] = {"Content-Type": "application/json"}

    api_path = path + "/" if path in TRAILING_SLASH else path
    last_error = None
    for base_url in get_pdu_base_urls():
        try:
            response = requests.request(method, f"{base_url}/{api_path}",
                                        **kwargs)
        except requests.RequestException as ex:
            last_error = ex
            continue
        return HttpResponse(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type",
                                              "application/json"),
        )
    return JsonResponse({"result": "error",
                         "message": f"PDU API unreachable: {last_error}"},
                        status=502)
