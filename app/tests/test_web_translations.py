import csv
import io
import os
import tempfile

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from app import web_translations
from app.web_translations import TranslationFileError

XHR = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


def rows(text):
    return list(csv.reader(io.StringIO(text.lstrip("﻿"))))


class WebTranslationsTest(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.file = os.path.join(self.directory.name, "web_translations.csv")
        self.locale = os.path.join(self.directory.name, "locale")
        self.settings_override = override_settings(
            WEB_TRANSLATIONS_FILE=self.file, WEB_TRANSLATIONS_LOCALE=self.locale,
            LOCALE_PATHS=(self.locale, os.path.join(settings.BASE_DIR, "locale")),
            LANGUAGES=settings.BUILTIN_LANGUAGES, RTL_LANGUAGES=settings.RTL_LANGUAGES)
        self.settings_override.enable()
        web_translations.refresh(force=True)
        self.client.force_login(User.objects.create_user("tr", password="x"))

    def tearDown(self):
        self.settings_override.disable()
        web_translations.refresh(force=True)
        self.directory.cleanup()

    def upload(self, text):
        return self.client.post("/web-translations/", text.encode("utf-8"),
                                content_type="text/csv", **XHR)

    def edited_export(self, edit):
        table = rows(self.client.get("/web-translations/").content.decode("utf-8"))
        head = table[0]
        edit(head, table[1:])
        out = io.StringIO()
        csv.writer(out, delimiter=";", lineterminator="\r\n").writerows(table)    # Excel
        return "﻿" + out.getvalue()

    def test_download(self):
        r = self.client.get("/web-translations/")
        self.assertEqual('attachment; filename="web-translations.csv"', r["Content-Disposition"])
        table = rows(r.content.decode("utf-8"))
        self.assertEqual(["ID", "Page", "Original text (key)", "Español (es)", "English (en)",
                          "Deutsch (de)", "中文 (简体) (zh-hans)", "العربية (ar)",
                          "Must keep unchanged"], table[0])
        panel = next(row for row in table if row[2] == "Panel")
        self.assertEqual("Dashboard", panel[4])
        self.assertEqual("Übersicht", panel[5])

    def test_reimporting_the_download_changes_nothing(self):
        r = self.upload(self.client.get("/web-translations/").content.decode("utf-8"))
        self.assertEqual(200, r.status_code)
        self.assertEqual(0, r.json()["report"]["changed"])
        self.assertEqual([], r.json()["report"]["rejected"])
        self.assertFalse(os.path.exists(self.file))

    def test_changed_text_new_language_and_rejected_text(self):
        def edit(head, body):
            head.insert(-1, "Français (fr)")
            key = head.index("Original text (key)")
            de = head.index("Deutsch (de)")
            for row in body:
                row.insert(-1, {"Panel": "Tableau de bord"}.get(row[key], ""))
                if row[key] == "Panel":
                    row[de] = "Startseite"
                if row[key] == "Update blocked: %(reason)s":
                    row[de] = "Update blockiert"        # placeholder missing
        r = self.upload(self.edited_export(edit))
        self.assertEqual(200, r.status_code, r.content)
        report = r.json()["report"]
        self.assertEqual(["fr"], report["new_languages"])
        self.assertEqual(2, report["changed"])
        self.assertEqual([("de", "placeholders")],
                         [(x["language"], x["reason"]) for x in report["rejected"]])
        self.assertIn({"code": "fr", "name": "Français"}, r.json()["languages"])

        # The pages use the texts at once, and offer the new language
        de = self.client.get("/de/dashboard/").content.decode()
        self.assertIn("Startseite", de)
        fr = self.client.get("/fr/dashboard/")
        self.assertEqual(200, fr.status_code)
        page = fr.content.decode()
        self.assertIn('lang="fr"', page)
        self.assertIn("Tableau de bord", page)
        self.assertIn(">Français<", page)
        self.assertIn("Alarms", page)            # not translated: English

        # Back to the original texts
        r = self.client.delete("/web-translations/", **XHR)
        self.assertEqual(200, r.status_code)
        self.assertFalse(r.json()["custom"])
        self.assertNotIn("Startseite", self.client.get("/de/dashboard/").content.decode())
        self.assertEqual(404, self.client.get("/fr/dashboard/").status_code)

    def test_right_to_left_language(self):
        self.upload("Original text (key),فارسی (fa)\nPanel,داشبورد\n")
        page = self.client.get("/fa/dashboard/").content.decode()
        self.assertIn('dir="rtl"', page)
        self.assertIn("داشبورد", page)

    def test_file_errors(self):
        r = self.upload("Text,Spanish\nPanel,Panel\n")
        self.assertEqual(400, r.status_code)
        self.assertEqual("no_key", r.json()["code"])
        r = self.client.post("/web-translations/", "Original text (key)\n".encode("utf-16"),
                             content_type="text/csv", **XHR)
        self.assertEqual("not_utf8", r.json()["code"])
        many = ",".join(f"L{i} (q{chr(97 + i)})" for i in range(12))
        r = self.upload("Original text (key)," + many + "\nPanel" + ",x" * 12 + "\n")
        self.assertEqual("too_many_languages", r.json()["code"])

    def test_access(self):
        self.assertEqual(403, self.client.post("/web-translations/", b"x", content_type="text/csv").status_code)
        self.assertEqual(403, self.client.delete("/web-translations/").status_code)
        self.client.logout()
        self.assertEqual(401, self.client.get("/web-translations/").status_code)
        self.assertEqual(401, self.client.get("/web-translations/info").status_code)

    def test_text_rules(self):
        problem = web_translations.text_problem
        self.assertIsNone(problem("Bloqueado: %(reason)s", "Blocked: %(reason)s"))
        self.assertEqual("placeholders", problem("Bloqueado: %(reason)s", "Blocked")[0])
        self.assertEqual("placeholders", problem("Bloqueado: %(reason)s", "100% %(reason)s")[0])
        self.assertIsNone(problem("{accepted} aceptados", "{accepted} accepted"))
        self.assertEqual("placeholders", problem("{accepted} aceptados", "accepted")[0])
        self.assertIsNone(problem("Carga", "Load 100%"))
        self.assertEqual("control_chars", problem("A", "A\tB")[0])
        with self.assertRaises(TranslationFileError):
            web_translations.parse_table(b"")
