import os
import re

import polib
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase

LOCALE_DIRS = {"de": "de", "zh-hans": "zh_Hans", "ar": "ar"}
PLACEHOLDER = re.compile(r"\{\w+\}|%\(\w+\)s")


def catalog(locale_dir):
    path = os.path.join(settings.BASE_DIR, "locale", locale_dir, "LC_MESSAGES", "django.po")
    return polib.pofile(path)


class CatalogTests(TestCase):
    def test_every_source_string_is_translated_in_each_new_language(self):
        source = {e.msgid for e in catalog("es") if e.msgid}
        source |= {e.msgid for e in catalog("en") if e.msgid}
        for code, locale_dir in LOCALE_DIRS.items():
            po = catalog(locale_dir)
            translated = {e.msgid: e.msgstr for e in po if e.msgstr}
            missing = sorted(source - set(translated))
            self.assertEqual([], missing[:5], f"{code}: {len(missing)} untranslated")

    def test_placeholders_match_the_source_string(self):
        for locale_dir in LOCALE_DIRS.values():
            for entry in catalog(locale_dir):
                if not entry.msgid or not entry.msgstr:
                    continue
                self.assertEqual(
                    sorted(PLACEHOLDER.findall(entry.msgid)),
                    sorted(PLACEHOLDER.findall(entry.msgstr)),
                    f"{locale_dir}: {entry.msgid!r}",
                )

    def test_compiled_files_exist_for_every_language(self):
        for locale_dir in LOCALE_DIRS.values():
            self.assertTrue(os.path.isfile(os.path.join(
                settings.BASE_DIR, "locale", locale_dir, "LC_MESSAGES", "django.mo")))


class PageLanguageTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("lang", password="x"))

    def test_german_page_is_german(self):
        html = self.client.get("/de/dashboard/").content.decode()
        self.assertIn('lang="de"', html)
        self.assertIn('dir="ltr"', html)
        self.assertIn("Eingänge", html)            # sidebar: Inputs

    def test_chinese_page_loads_cjk_font(self):
        html = self.client.get("/zh-hans/dashboard/").content.decode()
        self.assertIn('lang="zh-hans"', html)
        self.assertIn("Noto+Sans+SC", html)
        self.assertIn("输入", html)                # sidebar: Inputs

    def test_arabic_page_is_right_to_left(self):
        html = self.client.get("/ar/dashboard/").content.decode()
        self.assertIn('lang="ar"', html)
        self.assertIn('dir="rtl"', html)
        self.assertIn("bootstrap.rtl.min.css", html)
        self.assertIn("Noto+Sans+Arabic", html)

    def test_switcher_shows_each_language_in_its_own_name(self):
        html = self.client.get("/en/dashboard/").content.decode()
        for name in ("Español", "English", "Deutsch", "中文", "العربية"):
            self.assertIn(name, html)

    def test_spanish_and_english_still_default_to_ltr(self):
        for prefix, lang in (("/es", "es"), ("/en", "en")):
            html = self.client.get(f"{prefix}/dashboard/").content.decode()
            self.assertIn(f'lang="{lang}"', html)
            self.assertIn('dir="ltr"', html)
            self.assertIn("bootstrap.min.css", html)

    def test_login_page_follows_the_language_cookie(self):
        self.client.logout()
        self.client.cookies["django_language"] = "de"
        html = self.client.get("/login/").content.decode()
        self.assertIn('lang="de"', html)
        self.assertIn("Anmelden", html)

    def test_language_choice_on_login_page_is_stored(self):
        self.client.logout()
        r = self.client.post("/i18n/setlang/", {"language": "ar", "next": "/login/"})
        self.assertEqual(302, r.status_code)
        self.assertEqual("ar", r.cookies["django_language"].value)
        html = self.client.get("/login/").content.decode()
        self.assertIn('dir="rtl"', html)
