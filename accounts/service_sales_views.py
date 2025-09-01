from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Q, Count, Avg
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from production.models import ServiceSale, Store, ServiceSaleInvoice, Payment
from POSMagicApp.models import Customer


def is_admin_or_finance(user):
    """Check if user is admin or finance personnel"""
    return user.is_superuser or user.groups.filter(name__in=['Admin', 'Finance']).exists()


@login_required
@user_passes_test(is_admin_or_finance)
def unified_service_sales_dashboard(request):
    """
    Unified dashboard for all service sales across all stores
    For admin and finance users only
    """
    # Get filter parameters
    store_filter = request.GET.get('store', '')
    status_filter = request.GET.get('status', '')
    invoice_status_filter = request.GET.get('invoice_status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    customer_search = request.GET.get('customer', '')
    
    # Base queryset for all service sales
    service_sales = ServiceSale.objects.select_related(
        'store', 'customer'
    ).prefetch_related('payments').order_by('-sale_date')
    
    # Apply filters
    if store_filter:
        service_sales = service_sales.filter(store_id=store_filter)
    
    if status_filter:
        service_sales = service_sales.filter(paid_status=status_filter)
    
    if invoice_status_filter:
        service_sales = service_sales.filter(invoice_status=invoice_status_filter)
    
    if date_from:
        service_sales = service_sales.filter(sale_date__date__gte=date_from)
    
    if date_to:
        service_sales = service_sales.filter(sale_date__date__lte=date_to)
    
    if customer_search:
        service_sales = service_sales.filter(
            Q(customer__first_name__icontains=customer_search) |
            Q(customer__last_name__icontains=customer_search) |
            Q(customer__phone__icontains=customer_search)
        )
    
    # Calculate metrics
    total_sales = service_sales.count()
    total_revenue = service_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    total_paid = service_sales.filter(paid_status='paid').aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    total_outstanding = service_sales.filter(paid_status='not_paid').aggregate(total=Sum('balance'))['total'] or Decimal('0')
    
    # Status breakdown
    status_breakdown = {
        'not_invoiced': service_sales.filter(invoice_status='not_invoiced').count(),
        'invoiced': service_sales.filter(invoice_status='invoiced').count(),
        'cancelled': service_sales.filter(invoice_status='cancelled').count(),
        'paid': service_sales.filter(paid_status='paid').count(),
        'not_paid': service_sales.filter(paid_status='not_paid').count(),
    }
    
    # Store breakdown
    store_breakdown = service_sales.values('store__name').annotate(
        count=Count('id'),
        revenue=Sum('total_amount'),
        avg_sale=Avg('total_amount')
    ).order_by('-revenue')
    
    # Recent activity (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    recent_sales = service_sales.filter(sale_date__gte=week_ago).count()
    
    # Top customers
    top_customers = service_sales.values(
        'customer__first_name', 
        'customer__last_name', 
        'customer__phone'
    ).annotate(
        total_spent=Sum('total_amount'),
        visit_count=Count('id')
    ).order_by('-total_spent')[:10]
    
    # Pagination
    paginator = Paginator(service_sales, 25)  # Show 25 sales per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all stores for filter dropdown
    all_stores = Store.objects.all().order_by('name')
    
    context = {
        'service_sales': page_obj,
        'all_stores': all_stores,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'total_paid': total_paid,
        'total_outstanding': total_outstanding,
        'status_breakdown': status_breakdown,
        'store_breakdown': store_breakdown,
        'recent_sales': recent_sales,
        'top_customers': top_customers,
        # Filter values for maintaining state
        'store_filter': store_filter,
        'status_filter': status_filter,
        'invoice_status_filter': invoice_status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'customer_search': customer_search,
    }
    
    return render(request, 'accounts/unified_service_sales_dashboard.html', context)


@login_required
@user_passes_test(is_admin_or_finance)
def service_sales_analytics(request):
    """
    Advanced analytics for service sales across all stores
    """
    # Date range for analysis (default: last 30 days)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Override with custom date range if provided
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    
    # Filter sales by date range
    sales_in_period = ServiceSale.objects.filter(
        sale_date__date__range=[start_date, end_date]
    ).select_related('store', 'customer')
    
    # Daily sales trend
    from django.db.models.functions import TruncDate
    daily_sales = sales_in_period.annotate(
        day=TruncDate('sale_date')
    ).values('day').annotate(
        daily_count=Count('id'),
        daily_revenue=Sum('total_amount')
    ).order_by('day')
    
    # Store performance comparison
    store_performance = sales_in_period.values('store__name').annotate(
        total_sales=Count('id'),
        total_revenue=Sum('total_amount'),
        avg_sale_value=Avg('total_amount'),
        paid_sales=Count('id', filter=Q(paid_status='paid')),
        conversion_rate=Count('id', filter=Q(paid_status='paid')) * 100.0 / Count('id')
    ).order_by('-total_revenue')
    
    # Payment method analysis
    payment_methods = sales_in_period.values('payment_mode').annotate(
        count=Count('id'),
        revenue=Sum('total_amount')
    ).order_by('-revenue')
    
    # Customer analysis
    customer_metrics = sales_in_period.values(
        'customer__first_name',
        'customer__last_name',
        'customer__phone'
    ).annotate(
        visits=Count('id'),
        total_spent=Sum('total_amount'),
        avg_spend=Avg('total_amount')
    ).filter(visits__gt=1).order_by('-total_spent')[:20]
    
    # Revenue vs Collection analysis
    revenue_vs_collection = {
        'total_invoiced': sales_in_period.aggregate(total=Sum('total_amount'))['total'] or Decimal('0'),
        'total_collected': sales_in_period.filter(paid_status='paid').aggregate(total=Sum('total_amount'))['total'] or Decimal('0'),
        'pending_collection': sales_in_period.filter(paid_status='not_paid').aggregate(total=Sum('balance'))['total'] or Decimal('0'),
    }
    
    revenue_vs_collection['collection_rate'] = (
        (revenue_vs_collection['total_collected'] / revenue_vs_collection['total_invoiced'] * 100)
        if revenue_vs_collection['total_invoiced'] > 0 else 0
    )
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'daily_sales': daily_sales,
        'store_performance': store_performance,
        'payment_methods': payment_methods,
        'customer_metrics': customer_metrics,
        'revenue_vs_collection': revenue_vs_collection,
        'total_sales_count': sales_in_period.count(),
    }
    
    return render(request, 'accounts/service_sales_analytics.html', context)


@login_required
@user_passes_test(is_admin_or_finance)
def service_sale_detail_admin(request, sale_id):
    """
    Detailed view of a specific service sale for admin/finance
    """
    sale = get_object_or_404(ServiceSale, id=sale_id)
    
    # Get all related items
    service_items = sale.service_sale_items.all()
    product_items = sale.product_sale_items.all()
    accessory_items = sale.accessory_sale_items.all()
    payments = sale.payments.all().order_by('-payment_date')
    
    # Calculate totals
    service_total = sum(item.total_price for item in service_items)
    product_total = sum(item.total_price for item in product_items)
    accessory_total = sum(item.total_price for item in accessory_items)
    
    context = {
        'sale': sale,
        'service_items': service_items,
        'product_items': product_items,
        'accessory_items': accessory_items,
        'payments': payments,
        'service_total': service_total,
        'product_total': product_total,
        'accessory_total': accessory_total,
    }
    
    return render(request, 'accounts/service_sale_detail_admin.html', context)


@login_required
@user_passes_test(is_admin_or_finance)
def export_service_sales_data(request):
    """
    Export service sales data to CSV for analysis
    """
    import csv
    from django.http import HttpResponse
    
    # Get filter parameters (same as dashboard)
    store_filter = request.GET.get('store', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Apply same filters as dashboard
    service_sales = ServiceSale.objects.select_related('store', 'customer')
    
    if store_filter:
        service_sales = service_sales.filter(store_id=store_filter)
    if status_filter:
        service_sales = service_sales.filter(paid_status=status_filter)
    if date_from:
        service_sales = service_sales.filter(sale_date__date__gte=date_from)
    if date_to:
        service_sales = service_sales.filter(sale_date__date__lte=date_to)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="service_sales_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Sale ID', 'Service Sale Number', 'Store', 'Customer Name', 
        'Customer Phone', 'Sale Date', 'Total Amount', 'Paid Amount', 
        'Balance', 'Payment Status', 'Invoice Status', 'Payment Mode'
    ])
    
    for sale in service_sales:
        writer.writerow([
            sale.id,
            sale.service_sale_number or f'SS-{sale.id}',
            sale.store.name,
            f"{sale.customer.first_name} {sale.customer.last_name}",
            sale.customer.phone,
            sale.sale_date.strftime('%Y-%m-%d %H:%M'),
            sale.total_amount,
            sale.paid_amount,
            sale.balance,
            sale.get_paid_status_display(),
            sale.get_invoice_status_display(),
            sale.get_payment_mode_display(),
        ])
    
    return response
