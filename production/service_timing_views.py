from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg, Max
from datetime import datetime, timedelta
from .models import ServiceSale, Store
from POSMagicApp.models import Staff
from django.http import HttpRequest


@login_required
def start_service_timer(request, sale_id):
    """
    Start the service timer for a sale (when staff begins working on customer)
    """
    try:
        sale = get_object_or_404(ServiceSale, id=sale_id)
        
        # Check if user has permission to manage this sale
        user_store = get_user_store(request.user)
        
        if not user_store and not request.user.is_superuser:
            return JsonResponse({
                'success': False,
                'error': 'You are not associated with any store. Please contact your administrator.'
            }, status=403)
        
        if user_store and sale.store != user_store and not request.user.is_superuser:
            return JsonResponse({
                'success': False,
                'error': f'You do not have permission to manage this sale. Your store: {user_store.name}, Sale store: {sale.store.name}'
            }, status=403)
        
        if request.method == 'POST':
            if sale.start_service_timer():
                messages.success(request, f'Service timer started for {sale.customer.first_name} {sale.customer.last_name}')
                
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({
                        'success': True,
                        'message': 'Service timer started successfully',
                        'service_start_time': sale.service_start_time.isoformat() if sale.service_start_time else None,
                        'queue_waiting_time': str(sale.queue_waiting_time) if sale.queue_waiting_time else None,
                        'service_status': sale.get_service_status()
                    })
            else:
                error_msg = 'Service timer is already running for this sale.'
                messages.error(request, error_msg)
                
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({
                        'success': False,
                        'error': error_msg
                    })
        
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({'success': False, 'error': 'Invalid request method'})
        
        return redirect('service_sale_details', sale_id=sale.id)
        
    except Exception as e:
        print(f"ERROR in start_service_timer: {str(e)}")
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'success': False,
                'error': f'Server error: {str(e)}'
            }, status=500)
        return redirect('service_sale_details', sale_id=sale.id)


@login_required
def end_service_timer(request, sale_id):
    """
    End the service timer for a sale (usually called when payment is processed)
    """
    sale = get_object_or_404(ServiceSale, id=sale_id)
    
    # Check if user has permission to manage this sale
    user_store = get_user_store(request.user)
    if not user_store or sale.store != user_store:
        if not request.user.is_superuser:
            return JsonResponse({
                'success': False,
                'error': 'You do not have permission to manage this sale.'
            }, status=403)
    
    if request.method == 'POST':
        if sale.end_service_timer():
            messages.success(request, f'Service completed for {sale.customer.first_name} {sale.customer.last_name}')
            
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({
                    'success': True,
                    'message': 'Service timer ended successfully',
                    'service_end_time': sale.service_end_time.isoformat() if sale.service_end_time else None,
                    'service_duration': str(sale.service_duration) if sale.service_duration else None,
                    'service_status': sale.get_service_status()
                })
        else:
            error_msg = 'Service timer is already stopped for this sale.'
            messages.error(request, error_msg)
            
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                })
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    return redirect('service_sale_details', sale_id=sale.id)


@login_required
def branch_queue_management_dashboard(request):
    """
    Store-specific queue management dashboard for branch managers
    """
    user_store = get_user_store(request.user)
    
    if not user_store:
        messages.error(request, 'You are not associated with any store. Please contact your administrator.')
        return redirect('productionPage')
    
    # Get filter parameters
    date_filter = request.GET.get('date', timezone.now().date().isoformat())
    status_filter = request.GET.get('status', 'all')
    
    # Base queryset - only for this store
    sales = ServiceSale.objects.filter(store=user_store)
    
    # Filter by date
    if date_filter:
        filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
        sales = sales.filter(sale_date__date=filter_date)
    
    # Apply status filter
    if status_filter == 'in_queue':
        sales = sales.filter(queue_start_time__isnull=False, service_start_time__isnull=True)
    elif status_filter == 'in_progress':
        sales = sales.filter(service_start_time__isnull=False, service_end_time__isnull=True)
    elif status_filter == 'completed':
        sales = sales.filter(service_end_time__isnull=False)
    elif status_filter == 'created':
        sales = sales.filter(queue_start_time__isnull=True)
    
    # Order by slot number (latest first), then by queue start time, then by sale date
    sales = sales.select_related('customer', 'store').order_by('-slot_number', 'queue_start_time', 'sale_date')
    
    # Calculate queue metrics for this store only
    today = timezone.now().date()
    today_sales = ServiceSale.objects.filter(
        store=user_store,
        sale_date__date=today
    )
    
    queue_metrics = {
        'total_customers_today': today_sales.count(),
        'in_queue': today_sales.filter(queue_start_time__isnull=False, service_start_time__isnull=True).count(),
        'in_progress': today_sales.filter(service_start_time__isnull=False, service_end_time__isnull=True).count(),
        'completed_today': today_sales.filter(service_end_time__isnull=False).count(),
        'avg_waiting_time': today_sales.filter(queue_waiting_time__isnull=False).aggregate(
            avg=Avg('queue_waiting_time')
        )['avg'],
        'avg_service_time': today_sales.filter(service_duration__isnull=False).aggregate(
            avg=Avg('service_duration')
        )['avg'],
    }
    
    context = {
        'sales': sales,
        'queue_metrics': queue_metrics,
        'user_store': user_store,
        'date_filter': date_filter,
        'status_filter': status_filter,
        'is_branch_view': True,
    }
    
    return render(request, 'branch_queue_management.html', context)


@login_required
def global_queue_management_dashboard(request):
    """
    Global queue management dashboard for admin users
    """
    if not request.user.is_superuser and not request.user.groups.filter(name__in=['Admin', 'Finance']).exists():
        # Redirect non-admin users to their branch view
        return branch_queue_management_dashboard(request)
    
    # Get filter parameters
    date_filter = request.GET.get('date', timezone.now().date().isoformat())
    status_filter = request.GET.get('status', 'all')
    store_filter = request.GET.get('store', '')
    
    # Base queryset for all stores
    sales = ServiceSale.objects.all()
    
    # Apply store filter
    if store_filter:
        sales = sales.filter(store_id=store_filter)
    
    # Filter by date
    if date_filter:
        filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
        sales = sales.filter(sale_date__date=filter_date)
    
    # Apply status filter
    if status_filter == 'in_queue':
        sales = sales.filter(queue_start_time__isnull=False, service_start_time__isnull=True)
    elif status_filter == 'in_progress':
        sales = sales.filter(service_start_time__isnull=False, service_end_time__isnull=True)
    elif status_filter == 'completed':
        sales = sales.filter(service_end_time__isnull=False)
    elif status_filter == 'created':
        sales = sales.filter(queue_start_time__isnull=True)
    
    # Order by slot number (latest first), then by queue start time, then by sale date
    sales = sales.select_related('customer', 'store').order_by('-slot_number', 'queue_start_time', 'sale_date')
    
    # Calculate global queue metrics
    today = timezone.now().date()
    today_sales = ServiceSale.objects.filter(sale_date__date=today)
    
    if store_filter:
        today_sales = today_sales.filter(store_id=store_filter)
    
    queue_metrics = {
        'total_customers_today': today_sales.count(),
        'in_queue': today_sales.filter(queue_start_time__isnull=False, service_start_time__isnull=True).count(),
        'in_progress': today_sales.filter(service_start_time__isnull=False, service_end_time__isnull=True).count(),
        'completed_today': today_sales.filter(service_end_time__isnull=False).count(),
        'avg_waiting_time': today_sales.filter(queue_waiting_time__isnull=False).aggregate(
            avg=Avg('queue_waiting_time')
        )['avg'],
        'avg_service_time': today_sales.filter(service_duration__isnull=False).aggregate(
            avg=Avg('service_duration')
        )['avg'],
    }
    
    # Store breakdown
    store_breakdown = today_sales.values('store__name').annotate(
        count=Count('id'),
        in_queue=Count('id', filter=Q(queue_start_time__isnull=False, service_start_time__isnull=True)),
        in_progress=Count('id', filter=Q(service_start_time__isnull=False, service_end_time__isnull=True)),
        completed=Count('id', filter=Q(service_end_time__isnull=False))
    ).order_by('-count')
    
    # Get all stores for filter dropdown
    all_stores = Store.objects.all().order_by('name')
    
    context = {
        'sales': sales,
        'queue_metrics': queue_metrics,
        'store_breakdown': store_breakdown,
        'all_stores': all_stores,
        'date_filter': date_filter,
        'status_filter': status_filter,
        'store_filter': store_filter,
        'is_global_view': True,
    }
    
    return render(request, 'global_queue_management.html', context)


@login_required
def service_timing_analytics(request):
    """
    Service timing analytics view - General analytics for Finance/Admin across all stores
    """
    # Check if user has permission (admin, finance, or superuser)
    if not (request.user.is_superuser or 
            request.user.groups.filter(name__in=['Admin', 'Finance']).exists()):
        messages.error(request, 'You do not have permission to access service timing analytics.')
        return redirect('productionPage')
    
    # Date range parameters
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)  # Default: last 30 days
    
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    
    # Base queryset - All sales across all stores for analytics
    sales = ServiceSale.objects.all()
    
    # Store filter (optional - for detailed analysis)
    store_filter = request.GET.get('store', '')
    if store_filter:
        sales = sales.filter(store_id=store_filter)
    
    # Filter by date range
    sales_in_period = sales.filter(
        sale_date__date__range=[start_date, end_date]
    ).select_related('customer', 'store')
    
    # Calculate timing analytics
    completed_sales = sales_in_period.filter(service_end_time__isnull=False)
    
    analytics = {
        'total_sales': sales_in_period.count(),
        'completed_sales': completed_sales.count(),
        'completion_rate': (completed_sales.count() / sales_in_period.count() * 100) if sales_in_period.count() > 0 else 0,
        
        # Waiting time analytics
        'avg_waiting_time': sales_in_period.filter(queue_waiting_time__isnull=False).aggregate(
            avg=Avg('queue_waiting_time')
        )['avg'],
        'max_waiting_time': sales_in_period.filter(queue_waiting_time__isnull=False).aggregate(
            max=Max('queue_waiting_time')
        )['max'],
        
        # Service time analytics
        'avg_service_time': completed_sales.aggregate(avg=Avg('service_duration'))['avg'],
        'max_service_time': completed_sales.aggregate(max=Max('service_duration'))['max'],
        
        # Daily breakdown
        'daily_completed': completed_sales.extra(
            select={'day': 'DATE(sale_date)'}
        ).values('day').annotate(
            count=Count('id'),
            avg_wait=Avg('queue_waiting_time'),
            avg_service=Avg('service_duration')
        ).order_by('day'),
    }
    
    # Service type breakdown (if needed)
    service_breakdown = completed_sales.values(
        'service_sale_items__service__service__name'
    ).annotate(
        count=Count('id'),
        avg_duration=Avg('service_duration')
    ).order_by('-count')[:10]  # Top 10 services
    
    context = {
        'analytics': analytics,
        'service_breakdown': service_breakdown,
        'start_date': start_date,
        'end_date': end_date,
        'all_stores': Store.objects.all(),  # Always show all stores for analytics filtering
        'store_filter': store_filter,
        'is_analytics_view': True,  # Flag to indicate this is a general analytics view
    }
    
    return render(request, 'service_timing_analytics.html', context)


def get_user_store(user_or_request):
    """
    Get the store associated with the current user or request.
    Can accept either a User instance or a request object.
    """
    from .models import Store
    
    # If a request object is passed, get the user from it
    if isinstance(user_or_request, HttpRequest):
        user = user_or_request.user
    else:
        user = user_or_request
    
    # First check if user is a store manager
    managed_store = Store.objects.filter(manager=user).first()
    if managed_store:
        return managed_store
    
    # Then check if user is staff at a store
    staff_store = Store.objects.filter(staff=user).first()
    if staff_store:
        return staff_store
    
    # Then check user's profile for default store
    if hasattr(user, 'profile') and hasattr(user.profile, 'default_store'):
        return user.profile.default_store
    
    # If no specific store is found, return the first store
    return Store.objects.first()


@login_required
def get_sale_timing_status(request, sale_id):
    """
    AJAX endpoint to get current timing status of a sale
    """
    sale = get_object_or_404(ServiceSale, id=sale_id)
    
    # Check permissions
    user_store = get_user_store(request.user)
    if not user_store or sale.store != user_store:
        if not request.user.is_superuser:
            return JsonResponse({'error': 'Permission denied'}, status=403)
    
    return JsonResponse({
        'sale_id': sale.id,
        'service_status': sale.get_service_status(),
        'queue_start_time': sale.queue_start_time.isoformat() if sale.queue_start_time else None,
        'service_start_time': sale.service_start_time.isoformat() if sale.service_start_time else None,
        'service_end_time': sale.service_end_time.isoformat() if sale.service_end_time else None,
        'current_waiting_time': str(sale.get_current_waiting_time()) if sale.get_current_waiting_time() else None,
        'current_service_time': str(sale.get_current_service_time()) if sale.get_current_service_time() else None,
        'queue_waiting_time': str(sale.queue_waiting_time) if sale.queue_waiting_time else None,
        'service_duration': str(sale.service_duration) if sale.service_duration else None,
    })
