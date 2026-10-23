"""Configuration and local Django smoke tests; no external services required."""

import importlib.util
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings


class ConfigurationTests(SimpleTestCase):
    def load_settings(self, variables, dotenv=False):
        spec = importlib.util.spec_from_file_location(
            "isolated_settings", Path(__file__).with_name("settings.py")
        )
        module = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, variables, clear=True):
            if dotenv:
                spec.loader.exec_module(module)
            else:
                with patch("dotenv.load_dotenv"):
                    spec.loader.exec_module(module)
        return module

    def test_missing_or_blank_key_fails(self):
        for key in (None, "", "   "):
            with self.subTest(key=key):
                variables = {"DEBUG": "true"}
                if key is not None:
                    variables["SECRET_KEY"] = key
                with self.assertRaisesMessage(ImproperlyConfigured, "SECRET_KEY"):
                    self.load_settings(variables)

    def test_debug_defaults_to_false_and_requires_hosts(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "ALLOWED_HOSTS"):
            self.load_settings({"SECRET_KEY": "test-only-placeholder"})
        settings = self.load_settings(
            {"SECRET_KEY": "test-only-placeholder", "ALLOWED_HOSTS": "example.test"}
        )
        self.assertFalse(settings.DEBUG)

    def test_debug_boolean_values(self):
        for value in ("true", "1", "YES", " on ", "false", "0", "NO", " off "):
            with self.subTest(value=value):
                settings = self.load_settings(
                    {
                        "SECRET_KEY": "test-only-placeholder",
                        "DEBUG": value,
                        "ALLOWED_HOSTS": "example.test",
                    }
                )
                self.assertEqual(
                    settings.DEBUG, value.strip().lower() in {"true", "1", "yes", "on"}
                )
        with self.assertRaisesMessage(ImproperlyConfigured, "DEBUG"):
            self.load_settings({"DEBUG": "invalid"})

    def test_local_defaults_use_sqlite_and_loopback(self):
        settings = self.load_settings(
            {"SECRET_KEY": "test-only-placeholder", "DEBUG": "true"}
        )
        self.assertEqual(settings.ALLOWED_HOSTS, ["localhost", "127.0.0.1", "[::1]"])
        self.assertEqual(
            settings.DATABASES["default"]["ENGINE"], "django.db.backends.sqlite3"
        )
        self.assertEqual(
            settings.DATABASES["default"]["NAME"], settings.BASE_DIR / "db.sqlite3"
        )

    def test_hosts_are_trimmed_and_empty_entries_removed(self):
        settings = self.load_settings(
            {
                "SECRET_KEY": "test-only-placeholder",
                "ALLOWED_HOSTS": " one.test, ,two.test, ",
            }
        )
        self.assertEqual(settings.ALLOWED_HOSTS, ["one.test", "two.test"])

    def test_dotenv_loads_without_overriding_process_environment(self):
        # Load an isolated copy to avoid reading or modifying a developer's .env.
        source = Path(__file__).with_name("settings.py").read_text()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            settings_file = root / "config" / "settings.py"
            settings_file.write_text(source)
            (root / ".env").write_text(
                "SECRET_KEY=dotenv-test-placeholder\nDEBUG=true\nALLOWED_HOSTS=dotenv.test\n"
            )
            spec = importlib.util.spec_from_file_location(
                "dotenv_settings", settings_file
            )
            module = importlib.util.module_from_spec(spec)
            with patch.dict(
                os.environ, {"SECRET_KEY": "process-test-placeholder"}, clear=True
            ):
                spec.loader.exec_module(module)
                self.assertEqual(module.SECRET_KEY, "process-test-placeholder")
                self.assertTrue(module.DEBUG)
                self.assertEqual(module.ALLOWED_HOSTS, ["dotenv.test"])


@override_settings(ALLOWED_HOSTS=["testserver"])
class DjangoSmokeTests(TestCase):
    def test_admin_redirects_to_login_form(self):
        response = self.client.get("/admin/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain, [("/admin/login/?next=/admin/", 302)])
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_orm_and_authenticated_session(self):
        user = get_user_model().objects.create_user(
            username="local-test-user", password="test-only-password"
        )
        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())
        self.assertTrue(
            self.client.login(username="local-test-user", password="test-only-password")
        )
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

    def test_untrusted_host_is_rejected(self):
        self.assertEqual(
            self.client.get("/admin/", HTTP_HOST="untrusted.test").status_code, 400
        )
