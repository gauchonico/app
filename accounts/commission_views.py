from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from datetime import datetime
from decimal import Decimal
from .models import ChartOfAccounts, JournalEntry, JournalEntryLine, CommissionExpense
from .services import AccountingService
from production.models import StaffCommission, StaffProductCommission
from POSMagicApp.models import Staff

@login_required
def commission_expense_report(request):
    """Commission expense report tied to financial statements"""
    # Date range filter (default to current month)
    end_date = datetime.now().date()
    start_date = end_date.replace(day=1)  # First day of current month
    
    # Allow date filtering via GET parameters
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    
    # Get commission accounts
    service_commission_account = ChartOfAccounts.objects.filter(account_code='6015').first()
    product_commission_account = ChartOfAccounts.objects.filter(account_code='6016').first()
    commission_payable_account = ChartOfAccounts.objects.filter(account_code='2110').first()
    
    # Get commission expenses from journal entries
    commission_expenses = JournalEntryLine.objects.filter(
        account__account_code__in=['6015', '6016'],  # Commission expense accounts
        journal_entry__date__range=[start_date, end_date],
        entry_type='debit'
    ).select_related('account', 'journal_entry').order_by('-journal_entry__date')
    
    # Calculate totals
    total_service_commission = JournalEntryLine.objects.filter(
        account=service_commission_account,
        journal_entry__date__range=[start_date, end_date],
        entry_type='debit'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    total_product_commission = JournalEntryLine.objects.filter(
        account=product_commission_account,
        journal_entry__date__range=[start_date, end_date],
        entry_type='debit'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    total_commission_expense = total_service_commission + total_product_commission
    
    # Calculate outstanding commission payable balance
    commission_payable_credits = JournalEntryLine.objects.filter(
        account=commission_payable_account,
        entry_type='credit'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    commission_payable_debits = JournalEntryLine.objects.filter(
        account=commission_payable_account,
        entry_type='debit'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    outstanding_commission_payable = commission_payable_credits - commission_payable_debits
    
    # Get staff commission summary
    staff_commission_summary = []
    staff_members = Staff.objects.all()
    
    for staff in staff_members:
        service_commissions = StaffCommission.objects.filter(
            staff=staff,
            created_at__date__range=[start_date, end_date]
        ).aggregate(
            total=Sum('commission_amount'),
            count=Count('id'),
            paid_total=Sum('commission_amount', filter=Q(paid=True)),
            unpaid_total=Sum('commission_amount', filter=Q(paid=False))
        )
        
        product_commissions = StaffProductCommission.objects.filter(
            staff=staff,
            created_at__date__range=[start_date, end_date]
        ).aggregate(
            total=Sum('commission_amount'),
            count=Count('id'),
            paid_total=Sum('commission_amount', filter=Q(paid=True)),
            unpaid_total=Sum('commission_amount', filter=Q(paid=False))
        )
        
        total_commission = (service_commissions['total'] or 0) + (product_commissions['total'] or 0)
        total_paid = (service_commissions['paid_total'] or 0) + (product_commissions['paid_total'] or 0)
        total_unpaid = (service_commissions['unpaid_total'] or 0) + (product_commissions['unpaid_total'] or 0)
        
        if total_commission > 0:
            staff_commission_summary.append({
                'staff': staff,
                'service_commission': service_commissions['total'] or 0,
                'product_commission': product_commissions['total'] or 0,
                'total_commission': total_commission,
                'total_paid': total_paid,
                'total_unpaid': total_unpaid,
                'service_count': service_commissions['count'] or 0,
                'product_count': product_commissions['count'] or 0,
            })
    
    # Sort by total commission descending
    staff_commission_summary.sort(key=lambda x: x['total_commission'], reverse=True)
    
    context = {
        'commission_expenses': commission_expenses,
        'staff_commission_summary': staff_commission_summary,
        'total_service_commission': total_service_commission,
        'total_product_commission': total_product_commission,
        'total_commission_expense': total_commission_expense,
        'outstanding_commission_payable': outstanding_commission_payable,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'accounts/commission_expense_report.html', context)

@login_required
def sync_commission_accounting(request):
    """Sync existing commissions with accounting system"""
    if request.method == 'POST':
        try:
            # Get all service commissions without accounting records
            service_commissions = StaffCommission.objects.filter(
                accounting_records__isnull=True
            )
            
            # Get all product commissions without accounting records
            product_commissions = StaffProductCommission.objects.filter(
                accounting_records__isnull=True
            )
            
            created_count = 0
            
            # Create journal entries for service commissions
            for commission in service_commissions:
                journal_entry = AccountingService.create_service_commission_journal_entry(
                    commission, request.user
                )
                if journal_entry:
                    created_count += 1
            
            # Create journal entries for product commissions
            for commission in product_commissions:
                journal_entry = AccountingService.create_product_commission_journal_entry(
                    commission, request.user
                )
                if journal_entry:
                    created_count += 1
            
            messages.success(
                request, 
                f'Successfully synchronized {created_count} commission records with accounting system.'
            )
            
        except Exception as e:
            messages.error(request, f'Error synchronizing commissions: {e}')
    
    return redirect('commission_expense_report')
