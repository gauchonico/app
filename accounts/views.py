from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import date, timedelta, datetime
from decimal import Decimal
import json
import csv
from django.forms import ValidationError

from .models import (
    ChartOfAccounts, Department, Budget, JournalEntry, JournalEntryLine,
    FinancialPeriod, TrialBalance, ProfitLossStatement, BalanceSheet,
    ProductionExpense, SalesRevenue, StoreTransfer, ManufacturingRecord,
    PaymentRecord, StoreBudget, StoreFinancialSummary
)
from .forms import (
    ChartOfAccountsForm, DepartmentForm, BudgetForm, JournalEntryForm,
    JournalEntryLineForm, FinancialPeriodForm, TrialBalanceForm,
    ProfitLossStatementForm, BalanceSheetForm, DateRangeForm, BudgetReportForm,
    ChartOfAccountsImportForm, BulkJournalEntryForm, ManufacturingReportForm
)
from .services import AccountingService

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
    
    # Get additional statistics
    departments_count = Department.objects.filter(is_active=True).count()
    accounts_count = ChartOfAccounts.objects.filter(is_active=True).count()
    periods_count = FinancialPeriod.objects.count()
    
    # Get current month entries count
    current_month = timezone.now().month
    current_year = timezone.now().year
    monthly_entries_count = JournalEntry.objects.filter(
        created_at__month=current_month,
        created_at__year=current_year
    ).count()
    
    context = {
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'cash_balance': cash_balance,
        'recent_entries': recent_entries,
        'departments_count': departments_count,
        'accounts_count': accounts_count,
        'periods_count': periods_count,
        'monthly_entries_count': monthly_entries_count,
    }
    
    return render(request, 'dashboard.html', context)

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
    
    # Calculate summary statistics
    active_accounts = accounts.filter(is_active=True).count()
    account_types = len(set(account.account_type for account in accounts))
    parent_accounts = accounts.filter(parent_account__isnull=True).count()
    
    context = {
        'account_groups': account_groups,
        'accounts': accounts,
        'active_accounts': active_accounts,
        'account_types': account_types,
        'parent_accounts': parent_accounts,
    }
    return render(request, 'chart_of_accounts_list.html', context)

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
    return render(request, 'chart_of_accounts_form.html', context)

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
    return render(request, 'chart_of_accounts_form.html', context)

@login_required
def chart_of_accounts_delete(request, pk):
    """Delete chart of accounts"""
    account = get_object_or_404(ChartOfAccounts, pk=pk)
    if request.method == 'POST':
        account.delete()
        messages.success(request, 'Chart of accounts deleted successfully!')
        return redirect('accounts:chart_of_accounts_list')
    
    context = {'object': account}
    return render(request, 'chart_of_accounts_confirm_delete.html', context)

@login_required
def department_list(request):
    """Beautiful department list page"""
    departments = Department.objects.all().order_by('name')
    
    # Calculate summary statistics
    total_budget = sum(dept.total_budget for dept in departments)
    total_spent = sum(dept.total_spent for dept in departments)
    remaining_budget = total_budget - total_spent
    
    context = {
        'departments': departments,
        'total_budget': total_budget,
        'total_spent': total_spent,
        'remaining_budget': remaining_budget,
    }
    return render(request, 'department_list.html', context)

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
    return render(request, 'department_form.html', context)

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
    return render(request, 'department_form.html', context)

@login_required
def department_delete(request, pk):
    """Delete department"""
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        department.delete()
        messages.success(request, 'Department deleted successfully!')
        return redirect('accounts:department_list')
    
    context = {'object': department}
    return render(request, 'department_confirm_delete.html', context)

@login_required
def department_detail(request, pk):
    """Detail view for department with budget information"""
    department = get_object_or_404(Department, pk=pk)
    budgets = department.budgets.select_related('account').all().order_by('-start_date')
    
    # Calculate budget statistics
    total_budget = sum(budget.amount for budget in budgets)
    total_spent = sum(budget.spent_amount for budget in budgets)
    remaining_budget = total_budget - total_spent
    utilization_percentage = (total_spent / total_budget * 100) if total_budget > 0 else 0
    
    # Get recent journal entries for this department
    recent_entries = department.journal_entries.select_related('created_by').order_by('-date')[:10]
    
    context = {
        'department': department,
        'budgets': budgets,
        'total_budget': total_budget,
        'total_spent': total_spent,
        'remaining_budget': remaining_budget,
        'utilization_percentage': utilization_percentage,
        'recent_entries': recent_entries,
    }
    return render(request, 'department_detail.html', context)

@login_required
def budget_list(request):
    """List budgets with beautiful design"""
    budgets = Budget.objects.select_related('department', 'account').all().order_by('-start_date')
    
    # Calculate budget utilization
    for budget in budgets:
        budget.utilization = budget.utilization_percentage
    
    # Calculate summary statistics
    total_allocated = sum(budget.amount for budget in budgets)
    total_spent = sum(budget.spent_amount for budget in budgets)
    avg_utilization = sum(budget.utilization_percentage for budget in budgets) / len(budgets) if budgets else 0
    
    context = {
        'budgets': budgets,
        'total_allocated': total_allocated,
        'total_spent': total_spent,
        'avg_utilization': avg_utilization,
    }
    return render(request, 'budget_list.html', context)

@login_required
def budget_create(request):
    """Create new budget"""
    if request.method == 'POST':
        form = BudgetForm(request.POST)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.created_by = request.user
            budget.save()
            messages.success(request, 'Budget created successfully!')
            return redirect('accounts:budget_list')
    else:
        form = BudgetForm()
    
    context = {'form': form}
    return render(request, 'budget_form.html', context)

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
    return render(request, 'budget_form.html', context)

@login_required
def budget_delete(request, pk):
    """Delete budget"""
    budget = get_object_or_404(Budget, pk=pk)
    if request.method == 'POST':
        budget.delete()
        messages.success(request, 'Budget deleted successfully!')
        return redirect('accounts:budget_list')
    
    context = {'object': budget}
    return render(request, 'budget_confirm_delete.html', context)

@login_required
def journal_entry_list(request):
    """List journal entries with filtering and beautiful design"""
    # Get filter parameters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    entry_type = request.GET.get('entry_type')
    status = request.GET.get('status')
    department = request.GET.get('department')
    search = request.GET.get('search')
    
    # Start with base queryset
    entries = JournalEntry.objects.select_related('department', 'created_by').all()
    
    # Apply filters
    if date_from:
        entries = entries.filter(date__gte=date_from)
    if date_to:
        entries = entries.filter(date__lte=date_to)
    if entry_type:
        entries = entries.filter(entry_type=entry_type)
    if status == 'posted':
        entries = entries.filter(is_posted=True)
    elif status == 'draft':
        entries = entries.filter(is_posted=False)
    if department:
        entries = entries.filter(department_id=department)
    if search:
        entries = entries.filter(
            Q(description__icontains=search) |
            Q(reference__icontains=search) |
            Q(entry_number__icontains=search)
        )
    
    # Order by date and creation time
    entries = entries.order_by('-date', '-created_at')
    
    # Calculate statistics
    total_entries = JournalEntry.objects.count()
    posted_entries = JournalEntry.objects.filter(is_posted=True).count()
    draft_entries = JournalEntry.objects.filter(is_posted=False).count()
    
    # Calculate total amount from all entries
    total_amount = JournalEntryLine.objects.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    # Get departments for filter dropdown
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    # Pagination
    paginator = Paginator(entries, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'entries': page_obj,
        'total_entries': total_entries,
        'posted_entries': posted_entries,
        'draft_entries': draft_entries,
        'total_amount': total_amount,
        'departments': departments,
    }
    return render(request, 'journal_entry_list.html', context)

@login_required
def journal_entry_create(request):
    """Create new journal entry with dynamic lines"""
    if request.method == 'POST':
        # Debug: Print POST data to understand what's being sent
        print("POST data received:")
        for key, value in request.POST.items():
            print(f"  {key}: {value}")
        
        form = JournalEntryForm(request.POST)
        if form.is_valid():
            print("Form is valid, creating journal entry...")
            journal_entry = form.save(commit=False)
            journal_entry.created_by = request.user
            journal_entry.save()
            print(f"Journal entry created with ID: {journal_entry.id}")
            
            # Process the dynamic entry lines
            # The form sends data like lines[0][account], lines[0][entry_type], etc.
            lines_created = False
            index = 0
            
            while True:
                account_key = f'lines[{index}][account]'
                entry_type_key = f'lines[{index}][entry_type]'
                amount_key = f'lines[{index}][amount]'
                description_key = f'lines[{index}][description]'
                
                # Check if this line exists in the POST data
                if account_key not in request.POST:
                    print(f"Line {index} not found in POST data, stopping...")
                    break
                
                account_id = request.POST.get(account_key)
                entry_type = request.POST.get(entry_type_key)
                amount = request.POST.get(amount_key)
                description = request.POST.get(description_key, '')
                
                print(f"Processing line {index}: account={account_id}, type={entry_type}, amount={amount}")
                
                if account_id and entry_type and amount:
                    try:
                        account = ChartOfAccounts.objects.get(id=account_id)
                        line = JournalEntryLine.objects.create(
                            journal_entry=journal_entry,
                            account=account,
                            entry_type=entry_type,
                            amount=amount,
                            description=description
                        )
                        print(f"Created journal entry line: {line}")
                        lines_created = True
                    except (ChartOfAccounts.DoesNotExist, ValueError) as e:
                        # Log the error but continue processing other lines
                        print(f"Error creating journal entry line: {e}")
                        continue
                else:
                    print(f"Line {index} missing required data: account_id={account_id}, entry_type={entry_type}, amount={amount}")
                
                index += 1
            
            if lines_created:
                print("Journal entry created successfully with lines")
                messages.success(request, 'Journal entry created successfully!')
                return redirect('accounts:journal_entry_detail', pk=journal_entry.pk)
            else:
                # If no lines were created, delete the journal entry and show error
                print("No lines were created, deleting journal entry")
                journal_entry.delete()
                messages.error(request, 'No valid entry lines were provided. Please add at least one debit and one credit line.')
                return redirect('accounts:journal_entry_create')
        else:
            # Form is invalid, show errors
            print("Form is invalid:")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")
            messages.error(request, 'Please correct the errors below.')
    else:
        form = JournalEntryForm()
    
    # Get all active accounts for the dropdown
    accounts = ChartOfAccounts.objects.filter(is_active=True).order_by('account_code')
    
    context = {
        'form': form,
        'accounts': accounts,
    }
    return render(request, 'journal_entry_form.html', context)

@login_required
def journal_entry_detail(request, pk):
    """Detail view for journal entry"""
    entry = get_object_or_404(JournalEntry, pk=pk)
    
    context = {
        'entry': entry,
    }
    return render(request, 'journal_entry_detail.html', context)

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
    return render(request, 'journal_entry_form.html', context)

@login_required
def journal_entry_delete(request, pk):
    """Delete journal entry"""
    entry = get_object_or_404(JournalEntry, pk=pk)
    if request.method == 'POST':
        entry.delete()
        messages.success(request, 'Journal entry deleted successfully!')
        return redirect('accounts:journal_entry_list')
    
    context = {'object': entry}
    return render(request, 'journal_entry_confirm_delete.html', context)

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
            total_debits = Decimal('0.00')
            total_credits = Decimal('0.00')
            
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
                    balance = debits - credits
                    trial_balance_data.append({
                        'account': account,
                        'debits': debits,
                        'credits': credits,
                        'balance': balance
                    })
                    total_debits += debits
                    total_credits += credits
            
            balance_difference = total_debits - total_credits
            
            context = {
                'form': form,
                'trial_balance_data': trial_balance_data,
                'start_date': start_date,
                'end_date': end_date,
                'total_debits': total_debits,
                'total_credits': total_credits,
                'balance_difference': balance_difference,
            }
            return render(request, 'trial_balance.html', context)
    else:
        form = DateRangeForm()
    
    context = {'form': form}
    return render(request, 'trial_balance.html', context)

@login_required
def profit_loss_report(request):
    """Generate profit and loss report"""
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            # Calculate revenue from journal entries
            revenue_entries = JournalEntryLine.objects.filter(
                account__account_type='revenue',
                entry_type='credit',
                journal_entry__date__range=[start_date, end_date]
            ).select_related('account')
            
            revenue_from_journal = revenue_entries.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            # Calculate revenue from paid service sales (not yet in journal entries)
            try:
                from production.models import ServiceSale
                service_sales_revenue = ServiceSale.objects.filter(
                    paid_status='paid',
                    sale_date__date__range=[start_date, end_date]
                ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            except:
                service_sales_revenue = Decimal('0.00')
            
            # Calculate revenue from paid store sales (not yet in journal entries)
            try:
                from production.models import StoreSale
                store_sales_revenue = StoreSale.objects.filter(
                    payment_status='paid',
                    sale_date__date__range=[start_date, end_date]
                ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            except:
                store_sales_revenue = Decimal('0.00')
            
            # Total revenue from all sources
            revenue = revenue_from_journal + service_sales_revenue + store_sales_revenue
            
            # Calculate cost of goods sold
            cogs_entries = JournalEntryLine.objects.filter(
                account__account_category='cost_of_goods_sold',
                entry_type='debit',
                journal_entry__date__range=[start_date, end_date]
            ).select_related('account')
            
            cost_of_goods_sold = cogs_entries.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            # Calculate operating expenses
            operating_expense_entries = JournalEntryLine.objects.filter(
                account__account_type='expense',
                account__account_category__in=['operating_expense', 'administrative_expense', 'financial_expense'],
                entry_type='debit',
                journal_entry__date__range=[start_date, end_date]
            ).select_related('account')
            
            operating_expenses = operating_expense_entries.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            # Total expenses
            expenses = cost_of_goods_sold + operating_expenses
            
            # Calculate net income
            gross_profit = revenue - cost_of_goods_sold
            net_income = revenue - expenses
            
            # Calculate performance metrics
            profit_margin = (net_income / revenue * 100) if revenue > 0 else 0
            expense_ratio = (expenses / revenue * 100) if revenue > 0 else 0
            
            # Revenue breakdown
            revenue_breakdown = []
            
            # Add journal entry revenue
            revenue_by_account = revenue_entries.values('account__account_name', 'account__account_code').annotate(
                amount=Sum('amount')
            ).order_by('-amount')
            
            for item in revenue_by_account:
                revenue_breakdown.append({
                    'account_name': item['account__account_name'],
                    'account_code': item['account__account_code'],
                    'amount': item['amount']
                })
            
            # Add service sales revenue
            if service_sales_revenue > 0:
                revenue_breakdown.append({
                    'account_name': 'Service Sales Revenue',
                    'account_code': 'SERV',
                    'amount': service_sales_revenue
                })
            
            # Add store sales revenue
            if store_sales_revenue > 0:
                revenue_breakdown.append({
                    'account_name': 'Store Sales Revenue',
                    'account_code': 'STORE',
                    'amount': store_sales_revenue
                })
            
            # COGS breakdown
            cogs_breakdown = []
            cogs_by_account = cogs_entries.values('account__account_name', 'account__account_code').annotate(
                amount=Sum('amount')
            ).order_by('-amount')
            
            for item in cogs_by_account:
                cogs_breakdown.append({
                    'account_name': item['account__account_name'],
                    'account_code': item['account__account_code'],
                    'amount': item['amount']
                })
            
            # Expenses breakdown by category
            expenses_breakdown = {}
            expense_by_category = operating_expense_entries.values(
                'account__account_category', 'account__account_name', 'account__account_code'
            ).annotate(amount=Sum('amount')).order_by('account__account_category', '-amount')
            
            for item in expense_by_category:
                category = item['account__account_category']
                if category not in expenses_breakdown:
                    expenses_breakdown[category] = {
                        'total': Decimal('0.00'),
                        'accounts': []
                    }
                
                expenses_breakdown[category]['total'] += item['amount']
                expenses_breakdown[category]['accounts'].append({
                    'account_name': item['account__account_name'],
                    'account_code': item['account__account_code'],
                    'amount': item['amount']
                })
            
            context = {
                'form': form,
                'start_date': start_date,
                'end_date': end_date,
                'revenue': revenue,
                'revenue_from_journal': revenue_from_journal,
                'service_sales_revenue': service_sales_revenue,
                'store_sales_revenue': store_sales_revenue,
                'expenses': expenses,
                'cost_of_goods_sold': cost_of_goods_sold,
                'operating_expenses': operating_expenses,
                'gross_profit': gross_profit,
                'net_income': net_income,
                'profit_margin': profit_margin,
                'expense_ratio': expense_ratio,
                'revenue_breakdown': revenue_breakdown,
                'cogs_breakdown': cogs_breakdown,
                'expenses_breakdown': expenses_breakdown,
            }
            return render(request, 'profit_loss_report.html', context)
    else:
        form = DateRangeForm()
    
    context = {'form': form}
    return render(request, 'profit_loss_report.html', context)

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
            return render(request, 'budget_report.html', context)
    else:
        form = BudgetReportForm()
    
    context = {'form': form}
    return render(request, 'budget_report.html', context)

@login_required
def manufacturing_report(request):
    """Manufacturing report showing production quantities and costs over time"""
    if request.method == 'POST':
        form = ManufacturingReportForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            selected_product = form.cleaned_data.get('product')
        else:
            # Default to last 30 days
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
            selected_product = None
    else:
        # Default to last 30 days
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        selected_product = None
        form = ManufacturingReportForm(initial={'start_date': start_date, 'end_date': end_date})

    # Check for CSV export
    if request.GET.get('export') == 'csv':
        return export_manufacturing_csv(request, start_date, end_date, selected_product)

    # Get manufacturing data from production app
    from production.models import ManufactureProduct, ManufacturedProductInventory
    from production.views import cost_per_unit  # Import the cost calculation function
    
    # Base query for production data
    production_query = ManufactureProduct.objects.filter(
        manufactured_at__date__range=[start_date, end_date]
    )
    
    # Apply product filter if selected
    if selected_product:
        production_query = production_query.filter(product=selected_product)
    
    # Production quantities by product
    production_data = production_query.values('product__product_name').annotate(
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')

    # Calculate costs for each product
    for item in production_data:
        # Get the product object to calculate cost
        product = ManufactureProduct.objects.filter(
            product__product_name=item['product__product_name'],
            manufactured_at__date__range=[start_date, end_date]
        ).first().product
        
        # Calculate cost per unit using the existing function
        cost_per = cost_per_unit(product)
        
        # Calculate total cost for this product using the same logic as manufactured product details
        total_ingredient_cost = 0
        for ingredient_cost in cost_per:
            # Calculate total quantity of each ingredient needed for the total quantity of product
            total_quantity_needed = ingredient_cost['quantity'] * item['total_quantity']
            total_cost_for_ingredient = ingredient_cost['cost_per_unit'] * total_quantity_needed
            total_ingredient_cost += total_cost_for_ingredient
        
        item['total_cost'] = total_ingredient_cost
        item['avg_cost_per_unit'] = total_ingredient_cost / item['total_quantity'] if item['total_quantity'] > 0 else 0

    # Daily production summary
    daily_production_query = ManufactureProduct.objects.filter(
        manufactured_at__date__range=[start_date, end_date]
    )
    
    # Apply product filter to daily production if selected
    if selected_product:
        daily_production_query = daily_production_query.filter(product=selected_product)
    
    daily_production = daily_production_query.extra(
        select={'day': 'date(manufactured_at)'}
    ).values('day').annotate(
        total_quantity=Sum('quantity'),
        product_count=Count('product', distinct=True)
    ).order_by('day')

    # Calculate costs for daily production
    for day in daily_production:
        day_products = ManufactureProduct.objects.filter(
            manufactured_at__date=day['day']
        )
        day_total_cost = 0
        for mp in day_products:
            cost_per = cost_per_unit(mp.product)
            # Calculate using the same logic as manufactured product details
            for ingredient_cost in cost_per:
                total_quantity_needed = ingredient_cost['quantity'] * mp.quantity
                total_cost_for_ingredient = ingredient_cost['cost_per_unit'] * total_quantity_needed
                day_total_cost += total_cost_for_ingredient
        day['total_cost'] = day_total_cost

    # Calculate efficiency metrics FIRST
    total_products_manufactured = sum(item['total_quantity'] for item in production_data)
    total_cost_incurred = sum(item['total_cost'] for item in production_data)
    avg_cost_per_product = total_cost_incurred / total_products_manufactured if total_products_manufactured > 0 else 0

    # Cost breakdown by category
    cost_breakdown = {}
    total_production_cost = 0
    
    # Create cost breakdown from production data
    for item in production_data:
        if item['total_cost'] > 0:
            # Use product name as category
            category = item['product__product_name']
            cost_breakdown[category] = item['total_cost']
            total_production_cost += item['total_cost']
    
    # If no cost breakdown from production data, create sample data for demonstration
    if not cost_breakdown:
        cost_breakdown = {
            'Raw Materials': total_cost_incurred * 0.6 if total_cost_incurred > 0 else 1000000,
            'Labor Costs': total_cost_incurred * 0.25 if total_cost_incurred > 0 else 400000,
            'Overhead': total_cost_incurred * 0.15 if total_cost_incurred > 0 else 250000,
        }
        total_production_cost = sum(cost_breakdown.values())

    # Inventory levels
    current_inventory = ManufacturedProductInventory.objects.values('product__product_name').annotate(
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')

    # Get recent manufacturing records for the period
    recent_manufacturing_query = ManufactureProduct.objects.filter(
        manufactured_at__date__range=[start_date, end_date]
    )
    
    # Apply product filter to recent records if selected
    if selected_product:
        recent_manufacturing_query = recent_manufacturing_query.filter(product=selected_product)
    
    recent_manufacturing_records = recent_manufacturing_query.select_related('product', 'production_order').order_by('-manufactured_at')[:10]

    context = {
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'selected_product': selected_product,
        'production_data': production_data,
        'daily_production': daily_production,
        'cost_breakdown': cost_breakdown,
        'total_production_cost': total_production_cost,
        'current_inventory': current_inventory,
        'recent_manufacturing_records': recent_manufacturing_records,
        'total_products_manufactured': total_products_manufactured,
        'total_cost_incurred': total_cost_incurred,
        'avg_cost_per_product': avg_cost_per_product,
    }
    
    return render(request, 'accounts/manufacturing_report.html', context)

def export_manufacturing_csv(request, start_date, end_date, selected_product):
    """Export manufacturing report data to CSV"""
    from production.models import ManufactureProduct, ManufacturedProductInventory
    from production.views import cost_per_unit
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="manufacturing_report_{start_date}_{end_date}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow(['Manufacturing Report', f'{start_date} to {end_date}'])
    writer.writerow([])
    
    # Summary section
    production_data = ManufactureProduct.objects.filter(
        manufactured_at__date__range=[start_date, end_date]
    ).values('product__product_name').annotate(
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')
    
    # Apply product filter if selected
    if selected_product:
        production_data = production_data.filter(product=selected_product)
    
    # Calculate costs for each product
    for item in production_data:
        # Get the product object to calculate cost
        product = ManufactureProduct.objects.filter(
            product__product_name=item['product__product_name'],
            manufactured_at__date__range=[start_date, end_date]
        ).first().product
        
        # Calculate cost per unit using the existing function
        cost_per = cost_per_unit(product)
        
        # Calculate total cost for this product
        total_ingredient_cost = 0
        for ingredient_cost in cost_per:
            total_quantity_needed = ingredient_cost['quantity'] * item['total_quantity']
            total_cost_for_ingredient = ingredient_cost['cost_per_unit'] * total_quantity_needed
            total_ingredient_cost += total_cost_for_ingredient
        
        item['total_cost'] = total_ingredient_cost
        item['avg_cost_per_unit'] = total_ingredient_cost / item['total_quantity'] if item['total_quantity'] > 0 else 0
    
    total_products_manufactured = sum(item['total_quantity'] for item in production_data)
    total_cost_incurred = sum(item['total_cost'] for item in production_data)
    avg_cost_per_product = total_cost_incurred / total_products_manufactured if total_products_manufactured > 0 else 0
    
    writer.writerow(['SUMMARY'])
    writer.writerow(['Total Products Manufactured', total_products_manufactured])
    writer.writerow(['Total Production Cost', total_cost_incurred])
    writer.writerow(['Average Cost per Product', avg_cost_per_product])
    writer.writerow([])
    
    # Production by product
    writer.writerow(['PRODUCTION BY PRODUCT'])
    writer.writerow(['Product Name', 'Quantity Manufactured', 'Total Cost', 'Avg Cost per Unit'])
    for item in production_data:
        writer.writerow([
            item['product__product_name'],
            item['total_quantity'],
            item['total_cost'],
            item['avg_cost_per_unit']
        ])
    writer.writerow([])
    
    # Daily production
    daily_production = ManufactureProduct.objects.filter(
        manufactured_at__date__range=[start_date, end_date]
    ).extra(
        select={'day': 'date(manufactured_at)'}
    ).values('day').annotate(
        total_quantity=Sum('quantity'),
        product_count=Count('product', distinct=True)
    ).order_by('day')
    
    # Apply product filter to daily production if selected
    if selected_product:
        daily_production = daily_production.filter(product=selected_product)
    
    # Calculate costs for daily production
    for day in daily_production:
        day_products = ManufactureProduct.objects.filter(
            manufactured_at__date=day['day']
        )
        day_total_cost = 0
        for mp in day_products:
            cost_per = cost_per_unit(mp.product)
            # Calculate using the same logic as manufactured product details
            for ingredient_cost in cost_per:
                total_quantity_needed = ingredient_cost['quantity'] * mp.quantity
                total_cost_for_ingredient = ingredient_cost['cost_per_unit'] * total_quantity_needed
                day_total_cost += total_cost_for_ingredient
        day['total_cost'] = day_total_cost
    
    writer.writerow(['DAILY PRODUCTION'])
    writer.writerow(['Date', 'Quantity Produced', 'Production Cost', 'Products Count'])
    for day in daily_production:
        writer.writerow([
            day['day'],
            day['total_quantity'],
            day['total_cost'],
            day['product_count']
        ])
    writer.writerow([])
    
    # Current inventory
    current_inventory = ManufacturedProductInventory.objects.values('product__product_name').annotate(
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')
    
    writer.writerow(['CURRENT INVENTORY'])
    writer.writerow(['Product Name', 'Current Stock'])
    for item in current_inventory:
        writer.writerow([item['product__product_name'], item['total_quantity']])
    
    return response

@login_required
def process_pending_sales(request):
    """Process pending sales and create journal entries"""
    if request.method == 'POST':
        try:
            from accounts.services import AccountingService
            
            # Process pending sales
            result = AccountingService.process_pending_sales()
            
            if result:
                messages.success(
                    request, 
                    f"Successfully processed {result['service_sales_processed']} service sales and "
                    f"{result['store_sales_processed']} store sales. Journal entries have been created."
                )
            else:
                messages.error(request, 'Error processing pending sales. Please check the logs.')
                
        except Exception as e:
            messages.error(request, f'Error: {e}')
    
    # Get counts of pending sales
    try:
        from production.models import ServiceSale, StoreSale
        
        pending_service_sales = ServiceSale.objects.filter(
            paid_status='paid'
        ).exclude(
            accounting_entries__isnull=False
        ).count()
        
        pending_store_sales = StoreSale.objects.filter(
            payment_status='paid'
        ).exclude(
            accounting_entries__isnull=False
        ).count()
        
        total_pending = pending_service_sales + pending_store_sales
        
    except Exception as e:
        pending_service_sales = 0
        pending_store_sales = 0
        total_pending = 0
    
    context = {
        'pending_service_sales': pending_service_sales,
        'pending_store_sales': pending_store_sales,
        'total_pending': total_pending,
    }
    
    return render(request, 'process_pending_sales.html', context)

@login_required
def ledger_entries(request):
    """View ledger entries for individual accounts with filtering and running balances"""
    # Get filter parameters
    selected_account = request.GET.get('account')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    entry_type = request.GET.get('entry_type')
    
    # Get all accounts for the dropdown
    accounts = ChartOfAccounts.objects.filter(is_active=True).order_by('account_code')
    
    # Start with base queryset
    ledger_entries = JournalEntryLine.objects.select_related(
        'journal_entry', 'account'
    ).order_by('journal_entry__date', 'journal_entry__created_at')
    
    # Apply filters
    if selected_account:
        ledger_entries = ledger_entries.filter(account_id=selected_account)
    if start_date:
        ledger_entries = ledger_entries.filter(journal_entry__date__gte=start_date)
    if end_date:
        ledger_entries = ledger_entries.filter(journal_entry__date__lte=end_date)
    if entry_type:
        ledger_entries = ledger_entries.filter(entry_type=entry_type)
    
    # Get selected account object for summary
    selected_account_obj = None
    if selected_account:
        selected_account_obj = ChartOfAccounts.objects.filter(id=selected_account).first()
    
    # Calculate opening balance (balance before start date if specified)
    opening_balance = Decimal('0.00')
    if selected_account_obj and start_date:
        opening_entries = JournalEntryLine.objects.filter(
            account=selected_account_obj,
            journal_entry__date__lt=start_date
        )
        opening_debits = opening_entries.filter(entry_type='debit').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        opening_credits = opening_entries.filter(entry_type='credit').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        opening_balance = opening_debits - opening_credits
    
    # Calculate running balances
    running_balance = opening_balance
    entries_with_balance = []
    
    for entry in ledger_entries:
        if entry.entry_type == 'debit':
            running_balance += entry.amount
        else:
            running_balance -= entry.amount
        
        entry.running_balance = running_balance
        entries_with_balance.append(entry)
    
    # Calculate totals
    total_debits = sum(entry.amount for entry in entries_with_balance if entry.entry_type == 'debit')
    total_credits = sum(entry.amount for entry in entries_with_balance if entry.entry_type == 'credit')
    current_balance = opening_balance + total_debits - total_credits
    
    # Pagination
    paginator = Paginator(entries_with_balance, 50)  # 50 entries per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'ledger_entries': page_obj,
        'accounts': accounts,
        'selected_account': selected_account,
        'selected_account_obj': selected_account_obj,
        'start_date': start_date,
        'end_date': end_date,
        'entry_type': entry_type,
        'opening_balance': opening_balance,
        'current_balance': current_balance,
        'total_debits': total_debits,
        'total_credits': total_credits,
    }
    
    return render(request, 'ledger_entries.html', context)

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
