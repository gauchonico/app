from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count, Q, Avg
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import StoreSale, Store, StoreInventory
from accounts.decorators import allowed_users


def is_admin_or_finance(user):
    """Check if user is admin or finance"""
    return user.is_superuser or user.groups.filter(name__in=['Admin', 'Finance', 'Management']).exists()


@login_required
@user_passes_test(is_admin_or_finance)
def unified_store_sales_view(request):
    """
    Unified view for admin/finance to see all store sales across all stores
    """
    # Get filter parameters
    store_filter = request.GET.get('store', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    payment_status = request.GET.get('payment_status', '')
    search_query = request.GET.get('search', '')
    
    # Base queryset for all store sales
    sales = StoreSale.objects.select_related(
        'store', 'customer'
    ).prefetch_related(
        'store_sale_items__product'
    ).order_by('-sale_date')
    
    # Apply filters
    if store_filter:
        sales = sales.filter(store_id=store_filter)
    
    if status_filter:
        sales = sales.filter(status=status_filter)
    
    if payment_status:
        sales = sales.filter(payment_status=payment_status)
    
    if date_from:
        sales = sales.filter(sale_date__date__gte=date_from)
    
    if date_to:
        sales = sales.filter(sale_date__date__lte=date_to)
    
    if search_query:
        sales = sales.filter(
            Q(order_number__icontains=search_query) |
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query) |
            Q(customer__phone__icontains=search_query)
        )
    
    # Calculate metrics
    total_sales = sales.count()
    
    # Overall metrics
    metrics = {
        'total_sales': total_sales,
        'total_amount': sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0'),
        'invoiced_count': sales.filter(status='invoiced').count(),
        'confirmed_count': sales.filter(status='confirmed').count(),
        'pending_count': sales.filter(status='pending').count(),
        'paid_count': sales.filter(payment_status='paid').count(),
        'unpaid_count': sales.filter(payment_status='unpaid').count(),
        'partially_paid_count': sales.filter(payment_status='partially_paid').count(),
        'average_sale': sales.aggregate(avg=Avg('total_amount'))['avg'] or Decimal('0'),
    }
    
    # Store-wise breakdown
    store_breakdown = Store.objects.annotate(
        sales_count=Count('store_sales', filter=Q(store_sales__in=sales)),
        total_revenue=Sum('store_sales__total_amount', filter=Q(store_sales__in=sales)),
        invoiced_sales=Count('store_sales', filter=Q(store_sales__in=sales, store_sales__status='invoiced')),
        paid_sales=Count('store_sales', filter=Q(store_sales__in=sales, store_sales__payment_status='paid'))
    ).filter(sales_count__gt=0).order_by('-total_revenue')
    
    # Daily sales trend (last 30 days)
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    daily_sales = sales.filter(
        sale_date__date__gte=thirty_days_ago
    ).extra(
        select={'day': 'DATE(sale_date)'}
    ).values('day').annotate(
        daily_count=Count('id'),
        daily_revenue=Sum('total_amount')
    ).order_by('day')
    
    # Recent high-value sales
    high_value_sales = sales.filter(
        total_amount__gte=500000  # Sales over 500k
    ).order_by('-total_amount')[:10]
    
    # Pagination
    paginator = Paginator(sales, 25)  # Show 25 sales per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all stores for filter dropdown
    all_stores = Store.objects.all().order_by('name')
    
    context = {
        'sales': page_obj,
        'metrics': metrics,
        'store_breakdown': store_breakdown,
        'daily_sales': daily_sales,
        'high_value_sales': high_value_sales,
        'all_stores': all_stores,
        # Filter values for form persistence
        'store_filter': store_filter,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'payment_status': payment_status,
        'search_query': search_query,
        # Choices for dropdowns
        'status_choices': StoreSale.STATUS_CHOICES,
        'payment_status_choices': StoreSale.PAYMENT_STATUS_CHOICES,
    }
    
    return render(request, 'admin_unified_store_sales.html', context)


@login_required
@user_passes_test(is_admin_or_finance)
def store_sales_analytics_api(request):
    """
    API endpoint for charts and analytics data
    """
    chart_type = request.GET.get('type', 'daily')
    store_id = request.GET.get('store_id', '')
    
    sales_query = StoreSale.objects.all()
    if store_id:
        sales_query = sales_query.filter(store_id=store_id)
    
    if chart_type == 'daily':
        # Last 30 days daily sales
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        data = sales_query.filter(
            sale_date__date__gte=thirty_days_ago
        ).extra(
            select={'day': 'DATE(sale_date)'}
        ).values('day').annotate(
            count=Count('id'),
            revenue=Sum('total_amount')
        ).order_by('day')
        
        return JsonResponse({
            'labels': [item['day'] for item in data],
            'sales_count': [item['count'] for item in data],
            'revenue': [float(item['revenue'] or 0) for item in data]
        })
    
    elif chart_type == 'status':
        # Sales by status
        data = sales_query.values('status').annotate(
            count=Count('id'),
            revenue=Sum('total_amount')
        ).order_by('status')
        
        return JsonResponse({
            'labels': [item['status'].title() for item in data],
            'counts': [item['count'] for item in data],
            'revenues': [float(item['revenue'] or 0) for item in data]
        })
    
    elif chart_type == 'stores':
        # Sales by store
        data = Store.objects.annotate(
            sales_count=Count('store_sales'),
            total_revenue=Sum('store_sales__total_amount')
        ).filter(sales_count__gt=0).order_by('-total_revenue')
        
        return JsonResponse({
            'labels': [store.name for store in data],
            'sales_count': [store.sales_count for store in data],
            'revenue': [float(store.total_revenue or 0) for store in data]
        })
    
    return JsonResponse({'error': 'Invalid chart type'})


@login_required
@user_passes_test(is_admin_or_finance)
def store_performance_report(request):
    """
    Detailed store performance comparison report
    """
    # Get date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if not date_from:
        date_from = (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = timezone.now().date().strftime('%Y-%m-%d')
    
    # Store performance metrics
    stores_performance = Store.objects.annotate(
        total_sales=Count('store_sales', filter=Q(
            store_sales__sale_date__date__range=[date_from, date_to]
        )),
        total_revenue=Sum('store_sales__total_amount', filter=Q(
            store_sales__sale_date__date__range=[date_from, date_to]
        )),
        avg_sale_value=Avg('store_sales__total_amount', filter=Q(
            store_sales__sale_date__date__range=[date_from, date_to]
        )),
        paid_sales=Count('store_sales', filter=Q(
            store_sales__sale_date__date__range=[date_from, date_to],
            store_sales__payment_status='paid'
        )),
        invoiced_sales=Count('store_sales', filter=Q(
            store_sales__sale_date__date__range=[date_from, date_to],
            store_sales__status='invoiced'
        )),
    ).order_by('-total_revenue')
    
    # Calculate performance metrics
    for store in stores_performance:
        store.total_revenue = store.total_revenue or Decimal('0')
        store.avg_sale_value = store.avg_sale_value or Decimal('0')
        store.payment_rate = (store.paid_sales / store.total_sales * 100) if store.total_sales > 0 else 0
        store.invoice_rate = (store.invoiced_sales / store.total_sales * 100) if store.total_sales > 0 else 0
    
    # Overall totals
    overall_metrics = {
        'total_stores': stores_performance.count(),
        'total_sales': sum(store.total_sales for store in stores_performance),
        'total_revenue': sum(store.total_revenue for store in stores_performance),
        'avg_revenue_per_store': sum(store.total_revenue for store in stores_performance) / stores_performance.count() if stores_performance.count() > 0 else 0,
    }
    
    context = {
        'stores_performance': stores_performance,
        'overall_metrics': overall_metrics,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'store_performance_report.html', context)
