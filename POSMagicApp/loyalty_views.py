"""
Views for the customer loyalty system
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.db import transaction
from .models import LoyaltySettings, Customer, CustomerLoyaltyTransaction
from .loyalty_forms import (
    LoyaltySettingsForm, PointsRedemptionForm, 
    ManualPointsAdjustmentForm, LoyaltyReportFilterForm
)


def is_admin_or_finance(user):
    """Check if user is admin or finance"""
    return user.is_superuser or user.groups.filter(name__in=['Admin', 'Finance']).exists()


@login_required
@user_passes_test(is_admin_or_finance)
def loyalty_settings_view(request):
    """Admin page for configuring loyalty system settings"""
    
    # Get or create loyalty settings
    loyalty_settings = LoyaltySettings.get_current_settings()
    
    if request.method == 'POST':
        form = LoyaltySettingsForm(request.POST, instance=loyalty_settings)
        if form.is_valid():
            settings = form.save()
            messages.success(request, 'Loyalty settings updated successfully!')
            return redirect('DjangoHUDApp:loyalty_settings')
    else:
        form = LoyaltySettingsForm(instance=loyalty_settings)
    
    # Calculate some stats for the dashboard
    total_customers = Customer.objects.count()
    customers_with_points = Customer.objects.filter(loyalty_points__gt=0).count()
    total_points_in_circulation = Customer.objects.aggregate(
        total=Sum('loyalty_points')
    )['total'] or 0
    total_points_earned = Customer.objects.aggregate(
        total=Sum('total_points_earned')
    )['total'] or 0
    total_points_redeemed = Customer.objects.aggregate(
        total=Sum('total_points_redeemed')
    )['total'] or 0
    
    # Tier distribution
    tier_stats = Customer.objects.values('loyalty_tier').annotate(
        count=Count('id')
    ).order_by('loyalty_tier')
    
    context = {
        'form': form,
        'loyalty_settings': loyalty_settings,
        'stats': {
            'total_customers': total_customers,
            'customers_with_points': customers_with_points,
            'total_points_in_circulation': total_points_in_circulation,
            'total_points_earned': total_points_earned,
            'total_points_redeemed': total_points_redeemed,
            'tier_stats': tier_stats,
        }
    }
    
    return render(request, "pages/loyalty-settings.html", context)


@login_required
@user_passes_test(is_admin_or_finance)
def loyalty_reports_view(request):
    """Admin page for loyalty system reports and analytics"""
    
    # Get filter form
    filter_form = LoyaltyReportFilterForm(request.GET or None)
    
    # Base queryset for transactions
    transactions = CustomerLoyaltyTransaction.objects.select_related('customer')
    
    # Apply filters
    if filter_form.is_valid():
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        customer = filter_form.cleaned_data.get('customer')
        transaction_type = filter_form.cleaned_data.get('transaction_type')
        loyalty_tier = filter_form.cleaned_data.get('loyalty_tier')
        
        if date_from:
            transactions = transactions.filter(created_at__date__gte=date_from)
        if date_to:
            transactions = transactions.filter(created_at__date__lte=date_to)
        if customer:
            transactions = transactions.filter(customer=customer)
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
        if loyalty_tier:
            transactions = transactions.filter(customer__loyalty_tier=loyalty_tier)
    
    # Pagination
    paginator = Paginator(transactions.order_by('-created_at'), 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate summary stats for filtered data
    filtered_stats = {
        'total_transactions': transactions.count(),
        'points_earned': transactions.filter(transaction_type='EARNED').aggregate(
            total=Sum('points')
        )['total'] or 0,
        'points_redeemed': transactions.filter(transaction_type='REDEEMED').aggregate(
            total=Sum('points')
        )['total'] or 0,
        'points_expired': transactions.filter(transaction_type='EXPIRED').aggregate(
            total=Sum('points')
        )['total'] or 0,
        'bonus_points': transactions.filter(transaction_type='BONUS').aggregate(
            total=Sum('points')
        )['total'] or 0,
    }
    
    # Monthly trends (last 12 months)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=365)
    
    monthly_data = []
    current_date = start_date.replace(day=1)
    
    while current_date <= end_date:
        next_month = current_date.replace(day=28) + timedelta(days=4)
        next_month = next_month.replace(day=1)
        
        month_transactions = CustomerLoyaltyTransaction.objects.filter(
            created_at__date__gte=current_date,
            created_at__date__lt=next_month
        )
        
        monthly_data.append({
            'month': current_date.strftime('%b %Y'),
            'earned': month_transactions.filter(transaction_type='EARNED').aggregate(
                total=Sum('points')
            )['total'] or 0,
            'redeemed': abs(month_transactions.filter(transaction_type='REDEEMED').aggregate(
                total=Sum('points')
            )['total'] or 0),
            'customers': month_transactions.values('customer').distinct().count(),
        })
        
        current_date = next_month
    
    # Top customers by points
    top_customers = Customer.objects.filter(
        loyalty_points__gt=0
    ).order_by('-loyalty_points')[:10]
    
    # Recent activity
    recent_transactions = CustomerLoyaltyTransaction.objects.select_related(
        'customer'
    ).order_by('-created_at')[:20]
    
    context = {
        'filter_form': filter_form,
        'page_obj': page_obj,
        'filtered_stats': filtered_stats,
        'monthly_data': monthly_data,
        'top_customers': top_customers,
        'recent_transactions': recent_transactions,
    }
    
    return render(request, 'pages/loyalty-reports.html', context)


@login_required
def points_redemption_view(request):
    """Page for redeeming customer loyalty points"""
    
    if request.method == 'POST':
        form = PointsRedemptionForm(request.POST, user=request.user)
        if form.is_valid():
            customer = form.cleaned_data['customer']
            points_to_redeem = form.cleaned_data['points_to_redeem']
            notes = form.cleaned_data['notes']
            
            # Calculate redemption value
            redemption_value = form.get_redemption_value()
            
            # Process redemption
            with transaction.atomic():
                success = customer.redeem_loyalty_points(
                    points=points_to_redeem,
                    description=f"Points redeemed for {redemption_value:.2f} UGX. {notes}".strip(),
                    created_by=request.user
                )
                
                if success:
                    messages.success(
                        request, 
                        f"Successfully redeemed {points_to_redeem} points for {customer.name}. "
                        f"Value: {redemption_value:.2f} UGX"
                    )
                    return redirect('DjangoHUDApp:points_redemption')
                else:
                    messages.error(request, "Failed to redeem points. Please try again.")
    else:
        form = PointsRedemptionForm(user=request.user)
    
    # Get loyalty settings for display
    loyalty_settings = LoyaltySettings.get_current_settings()
    
    # Recent redemptions
    recent_redemptions = CustomerLoyaltyTransaction.objects.filter(
        transaction_type='REDEEMED'
    ).select_related('customer').order_by('-created_at')[:10]
    
    context = {
        'form': form,
        'loyalty_settings': loyalty_settings,
        'recent_redemptions': recent_redemptions,
    }
    
    return render(request, 'pages/points-redemption.html', context)


@login_required
@user_passes_test(is_admin_or_finance)
def manual_points_adjustment_view(request):
    """Admin page for manually adjusting customer loyalty points"""
    
    if request.method == 'POST':
        form = ManualPointsAdjustmentForm(request.POST)
        if form.is_valid():
            customer = form.cleaned_data['customer']
            points_adjustment = form.cleaned_data['points_adjustment']
            reason = form.cleaned_data['reason']
            
            # Process adjustment
            with transaction.atomic():
                if points_adjustment > 0:
                    # Adding points
                    success = customer.add_loyalty_points(
                        points=points_adjustment,
                        transaction_type='ADJUSTED',
                        description=f"Manual adjustment: {reason}",
                        created_by=request.user
                    )
                else:
                    # Subtracting points (manual redemption/adjustment)
                    customer.loyalty_points += points_adjustment  # points_adjustment is negative
                    customer.save(update_fields=['loyalty_points'])
                    
                    CustomerLoyaltyTransaction.objects.create(
                        customer=customer,
                        transaction_type='ADJUSTED',
                        points=points_adjustment,
                        description=f"Manual adjustment: {reason}",
                        created_by=request.user
                    )
                    success = True
                
                if success:
                    messages.success(
                        request,
                        f"Successfully adjusted {customer.name}'s points by {points_adjustment:+d}. "
                        f"New balance: {customer.loyalty_points} points"
                    )
                    return redirect('DjangoHUDApp:manual_points_adjustment')
                else:
                    messages.error(request, "Failed to adjust points. Please try again.")
    else:
        form = ManualPointsAdjustmentForm()
    
    # Recent adjustments
    recent_adjustments = CustomerLoyaltyTransaction.objects.filter(
        transaction_type='ADJUSTED'
    ).select_related('customer', 'created_by').order_by('-created_at')[:10]
    
    context = {
        'form': form,
        'recent_adjustments': recent_adjustments,
    }
    
    return render(request, 'pages/manual-points-adjustment.html', context)


@login_required
def customer_loyalty_details(request, customer_id):
    """Detailed view of a customer's loyalty information"""
    
    customer = get_object_or_404(Customer, id=customer_id)
    
    # Get loyalty transactions
    transactions = customer.loyalty_transactions.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate monthly activity (last 6 months)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=180)
    
    monthly_activity = []
    current_date = start_date.replace(day=1)
    
    while current_date <= end_date:
        next_month = current_date.replace(day=28) + timedelta(days=4)
        next_month = next_month.replace(day=1)
        
        month_transactions = customer.loyalty_transactions.filter(
            created_at__date__gte=current_date,
            created_at__date__lt=next_month
        )
        
        monthly_activity.append({
            'month': current_date.strftime('%b %Y'),
            'earned': month_transactions.filter(transaction_type='EARNED').aggregate(
                total=Sum('points')
            )['total'] or 0,
            'redeemed': abs(month_transactions.filter(transaction_type='REDEEMED').aggregate(
                total=Sum('points')
            )['total'] or 0),
        })
        
        current_date = next_month
    
    # Get loyalty summary
    loyalty_summary = customer.get_loyalty_summary()
    
    context = {
        'customer': customer,
        'page_obj': page_obj,
        'monthly_activity': monthly_activity,
        'loyalty_summary': loyalty_summary,
    }
    
    return render(request, 'customer_loyalty_details.html', context)


@login_required
def get_customer_points_ajax(request):
    """AJAX endpoint to get customer's current points"""
    customer_id = request.GET.get('customer_id')
    
    if customer_id:
        try:
            customer = Customer.objects.get(id=customer_id)
            loyalty_settings = LoyaltySettings.get_current_settings()
            
            return JsonResponse({
                'success': True,
                'points': customer.loyalty_points,
                'tier': customer.get_loyalty_tier_display(),
                'minimum_redemption': loyalty_settings.minimum_points_redemption if loyalty_settings else 0,
                'points_to_currency_ratio': float(loyalty_settings.points_to_currency_ratio) if loyalty_settings else 100,
            })
        except Customer.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Customer not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})
