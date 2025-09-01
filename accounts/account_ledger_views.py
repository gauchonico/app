from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from decimal import Decimal
from accounts.models import ChartOfAccounts, JournalEntry, JournalEntryLine


@login_required
def account_ledger_details(request, account_id):
    """
    Show all journal entry lines for a specific chart of account (Account Ledger)
    """
    account = get_object_or_404(ChartOfAccounts, id=account_id)
    
    # Get all journal entry lines for this account
    journal_lines = JournalEntryLine.objects.filter(
        account=account
    ).select_related('journal_entry', 'journal_entry__department').order_by('-journal_entry__date', '-journal_entry__created_at')
    
    # Calculate running balance and totals
    total_debits = journal_lines.filter(entry_type='debit').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_credits = journal_lines.filter(entry_type='credit').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Calculate balance based on account type
    if account.account_type in ['asset', 'expense']:
        # Asset and Expense accounts have debit balances
        account_balance = total_debits - total_credits
        normal_balance = 'debit'
    else:
        # Liability, Equity, and Revenue accounts have credit balances
        account_balance = total_credits - total_debits
        normal_balance = 'credit'
    
    # Add running balance to each entry
    running_balance = Decimal('0')
    journal_lines_with_balance = []
    
    # Process entries in chronological order for running balance
    for line in reversed(journal_lines):
        if normal_balance == 'debit':
            if line.entry_type == 'debit':
                running_balance += line.amount
            else:
                running_balance -= line.amount
        else:
            if line.entry_type == 'credit':
                running_balance += line.amount
            else:
                running_balance -= line.amount
        
        line.running_balance = running_balance
        journal_lines_with_balance.append(line)
    
    # Reverse back to latest first
    journal_lines_with_balance.reverse()
    
    # Pagination
    paginator = Paginator(journal_lines_with_balance, 25)  # Show 25 entries per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Filter options
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    entry_type_filter = request.GET.get('entry_type')
    
    filtered_lines = journal_lines
    if date_from:
        filtered_lines = filtered_lines.filter(journal_entry__date__gte=date_from)
    if date_to:
        filtered_lines = filtered_lines.filter(journal_entry__date__lte=date_to)
    if entry_type_filter:
        filtered_lines = filtered_lines.filter(entry_type=entry_type_filter)
    
    context = {
        'account': account,
        'journal_lines': page_obj,
        'total_debits': total_debits,
        'total_credits': total_credits,
        'account_balance': account_balance,
        'normal_balance': normal_balance,
        'entries_count': journal_lines.count(),
        'date_from': date_from,
        'date_to': date_to,
        'entry_type_filter': entry_type_filter,
    }
    
    return render(request, 'accounts/account_ledger_details.html', context)


@login_required
def account_summary_report(request, account_id):
    """
    Generate a summary report for a specific account
    """
    account = get_object_or_404(ChartOfAccounts, id=account_id)
    
    # Get monthly summary
    from django.db.models import DateTrunc
    from datetime import datetime, timedelta
    
    # Get last 12 months of data
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=365)
    
    monthly_summary = JournalEntryLine.objects.filter(
        account=account,
        journal_entry__date__range=[start_date, end_date]
    ).extra(
        select={'month': "strftime('%%Y-%%m', journal_entry.date)"}
    ).values('month').annotate(
        total_debits=Sum('amount', filter=Q(entry_type='debit')),
        total_credits=Sum('amount', filter=Q(entry_type='credit'))
    ).order_by('month')
    
    # Get recent large transactions
    large_transactions = JournalEntryLine.objects.filter(
        account=account,
        amount__gte=100000  # Transactions over 100k
    ).select_related('journal_entry').order_by('-amount')[:10]
    
    context = {
        'account': account,
        'monthly_summary': monthly_summary,
        'large_transactions': large_transactions,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'accounts/account_summary_report.html', context)
