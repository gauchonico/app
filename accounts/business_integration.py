from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import date
from .models import JournalEntry, JournalEntryLine, ChartOfAccounts, Department
from .services import AccountingService
from production.models import (
    Requisition, LPO, PaymentVoucher, GoodsReceivedNote,
    StoreSale, ServiceSale, ManufactureProduct,
    StaffCommission, StaffProductCommission
)
from production.utils import get_raw_material_price_with_fallback

class LivaraBusinessIntegration:
    """Integrate LIVARA business operations with accounting system"""
    
    @staticmethod
    def sync_requisition_to_accounting(requisition, user):
        """Sync requisition to accounting - create accounts payable"""
        try:
            with transaction.atomic():
                # Check if already synced
                existing_entry = JournalEntry.objects.filter(
                    reference=f"REQ-{requisition.requisition_no}"
                ).first()
                
                if existing_entry:
                    return existing_entry
                
                # Create journal entry for requisition (when delivered)
                if requisition.status == 'delivered':
                    journal_entry = JournalEntry.objects.create(
                        date=requisition.created_at.date(),
                        reference=f"REQ-{requisition.requisition_no}",
                        description=f"Raw materials received from {requisition.supplier.name}",
                        entry_type='system',
                        department=Department.objects.filter(code='PROD').first(),
                        created_by=user,
                        is_posted=True,
                        posted_at=timezone.now()
                    )
                    
                    # Get accounts
                    raw_materials_account = ChartOfAccounts.objects.filter(account_code='1200').first()

                    # Prefer supplier-specific AP account if configured
                    supplier = requisition.supplier
                    accounts_payable_account = getattr(supplier, 'payables_account', None)
                    if accounts_payable_account is None:
                        accounts_payable_account = ChartOfAccounts.objects.filter(account_code='2000').first()
                    
                    # Calculate total cost if not already stored
                    total_amount = requisition.total_cost or requisition.calculate_total_cost()
                    
                    if raw_materials_account and accounts_payable_account and total_amount and total_amount > 0:
                        # Dr. Raw Materials Inventory
                        JournalEntryLine.objects.create(
                            journal_entry=journal_entry,
                            account=raw_materials_account,
                            entry_type='debit',
                            amount=total_amount,
                            description=f"Raw materials from {requisition.supplier.name}"
                        )
                        
                        # Cr. Accounts Payable
                        JournalEntryLine.objects.create(
                            journal_entry=journal_entry,
                            account=accounts_payable_account,
                            entry_type='credit',
                            amount=total_amount,
                            description=f"Payable to {requisition.supplier.name}"
                        )
                        
                        return journal_entry
                        
        except Exception as e:
            print(f"Error syncing requisition {requisition.requisition_no}: {e}")
            return None
    
    @staticmethod
    def sync_payment_voucher_to_accounting(payment_voucher, user):
        """Sync payment voucher to accounting - record payment"""
        try:
            with transaction.atomic():
                # Check if already synced
                existing_entry = JournalEntry.objects.filter(
                    reference=f"PV-{payment_voucher.voucher_number}"
                ).first()
                
                if existing_entry:
                    return existing_entry
                
                journal_entry = JournalEntry.objects.create(
                    date=payment_voucher.payment_date.date(),
                    reference=f"PV-{payment_voucher.voucher_number}",
                    description=f"Payment to {payment_voucher.lpo.requisition.supplier.name}",
                    entry_type='system',
                    department=Department.objects.filter(code='PROD').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )
                
                # Get accounts (prefer supplier-specific AP if configured)
                supplier = payment_voucher.lpo.requisition.supplier
                accounts_payable_account = getattr(supplier, 'payables_account', None)
                if accounts_payable_account is None:
                    accounts_payable_account = ChartOfAccounts.objects.filter(account_code='2000').first()
                
                # Determine cash account based on payment method
                cash_account_code = '1000'  # Default to cash
                if payment_voucher.payment_account:
                    # Use the specified payment account
                    cash_account = payment_voucher.payment_account
                else:
                    # Use legacy pay_by field
                    if payment_voucher.pay_by == 'bank':
                        cash_account_code = '1020'
                    elif payment_voucher.pay_by == 'mobile':
                        cash_account_code = '1010'
                    
                    cash_account = ChartOfAccounts.objects.filter(account_code=cash_account_code).first()
                
                if accounts_payable_account and cash_account:
                    # Dr. Accounts Payable
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=accounts_payable_account,
                        entry_type='debit',
                        amount=payment_voucher.amount_paid,
                        description=f"Payment to {payment_voucher.lpo.requisition.supplier.name}"
                    )
                    
                    # Cr. Cash/Bank/Mobile
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=cash_account,
                        entry_type='credit',
                        amount=payment_voucher.amount_paid,
                        description=f"Payment via {cash_account.account_name}"
                    )
                    
                    return journal_entry
                    
        except Exception as e:
            print(f"Error syncing payment voucher {payment_voucher.voucher_number}: {e}")
            return None
    
    @staticmethod
    def sync_store_sale_to_accounting(store_sale, user):
        """Sync store sale to accounting - revenue recognition"""
        try:
            with transaction.atomic():
                # Check if already synced
                existing_entry = JournalEntry.objects.filter(
                    reference=f"StoreSale-{store_sale.id}"
                ).first()
                
                if existing_entry:
                    return existing_entry
                
                # Only create entry if sale is confirmed/invoiced
                if store_sale.status in ['confirmed', 'invoiced']:
                    journal_entry = JournalEntry.objects.create(
                        date=store_sale.order_date.date(),
                        reference=f"StoreSale-{store_sale.id}",
                        description=f"Store sale to {store_sale.customer.first_name} {store_sale.customer.last_name}",
                        entry_type='system',
                        department=Department.objects.filter(code='SALES').first(),
                        created_by=user,
                        is_posted=True,
                        posted_at=timezone.now()
                    )
                    
                    # Get accounts
                    ar_account = ChartOfAccounts.objects.filter(account_code='1100').first()
                    revenue_account = ChartOfAccounts.objects.filter(account_code='4100').first()
                    vat_account = ChartOfAccounts.objects.filter(account_code='2020').first()
                    
                    if ar_account and revenue_account:
                        # Dr. Accounts Receivable - Store Sales
                        JournalEntryLine.objects.create(
                            journal_entry=journal_entry,
                            account=ar_account,
                            entry_type='debit',
                            amount=store_sale.total_amount,
                            description=f"Store sale to {store_sale.customer.first_name}"
                        )
                        
                        # Cr. Store Sales Revenue
                        revenue_amount = store_sale.subtotal or store_sale.total_amount
                        JournalEntryLine.objects.create(
                            journal_entry=journal_entry,
                            account=revenue_account,
                            entry_type='credit',
                            amount=revenue_amount,
                            description=f"Store sales revenue"
                        )
                        
                        # Cr. VAT Payable (if applicable)
                        if store_sale.tax_amount and store_sale.tax_amount > 0 and vat_account:
                            JournalEntryLine.objects.create(
                                journal_entry=journal_entry,
                                account=vat_account,
                                entry_type='credit',
                                amount=store_sale.tax_amount,
                                description=f"VAT on store sale"
                            )
                        
                        return journal_entry
                        
        except Exception as e:
            print(f"Error syncing store sale {store_sale.id}: {e}")
            return None
    
    @staticmethod
    def sync_manufacturing_to_accounting(manufacture_product, user):
        """Sync manufacturing to accounting - cost tracking"""
        try:
            with transaction.atomic():
                # Check if already synced
                existing_entry = JournalEntry.objects.filter(
                    reference=f"MFG-{manufacture_product.id}"
                ).first()
                
                if existing_entry:
                    return existing_entry
                
                journal_entry = JournalEntry.objects.create(
                    date=manufacture_product.manufactured_at.date(),
                    reference=f"MFG-{manufacture_product.id}",
                    description=f"Manufacturing of {manufacture_product.product.product_name}",
                    entry_type='system',
                    department=Department.objects.filter(code='PROD').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )
                
                # Get accounts
                wip_account = ChartOfAccounts.objects.filter(account_code='1210').first()
                finished_goods_account = ChartOfAccounts.objects.filter(account_code='1220').first()
                raw_materials_account = ChartOfAccounts.objects.filter(account_code='1200').first()
                
                # Use stored production cost if available, otherwise calculate
                if manufacture_product.total_production_cost:
                    total_raw_material_cost = manufacture_product.total_production_cost
                else:
                    # Fallback calculation (but this should be avoided)
                    total_raw_material_cost = Decimal('0')
                    # Use a set to track already processed ingredients to avoid duplicates
                    processed_ingredients = set()
                    
                    for ingredient in manufacture_product.used_ingredients.all():
                        # Create a unique key for each ingredient
                        ingredient_key = f"{ingredient.raw_material.id}_{ingredient.raw_material.name}"
                        
                        if ingredient_key not in processed_ingredients:
                            processed_ingredients.add(ingredient_key)
                            # Get raw material price using proper fallback
                            price_info = get_raw_material_price_with_fallback(ingredient.raw_material)
                            material_price = price_info.get('price', Decimal('0')) if price_info else Decimal('0')
                            material_cost = ingredient.quantity_used * material_price
                            total_raw_material_cost += material_cost
                
                if raw_materials_account and finished_goods_account and total_raw_material_cost > 0:
                    # Dr. Finished Goods Inventory
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=finished_goods_account,
                        entry_type='debit',
                        amount=total_raw_material_cost,
                        description=f"Manufacturing cost - {manufacture_product.product.product_name}"
                    )
                    
                    # Cr. Raw Materials Inventory
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=raw_materials_account,
                        entry_type='credit',
                        amount=total_raw_material_cost,
                        description=f"Raw materials used in production"
                    )
                    
                    return journal_entry
                    
        except Exception as e:
            print(f"Error syncing manufacturing {manufacture_product.id}: {e}")
            return None
    
    @staticmethod
    def sync_all_existing_data(user):
        """Sync all existing business data to accounting"""
        results = {
            'requisitions': 0,
            'payments': 0,
            'store_sales': 0,
            'service_sales': 0,
            'manufacturing': 0,
            'commissions': 0,
            'errors': []
        }
        
        try:
            # Sync delivered requisitions
            requisitions = Requisition.objects.filter(status='delivered')
            for req in requisitions:
                if LivaraBusinessIntegration.sync_requisition_to_accounting(req, user):
                    results['requisitions'] += 1
            
            # Sync payment vouchers
            payment_vouchers = PaymentVoucher.objects.all()
            for pv in payment_vouchers:
                if LivaraBusinessIntegration.sync_payment_voucher_to_accounting(pv, user):
                    results['payments'] += 1
            
            # Sync confirmed store sales
            store_sales = StoreSale.objects.filter(status__in=['confirmed', 'invoiced'])
            for sale in store_sales:
                if LivaraBusinessIntegration.sync_store_sale_to_accounting(sale, user):
                    results['store_sales'] += 1
            
            # Sync service sales (already implemented)
            service_sales = ServiceSale.objects.filter(invoice_status='invoiced')
            for sale in service_sales:
                if AccountingService.create_service_sale_journal_entry(sale, user):
                    results['service_sales'] += 1
            
            # Sync manufacturing
            manufacturing = ManufactureProduct.objects.all()
            for mfg in manufacturing:
                if LivaraBusinessIntegration.sync_manufacturing_to_accounting(mfg, user):
                    results['manufacturing'] += 1
            
            # Commissions already synced
            results['commissions'] = 'Already synced'
            
            return results
            
        except Exception as e:
            results['errors'].append(str(e))
            return results
