from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from decimal import Decimal
from accounts.models import ChartOfAccounts, JournalEntry, JournalEntryLine
from production.models import Requisition, Supplier


@login_required
def accounts_payable_details(request):
    """
    Show detailed breakdown of Accounts Payable - what we owe to suppliers
    """
    # Get the Accounts Payable account
    accounts_payable_account = ChartOfAccounts.objects.filter(account_code='2000').first()
    
    if not accounts_payable_account:
        return render(request, 'accounts/accounts_payable_details.html', {
            'error': 'Accounts Payable account (2000) not found'
        })
    
    # Get all journal entry lines for Accounts Payable
    payable_entries = JournalEntryLine.objects.filter(
        account=accounts_payable_account
    ).select_related('journal_entry').order_by('-journal_entry__date')
    
    # Calculate totals
    total_credits = sum(e.amount for e in payable_entries if e.entry_type == 'credit')
    total_debits = sum(e.amount for e in payable_entries if e.entry_type == 'debit')
    net_payable = total_credits - total_debits
    
    # Group entries by supplier/reference for better understanding
    supplier_balances = {}
    detailed_entries = []
    
    for entry_line in payable_entries:
        je = entry_line.journal_entry
        
        # Extract supplier information from the reference or description
        supplier_name = "Unknown Supplier"
        requisition_no = None
        
        if je.reference.startswith('REQ-'):
            requisition_no = je.reference.replace('REQ-', '')
            try:
                requisition = Requisition.objects.get(requisition_no=requisition_no)
                supplier_name = requisition.supplier.name
            except Requisition.DoesNotExist:
                pass
        elif je.reference.startswith('PV-'):
            # Payment voucher - this should be a debit (payment made)
            if "to" in je.description.lower():
                supplier_name = je.description.split("to ")[-1]
        
        # Track by supplier
        if supplier_name not in supplier_balances:
            supplier_balances[supplier_name] = {
                'credits': Decimal('0'),
                'debits': Decimal('0'),
                'balance': Decimal('0'),
                'entries': []
            }
        
        if entry_line.entry_type == 'credit':
            supplier_balances[supplier_name]['credits'] += entry_line.amount
        else:
            supplier_balances[supplier_name]['debits'] += entry_line.amount
        
        supplier_balances[supplier_name]['balance'] = (
            supplier_balances[supplier_name]['credits'] - 
            supplier_balances[supplier_name]['debits']
        )
        supplier_balances[supplier_name]['entries'].append({
            'entry_line': entry_line,
            'journal_entry': je,
            'requisition_no': requisition_no
        })
        
        detailed_entries.append({
            'entry_line': entry_line,
            'journal_entry': je,
            'supplier_name': supplier_name,
            'requisition_no': requisition_no
        })
    
    # Get unpaid requisitions for verification
    unpaid_requisitions = Requisition.objects.filter(
        status='delivered'
    ).select_related('supplier')
    
    # Calculate total from unpaid requisitions
    requisition_totals = {}
    total_unpaid_from_requisitions = Decimal('0')
    
    for req in unpaid_requisitions:
        total_cost = req.total_cost or req.calculate_total_cost()
        if total_cost and total_cost > 0:
            total_unpaid_from_requisitions += total_cost
            
            supplier_name = req.supplier.name
            if supplier_name not in requisition_totals:
                requisition_totals[supplier_name] = {
                    'total_amount': Decimal('0'),
                    'requisitions': []
                }
            
            requisition_totals[supplier_name]['total_amount'] += total_cost
            requisition_totals[supplier_name]['requisitions'].append({
                'requisition': req,
                'amount': total_cost
            })
    
    context = {
        'accounts_payable_account': accounts_payable_account,
        'total_credits': total_credits,
        'total_debits': total_debits,
        'net_payable': net_payable,
        'supplier_balances': supplier_balances,
        'detailed_entries': detailed_entries,
        'unpaid_requisitions': unpaid_requisitions,
        'requisition_totals': requisition_totals,
        'total_unpaid_from_requisitions': total_unpaid_from_requisitions,
        'payable_entries_count': payable_entries.count(),
    }
    
    return render(request, 'accounts/accounts_payable_details.html', context)


@login_required
def supplier_payable_summary(request):
    """
    Summary view of what we owe each supplier
    """
    # Get all suppliers with delivered requisitions
    suppliers_with_debt = []
    
    for supplier in Supplier.objects.all():
        delivered_requisitions = supplier.requisition_set.filter(status='delivered')
        
        total_owed = Decimal('0')
        requisition_details = []
        
        for req in delivered_requisitions:
            req_total = req.total_cost or req.calculate_total_cost()
            if req_total and req_total > 0:
                total_owed += req_total
                requisition_details.append({
                    'requisition': req,
                    'amount': req_total
                })
        
        if total_owed > 0:
            suppliers_with_debt.append({
                'supplier': supplier,
                'total_owed': total_owed,
                'requisition_count': len(requisition_details),
                'requisition_details': requisition_details
            })
    
    # Sort by amount owed (highest first)
    suppliers_with_debt.sort(key=lambda x: x['total_owed'], reverse=True)
    
    total_all_suppliers = sum(s['total_owed'] for s in suppliers_with_debt)
    average_per_supplier = total_all_suppliers / len(suppliers_with_debt) if len(suppliers_with_debt) > 0 else Decimal('0')
    
    context = {
        'suppliers_with_debt': suppliers_with_debt,
        'total_all_suppliers': total_all_suppliers,
        'supplier_count': len(suppliers_with_debt),
        'average_per_supplier': average_per_supplier
    }
    
    return render(request, 'accounts/supplier_payable_summary.html', context)
