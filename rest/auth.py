from rest_framework import exceptions
from rest_framework.authentication import SessionAuthentication


class AjaxSessionAuthentication(SessionAuthentication):
    """Session login for the web pages' AJAX calls, without CSRF tokens.

    DRF's SessionAuthentication requires a CSRF token, but this project runs
    without Django's CSRF middleware, so the token cookie never exists and every
    logged-in POST failed with "CSRF Failed: CSRF cookie not set". Instead,
    state changing requests must carry ``X-Requested-With: XMLHttpRequest``
    (jQuery adds it to same-origin requests). A page on another origin cannot
    send that header without a CORS preflight, which this site does not answer,
    so cross-site requests are still rejected.
    """

    def enforce_csrf(self, request):
        if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
            return
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            raise exceptions.PermissionDenied(
                "Missing X-Requested-With header")
