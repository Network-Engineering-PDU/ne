"""Web interface translation file (Settings page): download, upload with a
report of the texts accepted and rejected, and reset. See web_translations.

Like the PDU proxy, state changing requests must carry the
``X-Requested-With: XMLHttpRequest`` header: the project runs without
Django's CSRF middleware, and a page on another origin can't add it.
"""
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from app import web_translations


def _unauthorized():
    return JsonResponse({"result": "error", "message": "Unauthorized"}, status=401)


def _file_error(ex):
    return JsonResponse({"detail": str(ex), "code": ex.code, "param": ex.detail}, status=400)


@csrf_exempt
def web_translations_file(request):
    if not request.user.is_authenticated:
        return _unauthorized()
    if request.method in ("GET", "HEAD"):
        response = HttpResponse(web_translations.export_csv().encode("utf-8"),
                                content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="web-translations.csv"'
        return response
    if request.method not in ("POST", "DELETE"):
        return JsonResponse({"result": "error", "message": "Not allowed"}, status=405)
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return JsonResponse({"result": "error", "message": "Forbidden"}, status=403)
    if request.method == "DELETE":
        web_translations.save(None)
        return JsonResponse(web_translations.info())
    try:
        text, report = web_translations.import_csv(request.body)
    except web_translations.TranslationFileError as ex:
        return _file_error(ex)
    web_translations.save(text)
    return JsonResponse({"report": report, **web_translations.info()})


def web_translations_info(request):
    if not request.user.is_authenticated:
        return _unauthorized()
    return JsonResponse(web_translations.info())
