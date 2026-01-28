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
    def create_raw_material_writeoff_journal_entry(write_off, user):
        """Create journal entry for an approved raw-material IncidentWriteOff.

        Logic:
        - Determine unit cost using latest RequisitionItem for the raw_material,
          falling back to RawMaterialPrice if needed.
        - Amount = write_off.quantity * unit_cost.
        - DR Raw Material Loss & Spoilage (expense/COGS)
        - CR Raw Materials Inventory (asset).
        """
        from decimal import Decimal
        from production.models import RequisitionItem, RawMaterialPrice

        try:
            with transaction.atomic():
                raw_material = write_off.raw_material

                # 1) Determine unit cost and total loss
                total_loss = Decimal('0.00')
                unit_cost = Decimal('0.00')
                price_source = "No requisition history found"

                # Latest requisition item with a valid price
                latest_req_item = (
                    RequisitionItem.objects.filter(
                        raw_material=raw_material,
                        price_per_unit__gt=0,
                    )
                    .order_by('-requisition__created_at')
                    .first()
                )

                if latest_req_item:
                    unit_cost = latest_req_item.price_per_unit
                    total_loss = write_off.quantity * unit_cost
                    price_source = f"Latest requisition: {latest_req_item.requisition.requisition_no}"
                else:
                    # Fallback: latest RawMaterialPrice if available
                    latest_price = (
                        RawMaterialPrice.objects.filter(
                            raw_material=raw_material,
                            is_current=True,
                        )
                        .order_by('-effective_date')
                        .first()
                    )
                    if latest_price:
                        unit_cost = latest_price.price
                        total_loss = write_off.quantity * unit_cost
                        price_source = f"Market price: {latest_price.supplier.name}"
                    else:
                        price_source = "No pricing information available"

                if total_loss <= 0:
                    print(
                        f"Skipping raw material write-off JE for {write_off.id}: "
                        f"total_loss is {total_loss} ({price_source})"
                    )
                    return None

                # 2) Get accounts
                # Raw Materials Inventory (asset)
                raw_materials_inventory_account = ChartOfAccounts.objects.filter(
                    account_name='Raw Materials Inventory',
                    account_type='asset',
                    account_category='current_asset',
                ).first()

                # Loss/Spillage expense (you should configure this in your CoA)
                loss_account = ChartOfAccounts.objects.filter(
                    account_name='Raw Material Loss & Spoilage',
                    account_type='expense',
                    account_category='cost_of_goods_sold',
                ).first()

                if not raw_materials_inventory_account or not loss_account:
                    print(
                        "Required accounts for raw material write-off not found. "
                        "Ensure 'Raw Materials Inventory' (asset/current_asset) and "
                        "'Raw Material Loss & Spoilage' (expense/cost_of_goods_sold) exist."
                    )
                    return None

                # 3) Create journal entry
                journal_entry = JournalEntry.objects.create(
                    date=write_off.date,
                    reference=f"RM-WO-{write_off.id}",
                    description=(
                        f"Raw material incident write-off for {raw_material.name} "
                        f"({price_source})"
                    ),
                    entry_type='production',
                    department=Department.objects.filter(code='PROD').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now(),
                )

                # 4) Post lines
                # DR Loss & Spoilage (expense/COGS)
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=loss_account,
                    entry_type='debit',
                    amount=total_loss,
                    description=(
                        f"Loss on write-off of {write_off.quantity} {raw_material.unit_measurement} "
                        f"of {raw_material.name}"
                    ),
                )

                # CR Raw Materials Inventory (asset)
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=raw_materials_inventory_account,
                    entry_type='credit',
                    amount=total_loss,
                    description=(
                        f"Inventory reduction for incident write-off of {raw_material.name}"
                    ),
                )

                return journal_entry

        except Exception as e:
            print(f"Error creating raw material write-off journal entry: {e}")
            return None

    @staticmethod
    def create_sales_journal_entry(store_sale, user):
        """Create journal entry for store sale.

        In addition to revenue and AR, this will compute Cost of Goods Sold (COGS)
        from the related SaleItem rows using the LivaraMainStore.unit_cost on each
        item.product, and post DR COGS / CR Inventory at cost.
        """
        try:
            with transaction.atomic():
                # Create journal entry
                journal_entry = JournalEntry.objects.create(
                    date=store_sale.order_date.date(),
                    reference=f"Sale-{store_sale.order_number}",
                    description=f"Store sale from {store_sale.customer.first_name} ({store_sale.order_number})",
                    entry_type='sales',
                    department=Department.objects.filter(code='STORE').first(),  # Assuming 'STORE' department exists
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )

                # Debit: Accounts Receivable (Asset) - Total amount due from customer
                ar_account = ChartOfAccounts.objects.filter(
                    account_name='Accounts Receivable', account_type='asset', account_category='current_asset'
                ).first()

                # Get revenue account (Store Sales Revenue)
                revenue_account = ChartOfAccounts.objects.filter(
                    account_name='Sales Revenue', account_type='revenue', account_category='operating_revenue'
                ).first()

                # Get VAT Payable account
                vat_payable_account = ChartOfAccounts.objects.filter(
                    account_name='VAT Payable', account_type='liability', account_category='tax_payable'
                ).first()

                # Get Withholding Tax Payable account
                wht_payable_account = ChartOfAccounts.objects.filter(
                    account_name='Withholding Tax Payable', account_type='liability', account_category='tax_payable'
                ).first()

                if ar_account and revenue_account:
                    # Debit Accounts Receivable
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=ar_account,
                        entry_type='debit',
                        amount=store_sale.total_amount,
                        description=f"Amount due from {store_sale.customer.first_name} for sale {store_sale.order_number}"
                    )

                    # Credit Sales Revenue
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=revenue_account,
                        entry_type='credit',
                        amount=store_sale.subtotal,
                        description=f"Revenue from sale {store_sale.order_number}"
                    )

                    # Credit VAT Payable if applicable
                    if store_sale.tax_amount > 0 and vat_payable_account:
                        JournalEntryLine.objects.create(
                            journal_entry=journal_entry,
                            account=vat_payable_account,
                            entry_type='credit',
                            amount=store_sale.tax_amount,
                            description=f"VAT collected on sale {store_sale.order_number}"
                        )

                    # Credit Withholding Tax Payable if applicable
                    if store_sale.withholding_tax > 0 and wht_payable_account:
                        JournalEntryLine.objects.create(
                            journal_entry=journal_entry,
                            account=wht_payable_account,
                            entry_type='credit',
                            amount=store_sale.withholding_tax,
                            description=(
                                f"Withholding tax collected on behalf of "
                                f"{store_sale.customer.first_name} for sale {store_sale.order_number}"
                            ),
                        )

                    # === Cost of Goods Sold & Inventory ===
                    # Use LivaraMainStore.unit_cost on each SaleItem.product to value COGS at cost.
                    cogs_account = ChartOfAccounts.objects.filter(account_code='5000').first()  # Cost of Goods Sold
                    inventory_account = ChartOfAccounts.objects.filter(account_code='1210').first()  # Store Inventory (Main Store)

                    total_cogs = Decimal('0.00')
                    if cogs_account and inventory_account:
                        # Iterate through sale items to compute total COGS at unit cost
                        sale_items = store_sale.saleitem_set.select_related('product').all()
                        for item in sale_items:
                            inventory_record = item.product  # LivaraMainStore instance
                            unit_cost = getattr(inventory_record, 'unit_cost', None)
                            if unit_cost is None:
                                continue  # Skip items without costing information

                            line_cogs = unit_cost * item.quantity
                            total_cogs += line_cogs

                        if total_cogs > 0:
                            # Debit Cost of Goods Sold
                            JournalEntryLine.objects.create(
                                journal_entry=journal_entry,
                                account=cogs_account,
                                entry_type='debit',
                                amount=total_cogs,
                                description=f"COGS for sale {store_sale.order_number}"
                            )

                            # Credit Inventory (reduce Store Inventory at cost)
                            JournalEntryLine.objects.create(
                                journal_entry=journal_entry,
                                account=inventory_account,
                                entry_type='credit',
                                amount=total_cogs,
                                description=f"Inventory reduction for sale {store_sale.order_number}"
                            )

                    # Create sales revenue record
                    SalesRevenue.objects.create(
                        store_sale=store_sale,
                        journal_entry=journal_entry,
                        amount=store_sale.total_amount,
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
                # Create journal entry
                journal_entry = JournalEntry.objects.create(
                    date=requisition.created_at.date(),
                    reference=f"Req-{requisition.requisition_no}",
                    description=f"Production requisition {requisition.requisition_no} - {requisition.supplier.name}",
                    entry_type='production',
                    department=Department.objects.filter(code='PROD').first(), # Assuming 'PROD' department exists
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )
                
                # Debit: Raw Materials Inventory (Asset)
                raw_materials_inventory_account = ChartOfAccounts.objects.filter(
                    account_name='Raw Materials Inventory', account_type='asset', account_category='current_asset'
                ).first()

                # Debit: Tax Receivable (Asset) for Input VAT
                tax_receivable_account = ChartOfAccounts.objects.filter(
                    account_name='Tax Receivable', account_type='asset', account_category='tax_receivable'
                ).first()
                
                # Get accounts payable account
                payable_account = ChartOfAccounts.objects.filter(
                    account_name='Accounts Payable', account_type='liability', account_category='current_liability'
                ).first()
                
                if raw_materials_inventory_account and payable_account:
                    # Debit Raw Materials Inventory
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=raw_materials_inventory_account,
                        entry_type='debit',
                        amount=requisition.calculate_subtotal_before_tax(),
                        description=f"Raw materials for requisition {requisition.requisition_no}"
                    )
                    
                    # Debit Tax Receivable if applicable
                    total_tax_amount = requisition.calculate_total_tax()
                    if total_tax_amount > 0 and tax_receivable_account:
                        JournalEntryLine.objects.create(
                            journal_entry=journal_entry,
                            account=tax_receivable_account,
                            entry_type='debit',
                            amount=total_tax_amount,
                            description=f"VAT paid on raw material purchase for requisition {requisition.requisition_no}"
                        )

                    # Credit Accounts Payable (total including tax)
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=payable_account,
                        entry_type='credit',
                        amount=requisition.calculate_grand_total_with_tax(), # Total including tax
                        description=f"Payable to {requisition.supplier.name} for requisition {requisition.requisition_no}"
                    )

                    # Handle Expense Items (if any) - Debit to their respective expense accounts
                    for expense_item in requisition.expense_items.all():
                        JournalEntryLine.objects.create(
                            journal_entry=journal_entry,
                            account=expense_item.expense_account,
                            entry_type='debit',
                            amount=expense_item.amount,
                            description=f"Expense for {expense_item.description} related to requisition {requisition.requisition_no}"
                        )
                    
                    # Create production expense record (assuming ProductionExpense tracks total requisition value)
                    ProductionExpense.objects.create(
                        requisition=requisition,
                        journal_entry=journal_entry,
                        amount=requisition.calculate_grand_total_with_tax() # Assuming ProductionExpense tracks total cost
                    )
                    
                    return journal_entry
                    
        except Exception as e:
            print(f"Error creating requisition expense journal entry: {e}")
            return None
    
    @staticmethod
    def create_manufacturing_journal_entry(manufacture_product, user):
        """Create journal entry when products are manufactured.

        `manufacture_product` is a production.models.ManufactureProduct instance.
        Total cost is primarily taken from its total_production_cost field when available,
        falling back to summing its used_ingredients via get_raw_material_price_with_fallback.

        This method also ensures a ManufacturingRecord exists and, where possible,
        links it to the corresponding ManufacturedProductInventory (production-store
        inventory for the manufactured batch).
        """
        try:
            with transaction.atomic():
                from production.utils import get_raw_material_price_with_fallback
                from production.models import ManufacturedProductInventory

                # 1) Prefer explicit total_production_cost recorded on the batch
                total_cost = manufacture_product.total_production_cost or Decimal('0.00')

                # 2) If not set, fall back to computing from used_ingredients
                if total_cost <= 0:
                    total_cost = Decimal('0.00')
                    for ingredient in manufacture_product.used_ingredients.all():
                        price_info = get_raw_material_price_with_fallback(ingredient.raw_material)
                        unit_price = price_info.get('price', Decimal('0.00'))
                        ingredient_cost = Decimal(ingredient.quantity_used) * unit_price
                        total_cost += ingredient_cost

                # If still zero, do not create a meaningless JE
                if total_cost <= 0:
                    print(f"Skipping manufacturing JE for {manufacture_product.id}: total_cost is 0")
                    return None

                # Create journal entry
                journal_entry = JournalEntry.objects.create(
                    date=manufacture_product.manufactured_at.date(),
                    reference=f"MFG-{manufacture_product.batch_number}",
                    description=(
                        f"Manufacturing {manufacture_product.quantity} units of "
                        f"{manufacture_product.product.product_name}"
                    ),
                    entry_type='production',
                    department=Department.objects.filter(code='PROD').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )

                # Get inventory account (Finished Goods) and raw materials account
                inventory_account = ChartOfAccounts.objects.filter(
                    account_code='1210'  # Finished Goods / Store Inventory
                ).first()

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

                    # Try to link this JE to a production-store inventory record
                    inventory = ManufacturedProductInventory.objects.filter(
                        product=manufacture_product.product,
                        batch_number=manufacture_product.batch_number,
                    ).first()

                    if inventory is not None:
                        mr, created = ManufacturingRecord.objects.get_or_create(
                            manufacture_product=inventory,
                            journal_entry=journal_entry,
                            defaults={'amount': total_cost},
                        )
                        # Keep amount in sync if record already existed
                        if not created and mr.amount != total_cost:
                            mr.amount = total_cost
                            mr.save(update_fields=['amount'])
                    else:
                        # Create a placeholder record that will be linked to
                        # ManufacturedProductInventory when it is created.
                        mr, created = ManufacturingRecord.objects.get_or_create(
                            manufacture_product=None,
                            journal_entry=journal_entry,
                            defaults={'amount': total_cost},
                        )
                        if not created and mr.amount != total_cost:
                            mr.amount = total_cost
                            mr.save(update_fields=['amount'])

                    return journal_entry

        except Exception as e:
            print(f"Error creating manufacturing journal entry: {e}")
            return None
    
    @staticmethod
    def create_store_transfer_journal_entry(store_transfer, user):
        """Create journal entry for store transfers.

        Each transfer line is valued at the inventory unit_cost of the
        underlying inventory record (item.product), rather than sales
        price or wholesale price, so that transfers move inventory at
        cost between locations without affecting profit.
        """
        try:
            with transaction.atomic():
                # Calculate total transfer value at inventory cost
                total_amount = Decimal('0.00')
                for item in store_transfer.items.all():
                    # item.product is expected to be an inventory record (e.g., LivaraMainStore)
                    inventory_record = item.product
                    unit_cost = getattr(inventory_record, 'unit_cost', None)
                    if unit_cost is None:
                        unit_cost = Decimal('0.00')

                    total_amount += unit_cost * item.quantity

                # If nothing to value, skip creating a JE
                if total_amount <= 0:
                    print(f"Skipping store transfer JE for {store_transfer.id}: total_amount is 0")
                    return None

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
                    account_code='1220'  # Store Inventory (Branch Stores)
                ).first()

                if main_store_inventory and branch_inventory:
                    # Debit Branch Inventory
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=branch_inventory,
                        entry_type='debit',
                        amount=total_amount,
                        description="Inventory transferred to branch stores at cost",
                    )

                    # Credit Main Store Inventory
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=main_store_inventory,
                        entry_type='credit',
                        amount=total_amount,
                        description="Inventory transferred from main store at cost",
                    )

                    # Create inventory transfer record
                    AccountingStoreTransfer.objects.create(
                        transfer=store_transfer,
                        journal_entry=journal_entry,
                        amount=total_amount,
                        transfer_type='store_to_store',
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
    def create_store_sale_payment_journal_entry(store_sale_payment, user):
        """Create journal entry when a payment is made against a StoreSale."""
        try:
            with transaction.atomic():
                journal_entry = JournalEntry.objects.create(
                    date=store_sale_payment.payment_date.date(),
                    reference=f"Payment-{store_sale_payment.payment_reference}",
                    description=f"Payment for Store Sale {store_sale_payment.receipt.store_sale.order_number} from {store_sale_payment.customer_name}",
                    entry_type='payment',
                    department=Department.objects.filter(code='STORE').first(), # Assuming 'STORE' department exists
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )

                # Debit: Cash/Bank (Asset)
                # Determine the cash/bank account based on payment method
                cash_account = None
                if store_sale_payment.payment_method == 'cash':
                    cash_account = ChartOfAccounts.objects.filter(account_code='1000', account_type='asset', account_category='current_asset').first()
                elif store_sale_payment.payment_method == 'mobile_money':
                    cash_account = ChartOfAccounts.objects.filter(account_code='1010', account_type='asset', account_category='current_asset').first()
                elif store_sale_payment.payment_method == 'bank_transfer':
                    cash_account = ChartOfAccounts.objects.filter(account_code='1020', account_type='asset', account_category='current_asset').first()
                # Add more payment methods as needed

                # Credit: Accounts Receivable (Asset)
                ar_account = ChartOfAccounts.objects.filter(
                    account_name='Accounts Receivable', account_type='asset', account_category='current_asset'
                ).first()
                
                if cash_account and ar_account:
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=cash_account,
                        entry_type='debit',
                        amount=store_sale_payment.amount_paid,
                        description=f"Cash received for sale {store_sale_payment.receipt.store_sale.order_number}"
                    )
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=ar_account,
                        entry_type='credit',
                        amount=store_sale_payment.amount_paid,
                        description=f"Reduction of receivable for sale {store_sale_payment.receipt.store_sale.order_number}"
                    )
                    return journal_entry
                else:
                    journal_entry.delete()
                    print(f"Required accounts not found for store sale payment {store_sale_payment.payment_reference}")
                    return None

        except Exception as e:
            print(f"Error creating store sale payment journal entry: {e}")
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