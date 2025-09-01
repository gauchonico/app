from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Q, Count, Avg
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import ServiceSaleInvoice, ServiceSale, Store
from POSMagicApp.models import Staff


def is_admin_or_finance(user):
    """Check if user is admin or finance personnel"""
    return user.is_superuser or user.groups.filter(name__in=['Admin', 'Finance']).exists()


def get_user_store(user):
    """Get the store associated with the current user"""
    # First check if user is a store manager
    managed_store = Store.objects.filter(manager=user).first()
    if managed_store:
        return managed_store
    
    # Then check if user is staff at a store
    try:
        staff = Staff.objects.get(user=user)
        return staff.store
    except Staff.DoesNotExist:
        pass
    
    # Check if user has a related staff profile
    try:
        staff = Staff.objects.filter(
            first_name__icontains=user.first_name,
            last_name__icontains=user.last_name
        ).first()
        if staff and staff.store:
            return staff.store
    except:
        pass
    
    return None


@login_required
def global_service_invoice_list(request):
    """
    Global view showing all service invoices from all stores
    For admin and finance users only
    """
    if not is_admin_or_finance(request.user):
        # Redirect non-admin users to their store-specific view
        return store_specific_service_invoice_list(request)
    
    # Get filter parameters
    store_filter = request.GET.get('store', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    customer_search = request.GET.get('customer', '')
    
    # Base queryset for all service invoices
    invoices = ServiceSaleInvoice.objects.select_related(
        'sale__store', 'sale__customer'
    ).order_by('-created_at')
    
    # Apply filters
    if store_filter:
        invoices = invoices.filter(sale__store_id=store_filter)
    
    if status_filter:
        invoices = invoices.filter(paid_status=status_filter)
    
    if date_from:
        invoices = invoices.filter(created_at__date__gte=date_from)
    
    if date_to:
        invoices = invoices.filter(created_at__date__lte=date_to)
    
    if customer_search:
        invoices = invoices.filter(
            Q(sale__customer__first_name__icontains=customer_search) |
            Q(sale__customer__last_name__icontains=customer_search) |
            Q(sale__customer__phone__icontains=customer_search)
        )
    
    # Calculate metrics
    total_invoices = invoices.count()
    total_value = invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    paid_invoices = invoices.filter(paid_status='paid').count()
    unpaid_invoices = invoices.filter(paid_status='unpaid').count()
    partially_paid_invoices = invoices.filter(paid_status='partially_paid').count()
    
    # Store breakdown
    store_breakdown = invoices.values('sale__store__name').annotate(
        count=Count('id'),
        revenue=Sum('total_amount'),
        avg_invoice=Avg('total_amount')
    ).order_by('-revenue')
    
    # Recent activity (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    recent_invoices = invoices.filter(created_at__gte=week_ago).count()
    
    # Pagination
    paginator = Paginator(invoices, 25)  # Show 25 invoices per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all stores for filter dropdown
    all_stores = Store.objects.all().order_by('name')
    
    context = {
        'invoices': page_obj,
        'all_stores': all_stores,
        'total_invoices': total_invoices,
        'total_value': total_value,
        'paid_invoices': paid_invoices,
        'unpaid_invoices': unpaid_invoices,
        'partially_paid_invoices': partially_paid_invoices,
        'store_breakdown': store_breakdown,
        'recent_invoices': recent_invoices,
        'is_global_view': True,
        # Filter values for maintaining state
        'store_filter': store_filter,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'customer_search': customer_search,
    }
    
    return render(request, 'service_invoice_list.html', context)


@login_required
def store_specific_service_invoice_list(request):
    """
    Store-specific view showing only invoices for the user's assigned store
    """
    user_store = get_user_store(request.user)
    
    if not user_store:
        # User is not associated with any store
        context = {
            'error_message': 'You are not associated with any store. Please contact your administrator.',
            'is_global_view': False,
        }
        return render(request, 'service_invoice_list.html', context)
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    customer_search = request.GET.get('customer', '')
    
    # Base queryset filtered by user's store
    invoices = ServiceSaleInvoice.objects.filter(
        sale__store=user_store
    ).select_related('sale__customer').order_by('-created_at')
    
    # Apply additional filters
    if status_filter:
        invoices = invoices.filter(paid_status=status_filter)
    
    if date_from:
        invoices = invoices.filter(created_at__date__gte=date_from)
    
    if date_to:
        invoices = invoices.filter(created_at__date__lte=date_to)
    
    if customer_search:
        invoices = invoices.filter(
            Q(sale__customer__first_name__icontains=customer_search) |
            Q(sale__customer__last_name__icontains=customer_search) |
            Q(sale__customer__phone__icontains=customer_search)
        )
    
    # Calculate metrics for this store
    total_invoices = invoices.count()
    total_value = invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    paid_invoices = invoices.filter(paid_status='paid').count()
    unpaid_invoices = invoices.filter(paid_status='unpaid').count()
    partially_paid_invoices = invoices.filter(paid_status='partially_paid').count()
    
    # Recent activity (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    recent_invoices = invoices.filter(created_at__gte=week_ago).count()
    
    # Pagination
    paginator = Paginator(invoices, 25)  # Show 25 invoices per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'invoices': page_obj,
        'user_store': user_store,
        'total_invoices': total_invoices,
        'total_value': total_value,
        'paid_invoices': paid_invoices,
        'unpaid_invoices': unpaid_invoices,
        'partially_paid_invoices': partially_paid_invoices,
        'recent_invoices': recent_invoices,
        'is_global_view': False,
        # Filter values for maintaining state
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'customer_search': customer_search,
    }
    
    return render(request, 'service_invoice_list.html', context)


@login_required
def service_invoice_detail(request, invoice_id):
    """
    Detailed view of a specific service invoice
    Users can only view invoices from their store (unless admin/finance)
    """
    invoice = get_object_or_404(ServiceSaleInvoice, id=invoice_id)
    
    # Check permissions
    if not is_admin_or_finance(request.user):
        user_store = get_user_store(request.user)
        if not user_store or invoice.sale.store != user_store:
            context = {
                'error_message': 'You do not have permission to view this invoice.',
            }
            return render(request, 'service_invoice_detail.html', context)
    
    # Get related data
    sale = invoice.sale
    service_items = sale.service_sale_items.all()
    product_items = sale.product_sale_items.all()
    accessory_items = sale.accessory_sale_items.all()
    payments = sale.payments.all().order_by('-payment_date')
    
    # Calculate totals
    service_total = sum(item.total_price for item in service_items)
    product_total = sum(item.total_price for item in product_items)
    accessory_total = sum(item.total_price for item in accessory_items)
    
    # Calculate payment summary
    total_paid = sum(payment.amount for payment in payments)
    balance_due = sale.balance
    
    context = {
        'invoice': invoice,
        'sale': sale,
        'service_items': service_items,
        'product_items': product_items,
        'accessory_items': accessory_items,
        'payments': payments,
        'service_total': service_total,
        'product_total': product_total,
        'accessory_total': accessory_total,
        'total_paid': total_paid,
        'balance_due': balance_due,
    }
    
    return render(request, 'service_invoice_detail.html', context)


@login_required
def service_invoice_analytics(request):
    """
    Analytics for service invoices
    Global view for admin/finance, store-specific for others
    """
    # Check if user is admin/finance
    if is_admin_or_finance(request.user):
        # Global analytics
        store_filter = request.GET.get('store', '')
        if store_filter:
            invoices = ServiceSaleInvoice.objects.filter(sale__store_id=store_filter)
            view_title = f"Analytics for {Store.objects.get(id=store_filter).name}"
        else:
            invoices = ServiceSaleInvoice.objects.all()
            view_title = "Global Service Invoice Analytics"
    else:
        # Store-specific analytics
        user_store = get_user_store(request.user)
        if not user_store:
            context = {'error_message': 'You are not associated with any store.'}
            return render(request, 'service_invoice_analytics.html', context)
        
        invoices = ServiceSaleInvoice.objects.filter(sale__store=user_store)
        view_title = f"Analytics for {user_store.name}"
    
    # Date range for analysis (default: last 30 days)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Override with custom date range if provided
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    
    # Filter by date range
    invoices_in_period = invoices.filter(
        created_at__date__range=[start_date, end_date]
    ).select_related('sale__store', 'sale__customer')
    
    # Calculate metrics
    total_invoices = invoices_in_period.count()
    total_value = invoices_in_period.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    collection_rate = 0
    
    if total_value > 0:
        collected_amount = invoices_in_period.filter(paid_status='paid').aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        collection_rate = (collected_amount / total_value * 100)
    
    # Payment method breakdown
    payment_methods = invoices_in_period.values('payment_method').annotate(
        count=Count('id'),
        revenue=Sum('total_amount')
    ).order_by('-revenue')
    
    # Daily trend
    from django.db.models.functions import TruncDate
    daily_invoices = invoices_in_period.annotate(
        day=TruncDate('created_at')
    ).values('day').annotate(
        daily_count=Count('id'),
        daily_value=Sum('total_amount')
    ).order_by('day')
    
    context = {
        'view_title': view_title,
        'start_date': start_date,
        'end_date': end_date,
        'total_invoices': total_invoices,
        'total_value': total_value,
        'collection_rate': collection_rate,
        'payment_methods': payment_methods,
        'daily_invoices': daily_invoices,
        'is_admin': is_admin_or_finance(request.user),
    }
    
    if is_admin_or_finance(request.user):
        context['all_stores'] = Store.objects.all().order_by('name')
        context['store_filter'] = request.GET.get('store', '')
    
    return render(request, 'service_invoice_analytics.html', context)
