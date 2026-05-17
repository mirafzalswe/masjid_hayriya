from django.apps import AppConfig


class MurojaatlarConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'murojaatlar'

    def ready(self):
        import murojaatlar.signals
