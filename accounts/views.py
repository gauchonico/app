from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from .models import (
    ChartOfAccounts, Department, Budget, JournalEntry, JournalEntryLine,
    FinancialPeriod, TrialBalance, ProfitLossStatement, BalanceSheet
)
from .forms import (
    ChartOfAccountsForm, DepartmentForm, BudgetForm, JournalEntryForm,
    JournalEntryLineForm, FinancialPeriodForm, TrialBalanceForm,
    ProfitLossStatementForm, BalanceSheetForm, DateRangeForm, BudgetReportForm,
    ChartOfAccountsImportForm, BulkJournalEntryForm
)

@login_required
def accounting_dashboard(request):
    """Beautiful accounting dashboard with financial overview"""
    # Calculate financial metrics
    total_revenue = JournalEntryLine.objects.filter(
        account__account_type='revenue',
        entry_type='credit'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    total_expenses = JournalEntryLine.objects.filter(
        account__account_type='expense',
        entry_type='debit'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    net_profit = total_revenue - total_expenses
    
    # Calculate cash balance
    cash_balance = JournalEntryLine.objects.filter(
        account__account_code='1000',  # Cash account
        entry_type='debit'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    cash_outflows = JournalEntryLine.objects.filter(
        account__account_code='1000',  # Cash account
        entry_type='credit'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    cash_balance = cash_balance - cash_outflows
    
    # Get recent journal entries
    recent_entries = JournalEntry.objects.select_related('department').order_by('-created_at')[:10]
    
    context = {
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'cash_balance': cash_balance,
        'recent_entries': recent_entries,
    }
    
    return render(request, 'accounts/dashboard.html', context)

@login_required
def chart_of_accounts_list(request):
    """List chart of accounts with beautiful design"""
    accounts = ChartOfAccounts.objects.all().order_by('account_code')
    
    # Group by account type
    account_groups = {}
    for account in accounts:
        if account.account_type not in account_groups:
            account_groups[account.account_type] = []
        account_groups[account.account_type].append(account)
    
    context = {
        'account_groups': account_groups,
        'accounts': accounts,
    }
    return render(request, 'accounts/chart_of_accounts_list.html', context)

@login_required
def chart_of_accounts_create(request):
    """Create new chart of accounts"""
    if request.method == 'POST':
        form = ChartOfAccountsForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Chart of accounts created successfully!')
            return redirect('accounts:chart_of_accounts_list')
    else:
        form = ChartOfAccountsForm()
    
    context = {'form': form}
    return render(request, 'accounts/chart_of_accounts_form.html', context)

@login_required
def chart_of_accounts_update(request, pk):
    """Update chart of accounts"""
    account = get_object_or_404(ChartOfAccounts, pk=pk)
    if request.method == 'POST':
        form = ChartOfAccountsForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, 'Chart of accounts updated successfully!')
            return redirect('accounts:chart_of_accounts_list')
    else:
        form = ChartOfAccountsForm(instance=account)
    
    context = {'form': form, 'object': account}
    return render(request, 'accounts/chart_of_accounts_form.html', context)

@login_required
def chart_of_accounts_delete(request, pk):
    """Delete chart of accounts"""
    account = get_object_or_404(ChartOfAccounts, pk=pk)
    if request.method == 'POST':
        account.delete()
        messages.success(request, 'Chart of accounts deleted successfully!')
        return redirect('accounts:chart_of_accounts_list')
    
    context = {'object': account}
    return render(request, 'accounts/chart_of_accounts_confirm_delete.html', context)

@login_required
def department_list(request):
    """Beautiful department list page"""
    departments = Department.objects.all().order_by('name')
    
    context = {
        'departments': departments,
    }
    return render(request, 'accounts/department_list.html', context)

@login_required
def department_create(request):
    """Create new department"""
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department created successfully!')
            return redirect('accounts:department_list')
    else:
        form = DepartmentForm()
    
    context = {'form': form}
    return render(request, 'accounts/department_form.html', context)

@login_required
def department_update(request, pk):
    """Update department"""
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department updated successfully!')
            return redirect('accounts:department_list')
    else:
        form = DepartmentForm(instance=department)
    
    context = {'form': form, 'object': department}
    return render(request, 'accounts/department_form.html', context)

@login_required
def department_delete(request, pk):
    """Delete department"""
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        department.delete()
        messages.success(request, 'Department deleted successfully!')
        return redirect('accounts:department_list')
    
    context = {'object': department}
    return render(request, 'accounts/department_confirm_delete.html', context)

@login_required
def budget_list(request):
    """List budgets with beautiful design"""
    budgets = Budget.objects.select_related('department', 'account').all().order_by('-start_date')
    
    # Calculate budget utilization
    for budget in budgets:
        budget.utilization = budget.utilization_percentage
    
    context = {
        'budgets': budgets,
    }
    return render(request, 'accounts/budget_list.html', context)

@login_required
def budget_create(request):
    """Create new budget"""
    if request.method == 'POST':
        form = BudgetForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Budget created successfully!')
            return redirect('accounts:budget_list')
    else:
        form = BudgetForm()
    
    context = {'form': form}
    return render(request, 'accounts/budget_form.html', context)

@login_required
def budget_update(request, pk):
    """Update budget"""
    budget = get_object_or_404(Budget, pk=pk)
    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=budget)
        if form.is_valid():
            form.save()
            messages.success(request, 'Budget updated successfully!')
            return redirect('accounts:budget_list')
    else:
        form = BudgetForm(instance=budget)
    
    context = {'form': form, 'object': budget}
    return render(request, 'accounts/budget_form.html', context)

@login_required
def budget_delete(request, pk):
    """Delete budget"""
    budget = get_object_or_404(Budget, pk=pk)
    if request.method == 'POST':
        budget.delete()
        messages.success(request, 'Budget deleted successfully!')
        return redirect('accounts:budget_list')
    
    context = {'object': budget}
    return render(request, 'accounts/budget_confirm_delete.html', context)

@login_required
def journal_entry_list(request):
    """List journal entries with beautiful design"""
    entries = JournalEntry.objects.select_related('department', 'created_by').all().order_by('-date', '-created_at')
    
    # Pagination
    paginator = Paginator(entries, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'entries': page_obj,
    }
    return render(request, 'accounts/journal_entry_list.html', context)

@login_required
def journal_entry_create(request):
    """Create new journal entry"""
    if request.method == 'POST':
        form = JournalEntryForm(request.POST)
        if form.is_valid():
            journal_entry = form.save(commit=False)
            journal_entry.created_by = request.user
            journal_entry.save()
            messages.success(request, 'Journal entry created successfully!')
            return redirect('accounts:journal_entry_detail', pk=journal_entry.pk)
    else:
        form = JournalEntryForm()
    
    context = {'form': form}
    return render(request, 'accounts/journal_entry_form.html', context)

@login_required
def journal_entry_detail(request, pk):
    """Detail view for journal entry"""
    entry = get_object_or_404(JournalEntry, pk=pk)
    
    context = {
        'entry': entry,
    }
    return render(request, 'accounts/journal_entry_detail.html', context)

@login_required
def journal_entry_update(request, pk):
    """Update journal entry"""
    entry = get_object_or_404(JournalEntry, pk=pk)
    if request.method == 'POST':
        form = JournalEntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, 'Journal entry updated successfully!')
            return redirect('accounts:journal_entry_detail', pk=entry.pk)
    else:
        form = JournalEntryForm(instance=entry)
    
    context = {'form': form, 'object': entry}
    return render(request, 'accounts/journal_entry_form.html', context)

@login_required
def journal_entry_delete(request, pk):
    """Delete journal entry"""
    entry = get_object_or_404(JournalEntry, pk=pk)
    if request.method == 'POST':
        entry.delete()
        messages.success(request, 'Journal entry deleted successfully!')
        return redirect('accounts:journal_entry_list')
    
    context = {'object': entry}
    return render(request, 'accounts/journal_entry_confirm_delete.html', context)

@login_required
def journal_entry_post(request, pk):
    """Post a journal entry"""
    entry = get_object_or_404(JournalEntry, pk=pk)
    if request.method == 'POST':
        try:
            entry.post_entry()
            messages.success(request, 'Journal entry posted successfully!')
        except ValueError as e:
            messages.error(request, f'Cannot post entry: {e}')
        return redirect('accounts:journal_entry_detail', pk=entry.pk)
    
    return redirect('accounts:journal_entry_detail', pk=entry.pk)

@login_required
def trial_balance(request):
    """Generate trial balance report"""
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            # Generate trial balance
            accounts = ChartOfAccounts.objects.all()
            trial_balance_data = []
            
            for account in accounts:
                debits = JournalEntryLine.objects.filter(
                    account=account,
                    entry_type='debit',
                    journal_entry__date__range=[start_date, end_date]
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                
                credits = JournalEntryLine.objects.filter(
                    account=account,
                    entry_type='credit',
                    journal_entry__date__range=[start_date, end_date]
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                
                if debits > 0 or credits > 0:
                    trial_balance_data.append({
                        'account': account,
                        'debits': debits,
                        'credits': credits,
                        'balance': debits - credits
                    })
            
            context = {
                'form': form,
                'trial_balance_data': trial_balance_data,
                'start_date': start_date,
                'end_date': end_date,
            }
            return render(request, 'accounts/trial_balance.html', context)
    else:
        form = DateRangeForm()
    
    context = {'form': form}
    return render(request, 'accounts/trial_balance.html', context)

@login_required
def profit_loss_report(request):
    """Generate profit and loss report"""
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            # Calculate revenue
            revenue = JournalEntryLine.objects.filter(
                account__account_type='revenue',
                entry_type='credit',
                journal_entry__date__range=[start_date, end_date]
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            # Calculate expenses
            expenses = JournalEntryLine.objects.filter(
                account__account_type='expense',
                entry_type='debit',
                journal_entry__date__range=[start_date, end_date]
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            net_income = revenue - expenses
            
            context = {
                'form': form,
                'revenue': revenue,
                'expenses': expenses,
                'net_income': net_income,
                'start_date': start_date,
                'end_date': end_date,
            }
            return render(request, 'accounts/profit_loss_report.html', context)
    else:
        form = DateRangeForm()
    
    context = {'form': form}
    return render(request, 'accounts/profit_loss_report.html', context)

@login_required
def budget_report(request):
    """Generate budget report"""
    if request.method == 'POST':
        form = BudgetReportForm(request.POST)
        if form.is_valid():
            department = form.cleaned_data['department']
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            # Get budgets for the department
            budgets = Budget.objects.filter(
                department=department,
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            
            budget_data = []
            for budget in budgets:
                spent = JournalEntryLine.objects.filter(
                    account=budget.account,
                    entry_type='debit',
                    journal_entry__department=department,
                    journal_entry__date__range=[start_date, end_date]
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                
                budget_data.append({
                    'budget': budget,
                    'spent': spent,
                    'remaining': budget.amount - spent,
                    'utilization': (spent / budget.amount * 100) if budget.amount > 0 else 0
                })
            
            context = {
                'form': form,
                'budget_data': budget_data,
                'department': department,
                'start_date': start_date,
                'end_date': end_date,
            }
            return render(request, 'accounts/budget_report.html', context)
    else:
        form = BudgetReportForm()
    
    context = {'form': form}
    return render(request, 'accounts/budget_report.html', context)

# API endpoints for AJAX
@login_required
def get_account_balance(request, account_id):
    """Get account balance for AJAX requests"""
    account = get_object_or_404(ChartOfAccounts, id=account_id)
    balance = account.balance
    return JsonResponse({'balance': float(balance)})

@login_required
def get_department_budget(request, department_id):
    """Get department budget for AJAX requests"""
    department = get_object_or_404(Department, id=department_id)
    total_budget = department.total_budget
    total_spent = department.total_spent
    remaining = department.remaining_budget
    
    return JsonResponse({
        'total_budget': float(total_budget),
        'total_spent': float(total_spent),
        'remaining': float(remaining)
    })
