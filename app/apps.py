from django.apps import AppConfig


class AppConfig(AppConfig):
    name = 'app'

    def ready(self):
        from rest.display_token import ensure_display_token
        ensure_display_token()
        # The customer's web translations and languages, if any
        from app import web_translations
        web_translations.refresh(force=True)
