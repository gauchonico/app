from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('POSMagicApp.urls')),
    path('cart/', include('cart.urls')),
    path('payment/', include('payment.urls')),
    path('production/', include('production.urls')),
    path('admin/', admin.site.urls),
]+ static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = 'POSMagicApp.views.handler404'