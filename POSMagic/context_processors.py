from django.conf import settings

def global_settings(request):
    return {
        'CURRENCY_SYMBOL': getattr(settings, 'CURRENCY_SYMBOL', '$'),
    }