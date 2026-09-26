import os
import shutil
import subprocess
import unittest

from django.conf import settings
from django.test import SimpleTestCase


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class UpdateStatusJsTests(SimpleTestCase):
    def test_update_status_summary(self):
        script = os.path.join(settings.BASE_DIR, "app", "tests", "js",
                              "update_status.test.js")
        result = subprocess.run(["node", script], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
