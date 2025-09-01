from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import date
from .models import (
    JournalEntry, JournalEntryLine, SalesRevenue, ProductionExpense, 
    StoreTransfer as AccountingStoreTransfer, StoreBudget, StoreFinancialSummary,
    ManufacturingRecord, PaymentRecord, CommissionExpense
)
from .models import ChartOfAccounts, Department
from django.db.models import Sum
from django.db import models

class AccountingService:
    """Service for automatic accounting entries from production data"""
    
    @staticmethod
    def create_sales_journal_entry(store_sale, user):
        """Create journal entry for store sale"""
        try:
            with transaction.atomic():
                # Create journal entry
                journal_entry = JournalEntry.objects.create(
                    date=store_sale.sale_date.date(),
                    reference=f"Sale-{store_sale.id}",
                    description=f"Store sale from {store_sale.customer.first_name}",
                    entry_type='sales',
                    department=Department.objects.filter(code='STORE').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )
                
                # Get revenue account (Store Sales Revenue)
                revenue_account = ChartOfAccounts.objects.filter(
                    account_code='4110'  # Store Sales Revenue
                ).first()
                
                # Get cash/accounts receivable account
                cash_account = ChartOfAccounts.objects.filter(
                    account_code='1000'  # Cash
                ).first()
                
                if revenue_account and cash_account:
                    # Credit Revenue
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=revenue_account,
                        entry_type='credit',
                        amount=store_sale.total_amount,
                        description=f"Revenue from sale {store_sale.id}"
                    )
                    
                    # Debit Cash/Accounts Receivable
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=cash_account,
                        entry_type='debit',
                        amount=store_sale.total_amount,
                        description=f"Cash received from sale {store_sale.id}"
                    )
                    
                    # Create sales revenue record
                    SalesRevenue.objects.create(
                        store_sale=store_sale,
                        journal_entry=journal_entry,
                        amount=store_sale.total_amount
                    )
                    
                    return journal_entry
                    
        except Exception as e:
            print(f"Error creating sales journal entry: {e}")
            return None
    
    @staticmethod
    def create_requisition_expense_journal_entry(requisition, user):
        """Create journal entry for production requisition when approved"""
        try:
            with transaction.atomic():
                # Calculate total requisition amount from items
                total_amount = sum(item.total_cost for item in requisition.requisitionitem_set.all())
                
                # Create journal entry
                journal_entry = JournalEntry.objects.create(
                    date=requisition.created_at.date(),
                    reference=f"Req-{requisition.requisition_no}",
                    description=f"Production requisition {requisition.requisition_no} - {requisition.supplier.name}",
                    entry_type='production',
                    department=Department.objects.filter(code='PROD').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )
                
                # Get expense account (Raw Materials)
                expense_account = ChartOfAccounts.objects.filter(
                    account_code='5100'  # Raw Materials
                ).first()
                
                # Get accounts payable account
                payable_account = ChartOfAccounts.objects.filter(
                    account_code='2000'  # Accounts Payable
                ).first()
                
                if expense_account and payable_account:
                    # Debit Raw Materials (inventory)
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=expense_account,
                        entry_type='debit',
                        amount=total_amount,
                        description=f"Raw materials for requisition {requisition.requisition_no}"
                    )
                    
                    # Credit Accounts Payable
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=payable_account,
                        entry_type='credit',
                        amount=total_amount,
                        description=f"Payable to {requisition.supplier.name} for requisition {requisition.requisition_no}"
                    )
                    
                    # Create production expense record
                    ProductionExpense.objects.create(
                        requisition=requisition,
                        journal_entry=journal_entry,
                        amount=total_amount
                    )
                    
                    return journal_entry
                    
        except Exception as e:
            print(f"Error creating requisition expense journal entry: {e}")
            return None
    
    @staticmethod
    def create_manufacturing_journal_entry(manufacture_product, user):
        """Create journal entry when products are manufactured"""
        try:
            with transaction.atomic():
                # Calculate manufacturing cost from raw material usage based on actual requisition costs
                from production.utils import get_raw_material_price_with_fallback
                total_cost = 0
                
                for ingredient in manufacture_product.used_ingredients.all():
                    # Get the actual cost from the latest requisition (most accurate pricing)
                    price_info = get_raw_material_price_with_fallback(ingredient.raw_material)
                    unit_price = price_info.get('price', 0)
                    
                    ingredient_cost = ingredient.quantity_used * unit_price
                    total_cost += ingredient_cost
                
                # Create journal entry
                journal_entry = JournalEntry.objects.create(
                    date=manufacture_product.manufactured_at.date(),
                    reference=f"MFG-{manufacture_product.batch_number}",
                    description=f"Manufacturing {manufacture_product.quantity} units of {manufacture_product.product.product_name}",
                    entry_type='production',
                    department=Department.objects.filter(code='PROD').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )
                
                # Get inventory account (Store Inventory)
                inventory_account = ChartOfAccounts.objects.filter(
                    account_code='1210'  # Store Inventory
                ).first()
                
                # Get raw materials account
                raw_materials_account = ChartOfAccounts.objects.filter(
                    account_code='5100'  # Raw Materials
                ).first()
                
                if inventory_account and raw_materials_account:
                    # Debit Finished Goods Inventory
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=inventory_account,
                        entry_type='debit',
                        amount=total_cost,
                        description=f"Finished goods inventory - {manufacture_product.product.product_name}"
                    )
                    
                    # Credit Raw Materials (transfer from raw materials to finished goods)
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=raw_materials_account,
                        entry_type='credit',
                        amount=total_cost,
                        description=f"Raw materials consumed for {manufacture_product.batch_number}"
                    )
                    
                    return journal_entry
                    
        except Exception as e:
            print(f"Error creating manufacturing journal entry: {e}")
            return None
    
    @staticmethod
    def create_store_transfer_journal_entry(store_transfer, user):
        """Create journal entry for store transfers"""
        try:
            with transaction.atomic():
                # Calculate total transfer value
                total_amount = sum(
                    item.quantity * item.product.product.wholesale_price  # Use wholesale price for transfers
                    for item in store_transfer.items.all()
                )
                
                # Create journal entry
                journal_entry = JournalEntry.objects.create(
                    date=store_transfer.date.date(),
                    reference=f"Transfer-{store_transfer.liv_main_transfer_number}",
                    description=f"Store transfer {store_transfer.liv_main_transfer_number}",
                    entry_type='system',
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )
                
                # Get inventory accounts
                main_store_inventory = ChartOfAccounts.objects.filter(
                    account_code='1210'  # Store Inventory (Main Store)
                ).first()
                
                branch_inventory = ChartOfAccounts.objects.filter(
                    account_code='1220'  # Store Equipment (Branch Stores)
                ).first()
                
                if main_store_inventory and branch_inventory:
                    # Debit Branch Inventory
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=branch_inventory,
                        entry_type='debit',
                        amount=total_amount,
                        description=f"Inventory transferred to branch stores"
                    )
                    
                    # Credit Main Store Inventory
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=main_store_inventory,
                        entry_type='credit',
                        amount=total_amount,
                        description=f"Inventory transferred from main store"
                    )
                    
                    # Create inventory transfer record
                    AccountingStoreTransfer.objects.create(
                        transfer=store_transfer,
                        journal_entry=journal_entry,
                        amount=total_amount,
                        transfer_type='store_to_store'
                    )
                    
                    return journal_entry
                    
        except Exception as e:
            print(f"Error creating store transfer journal entry: {e}")
            return None
    
    @staticmethod
    def create_payment_journal_entry(payment_voucher, user):
        """Create journal entry for payment vouchers"""
        try:
            with transaction.atomic():
                # Generate entry number manually to avoid race conditions
                year = timezone.now().year
                max_count = JournalEntry.objects.filter(
                    entry_number__startswith=f"JE-{year}"
                ).aggregate(max_num=models.Max('entry_number'))['max_num']
                
                if max_count:
                    # Extract the number from the max entry number
                    max_num = int(max_count.split('-')[-1])
                    new_count = max_num + 1
                else:
                    new_count = 1
                
                entry_number = f"JE-{year}-{new_count:04d}"
                
                # Create journal entry with explicit entry number
                journal_entry = JournalEntry.objects.create(
                    entry_number=entry_number,
                    date=payment_voucher.payment_date.date(),
                    reference=f"PV-{payment_voucher.voucher_number}",
                    description=f"Payment for LPO {payment_voucher.lpo.lpo_number}",
                    entry_type='system',
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )
                
                # Get accounts payable account
                payable_account = ChartOfAccounts.objects.filter(
                    account_code='2000'  # Accounts Payable
                ).first()
                
                # Get cash account
                cash_account = ChartOfAccounts.objects.filter(
                    account_code='1000'  # Cash
                ).first()
                
                if payable_account and cash_account:
                    # Debit Accounts Payable
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=payable_account,
                        entry_type='debit',
                        amount=payment_voucher.amount_paid,
                        description=f"Payment to supplier for LPO {payment_voucher.lpo.lpo_number}"
                    )
                    
                    # Credit Cash
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=cash_account,
                        entry_type='credit',
                        amount=payment_voucher.amount_paid,
                        description=f"Cash payment for LPO {payment_voucher.lpo.lpo_number}"
                    )
                    
                    return journal_entry
                else:
                    # If accounts not found, delete the journal entry and return None
                    journal_entry.delete()
                    print(f"Required accounts not found for payment voucher {payment_voucher.voucher_number}")
                    return None
                    
        except Exception as e:
            print(f"Error creating payment journal entry: {e}")
            return None
    
    @staticmethod
    def generate_store_financial_summary(store, start_date, end_date):
        """Generate financial summary for a store"""
        try:
            # Get store sales for the period
            store_sales = store.storesale_set.filter(
                date__range=[start_date, end_date]
            )
            
            total_sales = sum(sale.total_amount for sale in store_sales)
            
            # Calculate cost of goods sold (you may need to adjust this based on your model)
            total_cost = sum(sale.total_cost for sale in store_sales if hasattr(sale, 'total_cost'))
            
            # Get operating expenses from journal entries
            operating_expenses = JournalEntryLine.objects.filter(
                journal_entry__date__range=[start_date, end_date],
                account__account_category='operating_expense',
                entry_type='debit',
                journal_entry__department__code='STORE'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            # Create or update financial summary
            summary, created = StoreFinancialSummary.objects.get_or_create(
                store=store,
                date=end_date,
                defaults={
                    'total_sales': total_sales,
                    'total_cost': total_cost,
                    'operating_expenses': operating_expenses,
                }
            )
            
            if not created:
                summary.total_sales = total_sales
                summary.total_cost = total_cost
                summary.operating_expenses = operating_expenses
            
            summary.calculate_totals()
            return summary
            
        except Exception as e:
            print(f"Error generating store financial summary: {e}")
            return None
    
    @staticmethod
    def create_service_sale_journal_entry(service_sale, user):
        """Create journal entry for service sale when invoiced (creates accounts receivable)"""
        try:
            with transaction.atomic():
                # Check if journal entry already exists
                existing_entry = JournalEntry.objects.filter(
                    reference=f"ServiceSale-{service_sale.id}"
                ).first()
                
                if existing_entry:
                    print(f"Journal entry already exists for service sale {service_sale.id}")
                    return existing_entry
                
                # Generate entry number manually to avoid race conditions
                year = timezone.now().year
                max_count = JournalEntry.objects.filter(
                    entry_number__startswith=f"JE-{year}"
                ).aggregate(max_num=models.Max('entry_number'))['max_num']
                
                if max_count:
                    # Extract the number from the max entry number
                    max_num = int(max_count.split('-')[-1])
                    new_count = max_num + 1
                else:
                    new_count = 1
                
                entry_number = f"JE-{year}-{new_count:04d}"
                
                # Create journal entry with explicit entry number
                journal_entry = JournalEntry.objects.create(
                    entry_number=entry_number,
                    date=service_sale.sale_date.date(),
                    reference=f"ServiceSale-{service_sale.id}",
                    description=f"Service sale {service_sale.service_sale_number} from {service_sale.customer.first_name}",
                    entry_type='sales',
                    department=Department.objects.filter(code='SALON').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )
                
                # Get revenue account (Service Sales Revenue)
                revenue_account = ChartOfAccounts.objects.filter(
                    account_code='4120'  # Service Sales Revenue
                ).first()
                
                if not revenue_account:
                    # Create service sales revenue account if it doesn't exist
                    revenue_account = ChartOfAccounts.objects.create(
                        account_code='4120',
                        account_name='Service Sales Revenue',
                        account_type='revenue',
                        account_category='service_revenue',
                        is_active=True
                    )
                
                # Get accounts receivable account
                ar_account = ChartOfAccounts.objects.filter(
                    account_code='1100'  # Accounts Receivable
                ).first()
                
                if not ar_account:
                    # Create accounts receivable account if it doesn't exist
                    ar_account = ChartOfAccounts.objects.create(
                        account_code='1100',
                        account_name='Accounts Receivable',
                        account_type='asset',
                        account_category='current_asset',
                        is_active=True
                    )
                
                if revenue_account and ar_account:
                    # Credit Revenue
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=revenue_account,
                        entry_type='credit',
                        amount=service_sale.total_amount,
                        description=f"Service revenue from {service_sale.service_sale_number}"
                    )
                    
                    # Debit Accounts Receivable
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=ar_account,
                        entry_type='debit',
                        amount=service_sale.total_amount,
                        description=f"Service sale receivable from {service_sale.customer.first_name} {service_sale.customer.last_name}"
                    )
                    
                    # Create sales revenue record
                    SalesRevenue.objects.create(
                        service_sale=service_sale,
                        journal_entry=journal_entry,
                        amount=service_sale.total_amount
                    )
                    
                    print(f"Created journal entry for service sale {service_sale.id}: {journal_entry.entry_number}")
                    return journal_entry
                else:
                    # If accounts not found, delete the journal entry and return None
                    journal_entry.delete()
                    print(f"Required accounts not found for service sale {service_sale.id}")
                    return None
                    
        except Exception as e:
            print(f"Error creating service sale journal entry: {e}")
            return None
    
    @staticmethod
    def create_service_payment_journal_entry(service_sale, payment, user):
        """Create journal entry for service sale payment (reduces accounts receivable)"""
        try:
            with transaction.atomic():
                # Create journal entry
                journal_entry = JournalEntry.objects.create(
                    date=payment.payment_date.date(),
                    reference=f"Payment-{service_sale.service_sale_number}-{payment.id}",
                    description=f"Payment received for service sale {service_sale.service_sale_number} via {payment.payment_method}",
                    entry_type='payment',
                    department=Department.objects.filter(code='SALON').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )
                
                # Get accounts receivable account
                ar_account = ChartOfAccounts.objects.filter(
                    account_code='1100'  # Accounts Receivable
                ).first()
                
                # Get appropriate cash account based on payment method
                if payment.payment_method == 'cash':
                    cash_account = ChartOfAccounts.objects.filter(
                        account_code='1000'  # Cash
                    ).first()
                elif payment.payment_method in ['mobile_money', 'airtel_money']:
                    cash_account = ChartOfAccounts.objects.filter(
                        account_code='1010'  # Mobile Money
                    ).first()
                    if not cash_account:
                        cash_account = ChartOfAccounts.objects.create(
                            account_code='1010',
                            account_name='Mobile Money',
                            account_type='asset',
                            account_category='current_asset',
                            is_active=True
                        )
                elif payment.payment_method in ['visa', 'bank_transfer']:
                    cash_account = ChartOfAccounts.objects.filter(
                        account_code='1020'  # Bank Account
                    ).first()
                    if not cash_account:
                        cash_account = ChartOfAccounts.objects.create(
                            account_code='1020',
                            account_name='Bank Account',
                            account_type='asset',
                            account_category='current_asset',
                            is_active=True
                        )
                else:
                    # Default to cash
                    cash_account = ChartOfAccounts.objects.filter(
                        account_code='1000'  # Cash
                    ).first()
                
                if ar_account and cash_account:
                    # Debit Cash/Bank (increase cash)
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=cash_account,
                        entry_type='debit',
                        amount=payment.amount,
                        description=f"Payment received via {payment.payment_method} for {service_sale.service_sale_number}"
                    )
                    
                    # Credit Accounts Receivable (reduce receivable)
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=ar_account,
                        entry_type='credit',
                        amount=payment.amount,
                        description=f"Payment received from {service_sale.customer.first_name} {service_sale.customer.last_name}"
                    )
                    
                    # Create payment record for tracking
                    PaymentRecord.objects.create(
                        service_sale=service_sale,
                        payment=payment,
                        journal_entry=journal_entry,
                        amount=payment.amount
                    )
                    
                    print(f"Created payment journal entry {journal_entry.entry_number} for service sale {service_sale.id}")
                    return journal_entry
                else:
                    journal_entry.delete()
                    print(f"Required accounts not found for payment {payment.id}")
                    return None
                    
        except Exception as e:
            print(f"Error creating service payment journal entry: {e}")
            return None
    
    @staticmethod
    def create_store_sale_journal_entry(store_sale, user):
        """Create journal entry for store sale when paid"""
        try:
            with transaction.atomic():
                # Check if journal entry already exists
                existing_entry = JournalEntry.objects.filter(
                    reference=f"StoreSale-{store_sale.id}"
                ).first()
                
                if existing_entry:
                    print(f"Journal entry already exists for store sale {store_sale.id}")
                    return existing_entry
                
                # Create journal entry
                journal_entry = JournalEntry.objects.create(
                    date=store_sale.sale_date.date(),
                    reference=f"StoreSale-{store_sale.id}",
                    description=f"Store sale for {store_sale.customer.first_name}",
                    entry_type='sales',
                    department=Department.objects.filter(code='STORE').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )
                
                # Get revenue account (Store Sales Revenue)
                revenue_account = ChartOfAccounts.objects.filter(
                    account_code='4110'  # Store Sales Revenue
                ).first()
                
                if not revenue_account:
                    # Create store sales revenue account if it doesn't exist
                    revenue_account = ChartOfAccounts.objects.create(
                        account_code='4110',
                        account_name='Store Sales Revenue',
                        account_type='revenue',
                        account_category='store_revenue',
                        is_active=True
                    )
                
                # Get cash account
                cash_account = ChartOfAccounts.objects.filter(
                    account_code='1000'  # Cash
                ).first()
                
                if revenue_account and cash_account:
                    # Credit Revenue
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=revenue_account,
                        entry_type='credit',
                        amount=store_sale.total_amount,
                        description=f"Store revenue from sale {store_sale.id}"
                    )
                    
                    # Debit Cash
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=cash_account,
                        entry_type='debit',
                        amount=store_sale.total_amount,
                        description=f"Cash received for store sale {store_sale.id}"
                    )
                    
                    # Create sales revenue record
                    SalesRevenue.objects.create(
                        store_sale=store_sale,
                        journal_entry=journal_entry,
                        amount=store_sale.total_amount
                    )
                    
                    print(f"Created journal entry for store sale {store_sale.id}: {journal_entry.entry_number}")
                    return journal_entry
                    
        except Exception as e:
            print(f"Error creating store sale journal entry: {e}")
            return None

    @staticmethod
    def process_pending_sales():
        """Process all pending sales and create journal entries"""
        try:
            from production.models import ServiceSale, StoreSale
            
            # Process service sales
            pending_service_sales = ServiceSale.objects.filter(
                paid_status='paid'
            ).exclude(
                accounting_entries__isnull=False
            )
            
            service_sales_processed = 0
            for service_sale in pending_service_sales:
                # Use store manager or system user
                user = getattr(service_sale.store, 'manager', None)
                if not user:
                    # Create a system user if no manager
                    from django.contrib.auth.models import User
                    user, created = User.objects.get_or_create(
                        username='system',
                        defaults={'first_name': 'System', 'last_name': 'User'}
                    )
                
                if AccountingService.create_service_sale_journal_entry(service_sale, user):
                    service_sales_processed += 1
            
            # Process store sales
            pending_store_sales = StoreSale.objects.filter(
                payment_status='paid'
            ).exclude(
                accounting_entries__isnull=False
            )
            
            store_sales_processed = 0
            for store_sale in pending_store_sales:
                # Use customer user or system user
                user = getattr(store_sale.customer, 'user', None)
                if not user:
                    # Create a system user if no customer user
                    from django.contrib.auth.models import User
                    user, created = User.objects.get_or_create(
                        username='system',
                        defaults={'first_name': 'System', 'last_name': 'User'}
                    )
                
                if AccountingService.create_store_sale_journal_entry(store_sale, user):
                    store_sales_processed += 1
            
            return {
                'service_sales_processed': service_sales_processed,
                'store_sales_processed': store_sales_processed
            }
            
        except Exception as e:
            print(f"Error processing pending sales: {e}")
            return None

    @staticmethod
    def create_store_budget(store, account_code, amount, period, start_date, end_date, user, description=""):
        """Create budget for a specific store"""
        try:
            account = ChartOfAccounts.objects.filter(account_code=account_code).first()
            if not account:
                raise ValueError(f"Account with code {account_code} not found")
            
            budget = StoreBudget.objects.create(
                store=store,
                account=account,
                amount=amount,
                period=period,
                start_date=start_date,
                end_date=end_date,
                description=description,
                created_by=user
            )
            
            return budget
            
        except Exception as e:
            print(f"Error creating store budget: {e}")
            return None
    
    @staticmethod
    def create_service_commission_journal_entry(staff_commission, user):
        """Create journal entry when service commission is earned"""
        try:
            with transaction.atomic():
                # Check if journal entry already exists
                existing_expense = CommissionExpense.objects.filter(
                    staff_commission=staff_commission
                ).first()
                
                if existing_expense:
                    print(f"Commission journal entry already exists for {staff_commission.id}")
                    return existing_expense.journal_entry
                
                # Create journal entry
                journal_entry = JournalEntry.objects.create(
                    date=staff_commission.created_at.date(),
                    reference=f"ServiceCommission-{staff_commission.id}",
                    description=f"Service commission for {staff_commission.staff.first_name} - {staff_commission.service_sale_item.service.service.name}",
                    entry_type='system',
                    department=Department.objects.filter(code='SALES').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )
                
                # Get commission expense account
                expense_account = ChartOfAccounts.objects.filter(
                    account_code='6015'  # Service Commission Expense
                ).first()
                
                # Get commission payable account
                payable_account = ChartOfAccounts.objects.filter(
                    account_code='2110'  # Commission Payable
                ).first()
                
                if expense_account and payable_account:
                    # Dr. Service Commission Expense
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=expense_account,
                        entry_type='debit',
                        amount=staff_commission.commission_amount,
                        description=f"Service commission expense for {staff_commission.staff.first_name}"
                    )
                    
                    # Cr. Commission Payable
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=payable_account,
                        entry_type='credit',
                        amount=staff_commission.commission_amount,
                        description=f"Commission payable to {staff_commission.staff.first_name}"
                    )
                    
                    # Create commission expense record
                    CommissionExpense.objects.create(
                        staff_commission=staff_commission,
                        journal_entry=journal_entry,
                        amount=staff_commission.commission_amount,
                        commission_type='service'
                    )
                    
                    print(f"Created service commission journal entry: {journal_entry.entry_number}")
                    return journal_entry
                else:
                    print("Commission accounts not found. Please run setup_commission_accounts command.")
                    return None
                    
        except Exception as e:
            print(f"Error creating service commission journal entry: {e}")
            return None
    
    @staticmethod
    def create_product_commission_journal_entry(product_commission, user):
        """Create journal entry when product commission is earned"""
        try:
            with transaction.atomic():
                # Check if journal entry already exists
                existing_expense = CommissionExpense.objects.filter(
                    product_commission=product_commission
                ).first()
                
                if existing_expense:
                    print(f"Product commission journal entry already exists for {product_commission.id}")
                    return existing_expense.journal_entry
                
                # Create journal entry
                journal_entry = JournalEntry.objects.create(
                    date=product_commission.created_at.date(),
                    reference=f"ProductCommission-{product_commission.id}",
                    description=f"Product commission for {product_commission.staff.first_name} - {product_commission.product_sale_item.product.product.product_name}",
                    entry_type='system',
                    department=Department.objects.filter(code='SALES').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )
                
                # Get commission expense account
                expense_account = ChartOfAccounts.objects.filter(
                    account_code='6016'  # Product Commission Expense
                ).first()
                
                # Get commission payable account
                payable_account = ChartOfAccounts.objects.filter(
                    account_code='2110'  # Commission Payable
                ).first()
                
                if expense_account and payable_account:
                    # Dr. Product Commission Expense
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=expense_account,
                        entry_type='debit',
                        amount=product_commission.commission_amount,
                        description=f"Product commission expense for {product_commission.staff.first_name}"
                    )
                    
                    # Cr. Commission Payable
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=payable_account,
                        entry_type='credit',
                        amount=product_commission.commission_amount,
                        description=f"Commission payable to {product_commission.staff.first_name}"
                    )
                    
                    # Create commission expense record
                    CommissionExpense.objects.create(
                        product_commission=product_commission,
                        journal_entry=journal_entry,
                        amount=product_commission.commission_amount,
                        commission_type='product'
                    )
                    
                    print(f"Created product commission journal entry: {journal_entry.entry_number}")
                    return journal_entry
                else:
                    print("Commission accounts not found. Please run setup_commission_accounts command.")
                    return None
                    
        except Exception as e:
            print(f"Error creating product commission journal entry: {e}")
            return None
    
    @staticmethod
    def create_commission_payment_journal_entry(monthly_commission, user, payment_method='cash'):
        """Create journal entry when commission is paid to staff"""
        try:
            with transaction.atomic():
                # Check if journal entry already exists
                existing_expense = CommissionExpense.objects.filter(
                    monthly_commission=monthly_commission,
                    commission_type='monthly'
                ).first()
                
                if existing_expense:
                    print(f"Commission payment journal entry already exists for {monthly_commission.id}")
                    return existing_expense.journal_entry
                
                # Create journal entry
                journal_entry = JournalEntry.objects.create(
                    date=monthly_commission.paid_date.date() if monthly_commission.paid_date else date.today(),
                    reference=f"CommissionPayment-{monthly_commission.id}",
                    description=f"Commission payment to {monthly_commission.staff.first_name} for {monthly_commission.month_name}",
                    entry_type='system',
                    department=Department.objects.filter(code='SALES').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )
                
                # Get commission payable account
                payable_account = ChartOfAccounts.objects.filter(
                    account_code='2110'  # Commission Payable
                ).first()
                
                # Get appropriate cash account based on payment method
                cash_account_code = '1000'  # Default to Cash
                if payment_method == 'mobile_money':
                    cash_account_code = '1010'  # Mobile Money
                elif payment_method == 'bank_transfer':
                    cash_account_code = '1020'  # Bank Account
                
                cash_account = ChartOfAccounts.objects.filter(
                    account_code=cash_account_code
                ).first()
                
                if payable_account and cash_account:
                    # Dr. Commission Payable
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=payable_account,
                        entry_type='debit',
                        amount=monthly_commission.total_amount,
                        description=f"Payment of commission to {monthly_commission.staff.first_name}"
                    )
                    
                    # Cr. Cash/Bank
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=cash_account,
                        entry_type='credit',
                        amount=monthly_commission.total_amount,
                        description=f"Commission payment via {payment_method} to {monthly_commission.staff.first_name}"
                    )
                    
                    # Create commission expense record
                    CommissionExpense.objects.create(
                        monthly_commission=monthly_commission,
                        journal_entry=journal_entry,
                        amount=monthly_commission.total_amount,
                        commission_type='monthly'
                    )
                    
                    print(f"Created commission payment journal entry: {journal_entry.entry_number}")
                    return journal_entry
                else:
                    print("Required accounts not found. Please run setup_commission_accounts command.")
                    return None
                    
        except Exception as e:
            print(f"Error creating commission payment journal entry: {e}")
            return None 