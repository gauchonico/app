from django.apps import AppConfig


class POSMagicappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'POSMagicApp'
    
    def ready(self):
        import POSMagicApp.signals