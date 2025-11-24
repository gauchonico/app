# production/middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from .utils import is_cash_drawer_session_required, get_user_store
from .models import CashDrawerSession

# production/middleware.py
class CashDrawerSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip for non-authenticated users or specific URLs
        if (not request.user.is_authenticated or 
            request.path.startswith('/admin/') or
            request.path.startswith('/static/') or
            request.path.startswith('/media/') or
            request.path.startswith('/cash-drawer/')):
            return self.get_response(request)

        # Add session check to request for use in views
        if hasattr(request.user, 'profile'):
            store = get_user_store(request)  # Pass the request object
            if store:
                request.has_active_cash_drawer_session = CashDrawerSession.objects.filter(
                    user=request.user,
                    store=store,
                    status='open'
                ).exists()
                request.current_store = store

        return self.get_response(request)