from django.apps import AppConfig

class PersonasConfig(AppConfig):
    name = 'personas'

    def ready(self):
        import personas.signals