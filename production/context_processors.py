# production/context_processors.py
from .models import CashDrawerSession

def cash_drawer_context(request):
    context = {
        'has_active_cash_drawer_session': False,
        'active_cash_drawer_session': None
    }
    
    if hasattr(request, 'user') and request.user.is_authenticated:
        if hasattr(request, 'current_store') and request.current_store:
            session = CashDrawerSession.objects.filter(
                user=request.user,
                store=request.current_store,
                status='open'
            ).first()
            
            if session:
                context.update({
                    'has_active_cash_drawer_session': True,
                    'active_cash_drawer_session': session
                })
    
    return context