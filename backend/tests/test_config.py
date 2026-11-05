import unittest

from pydantic import ValidationError

from app.config import Settings

SAFE = {
    "app_env": "production",
    "api_token": "t" * 40,
    "sandbox_backend": "docker",
    "frontend_origins": ["https://skillforge.example.com"],
    "postgres_password": "a-long-random-db-password",
}


def build(**changes):
    return Settings(_env_file=None, **{**SAFE, **changes})


class ProductionSettingsTests(unittest.TestCase):
    def test_safe_production_settings_load(self):
        self.assertEqual(build().app_env, "production")

    def test_each_unsafe_setting_is_refused(self):
        cases = {
            "API_TOKEN": {"api_token": None},
            "SANDBOX_BACKEND": {"sandbox_backend": "process"},
            "https://": {"frontend_origins": ["http://skillforge.example.com"]},
            "'*'": {"frontend_origins": ["*"]},
            "POSTGRES_PASSWORD": {"postgres_password": "change-me"},
        }
        for fragment, change in cases.items():
            with self.subTest(fragment), self.assertRaises(ValidationError) as caught:
                build(**change)
            self.assertIn(fragment, str(caught.exception))

    def test_development_keeps_local_defaults(self):
        settings = Settings(_env_file=None, app_env="development", postgres_password="dev")
        self.assertEqual(settings.sandbox_backend, "process")
        self.assertIsNone(settings.api_token)


if __name__ == "__main__":
    unittest.main()
