from django.apps import AppConfig


class SimControlConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'SIM_Control'

    def ready(self):
        import SIM_Control.signals
