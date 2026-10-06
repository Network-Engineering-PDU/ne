import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.urls import resolve, reverse, Resolver404
from django.utils.translation import get_language, activate

register = template.Library()


@register.simple_tag(takes_context=True)
def change_lang(context, lang=None, *args, **kwargs):
    """
    Get active page's url by a specified language
    Usage: {% change_lang 'en' %}
    """
    path = context['request'].path
    full_path = context['request'].get_full_path()
    try:
        url_parts = resolve(path)
        cur_language = get_language()
        try:
            activate(lang)
            url = reverse(url_parts.view_name, kwargs=url_parts.kwargs)
            activate(cur_language)
            parameters = "?{0}".format(full_path.split('?')[1]) if len(full_path.split('?')) == 2 else ""
            return "{0}{1}".format(url, parameters)
        except Exception:
            pass
    except Resolver404:
        pass
    return full_path


def callmethod(obj, methodname):
    method = getattr(obj, methodname)
    if obj.__dict__.get("__callArg"):
        ret = method(*obj.__callArg)
        del obj.__callArg
        return ret
    return method()


def args(obj, arg):
    if not obj.__dict__.get("__callArg", ""):
        obj.__callArg = []
    obj.__callArg.append(arg)
    return obj


register.filter("call", callmethod)
register.filter("args", args)


@register.simple_tag
def static_v(path):
    """Like {% static %} but versioned by the file's modification time.

    Browsers keep scripts and stylesheets cached when only their content
    changes, so an updated page could run an old script. The version changes
    whenever the file does, which forces a fresh download.
    """
    url = static(path)
    found = finders.find(path)
    if isinstance(found, (list, tuple)):
        found = found[0] if found else None
    try:
        return f"{url}?v={int(os.path.getmtime(found))}" if found else url
    except OSError:
        return url


# Names are shown in their own language so a user can find theirs.
NATIVE_LANGUAGE_NAMES = {
    'es': 'Español',
    'en': 'English',
    'de': 'Deutsch',
    'zh-hans': '中文',
    'ar': 'العربية',
}


@register.simple_tag
def native_name(code):
    return NATIVE_LANGUAGE_NAMES.get(code, code)


@register.simple_tag
def text_direction(code):
    """'rtl' for right-to-left languages, otherwise 'ltr'."""
    from django.conf import settings
    return 'rtl' if code in getattr(settings, 'RTL_LANGUAGES', ()) else 'ltr'
