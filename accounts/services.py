from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import date
from .models import (
    JournalEntry, JournalEntryLine, SalesRevenue, ProductionExpense, 
    StoreTransfer as AccountingStoreTransfer, StoreBudget, StoreFinancialSummary,
    ManufacturingRecord, PaymentRecord, CommissionExpense
)
from .models import ChartOfAccounts, Department, Budget, StoreBudget
from django.db.models import Sum
from django.db import models


class BudgetService:
    """Helpers for checking department- and store-level budgets before approvals."""

    @staticmethod
    def check_budget_for_department(dept_code: str, account_code: str, amount, when=None):
        """Return (ok: bool, budget: Budget|None, remaining: Decimal, over_by: Decimal).

        - ok: True if within budget or no active budget found.
        - budget: the matching Budget instance, if any.
        - remaining: remaining_amount on that budget (0 if none).
        - over_by: positive amount by which the requested spend exceeds remaining.
        """
        from decimal import Decimal

        when = when or timezone.now().date()
        amount = Decimal(str(amount))

        try:
            dept = Department.find_by_code(dept_code) if hasattr(Department, 'find_by_code') else Department.objects.get(code=dept_code)
            account = ChartOfAccounts.objects.get(account_code=account_code)
        except (Department.DoesNotExist, ChartOfAccounts.DoesNotExist):
            # If we cannot resolve dept/account, do not block
            return True, None, Decimal('0.00'), Decimal('0.00')

        b = Budget.objects.filter(
            department=dept,
            account=account,
            is_active=True,
            start_date__lte=when,
            end_date__gte=when,
        ).first()

        if not b:
            # No specific budget configured for this combination
            return True, None, Decimal('0.00'), Decimal('0.00')

        remaining = b.remaining_amount
        over_by = amount - remaining
        ok = amount <= remaining
        return ok, b, remaining, (over_by if over_by > 0 else Decimal('0.00'))

    @staticmethod
    def check_budget_for_store(store, account_code: str, amount, when=None):
        """Return (ok: bool, store_budget: StoreBudget|None, remaining: Decimal, over_by: Decimal)."""
        from decimal import Decimal

        when = when or timezone.now().date()
        amount = Decimal(str(amount))

        try:
            account = ChartOfAccounts.objects.get(account_code=account_code)
        except ChartOfAccounts.DoesNotExist:
            return True, None, Decimal('0.00'), Decimal('0.00')

        sb = StoreBudget.objects.filter(
            store=store,
            account=account,
            is_active=True,
            start_date__lte=when,
            end_date__gte=when,
        ).first()

        if not sb:
            return True, None, Decimal('0.00'), Decimal('0.00')

        remaining = sb.remaining_amount
        over_by = amount - remaining
        ok = amount <= remaining
        return ok, sb, remaining, (over_by if over_by > 0 else Decimal('0.00'))


class AccountingService:
    """Service for automatic accounting entries from production data"""
    
    @staticmethod
    def create_accessory_consumption_journal_entry(service_sale, user):
        """Record salon supplies expense when accessories are consumed in a paid ServiceSale.

        Trigger: ServiceSale has been fully paid (paid_status == 'paid') and has
        one or more AccessorySaleItem rows that represent **internal use** of
        accessories (they do not appear on the customer's receipt as separate
        charge lines, or are priced at 0 for internal consumption).

        For each such sale, we:
        - Determine the store from service_sale.store.
        - Map that store to the correct "Accessory Inventory {Store}" account
          (e.g. 31200/31201/31202).
        - Value consumption at accessory.purchase_price * quantity (main-store
          unit cost).
        - Post:

            Dr 31222 Salon Supplies Expense
            Cr 3120x Accessory Inventory {Store}

        This should be called **once per ServiceSale** after payment, and will
        skip if no accessory consumption value > 0 can be computed.
        """
        from decimal import Decimal
        from production.models import AccessorySaleItem, StoreAccessoryInventory

        try:
            if getattr(service_sale, "paid_status", None) != "paid":
                return None

            store = getattr(service_sale, "store", None)
            if store is None:
                return None

            # 1) Collect accessory consumption lines for this sale.
            # We rely on AccessorySaleItem records; if your business logic
            # distinguishes billable vs internal-use accessories, you can
            # further filter here (e.g., price == 0 for internal use).
            accessory_items = AccessorySaleItem.objects.filter(sale=service_sale)
            if not accessory_items.exists():
                return None

            total_consumption_value = Decimal("0.00")

            for item in accessory_items.select_related("accessory__accessory"):
                sai = item.accessory  # StoreAccessoryInventory
                accessory = getattr(sai, "accessory", None)
                qty = item.quantity or Decimal("0.00")
                if not accessory or qty <= 0:
                    continue

                unit_cost = accessory.purchase_price or Decimal("0.00")
                if unit_cost <= 0:
                    continue

                total_consumption_value += unit_cost * qty

            if total_consumption_value <= 0:
                return None

            # 2) Resolve accounts
            # 31222 Salon Supplies Expense
            supplies_expense = ChartOfAccounts.objects.filter(account_code="31222").first()

            # Per-store accessory inventory account based on store name. We map
            # using a small helper so that real store names like
            #   "Kyanja", "Ntinda Store", "Livara Bugolobi Branch"
            # resolve to CoA accounts such as:
            #   31202 Accessory Inventory Kyanja
            #   31201 Accessory Inventory Ntinda
            #   31200 Accessory Inventory Bugolobi
            def get_store_accessory_account(store_obj):
                name = (store_obj.name or "").strip()
                # Normalise to a simple key
                key = name.lower()
                if "kyanja" in key:
                    target_name = "Accessory Inventory Kyanja"
                elif "ntinda" in key:
                    target_name = "Accessory Inventory Ntinda"
                elif "bugolobi" in key:
                    target_name = "Accessory Inventory Bugolobi"
                else:
                    # Fallback to generic pattern: "Accessory Inventory {store.name}"
                    target_name = f"Accessory Inventory {store_obj.name}"

                return ChartOfAccounts.objects.filter(
                    account_name=target_name,
                    account_type="asset",
                    account_category="current_asset",
                ).first()

            store_inventory_account = get_store_accessory_account(store)

            if not supplies_expense or not store_inventory_account:
                # If mapping is missing, better to skip than post incorrectly
                return None

            # 3) Create journal entry
            journal_entry = JournalEntry.objects.create(
                date=service_sale.sale_date.date() if hasattr(service_sale, "sale_date") else timezone.now().date(),
                reference=f"AccCons-{service_sale.id}",
                description=(
                    f"Accessory consumption for service sale {getattr(service_sale, 'service_sale_number', service_sale.id)} "
                    f"at {store.name}"
                ),
                entry_type="production",
                department=Department.objects.filter(code="PROD").first(),
                created_by=user,
                is_posted=True,
                posted_at=timezone.now(),
            )

            # DR 31222 Salon Supplies Expense
            JournalEntryLine.objects.create(
                journal_entry=journal_entry,
                account=supplies_expense,
                entry_type="debit",
                amount=total_consumption_value,
                description="Salon supplies expense - accessories consumed",
            )

            # CR 3120x Accessory Inventory {Store}
            JournalEntryLine.objects.create(
                journal_entry=journal_entry,
                account=store_inventory_account,
                entry_type="credit",
                amount=total_consumption_value,
                description=f"Accessories consumed for services at {store.name}",
            )

            return journal_entry

        except Exception as e:
            print(f"Error creating accessory consumption journal entry: {e}")
            return None
        
    def create_raw_material_writeoff_journal_entry(writeoff, user):
        """
        Create journal entry for an IncidentWriteOff (raw material loss).

        Valuation: latest RequisitionItem price for this raw material.
        Falls back to RawMaterialPrice if no requisition history exists.

        DR  50900  Raw Material Loss & Spoilage  (expense / COGS)
        CR  5100   Raw Materials Inventory        (asset)
        """
        from decimal import Decimal
        from production.models import RequisitionItem, RawMaterialPrice

        try:
            with transaction.atomic():

                # ── Guard: already posted? ────────────────────────────────
                if JournalEntry.objects.filter(reference=f"RM-WO-{writeoff.id}").exists():
                    print(f"RM-WO-{writeoff.id}: journal entry already exists, skipping.")
                    return JournalEntry.objects.get(reference=f"RM-WO-{writeoff.id}")

                raw_material = writeoff.raw_material

                # ── Resolve unit cost ─────────────────────────────────────
                unit_cost = Decimal('0.00')
                price_source = None

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
                    price_source = f"Requisition {latest_req_item.requisition.requisition_no}"
                else:
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
                        price_source = f"Market price ({latest_price.supplier.name})"

                if unit_cost <= 0:
                    print(
                        f"RM-WO-{writeoff.id}: no unit cost found for "
                        f"'{raw_material.name}' — skipping journal entry."
                    )
                    return None

                total_loss = Decimal(str(writeoff.quantity)) * unit_cost

                # ── Resolve accounts ──────────────────────────────────────
                loss_account = ChartOfAccounts.objects.filter(
                    account_code='50900'
                ).first()

                inventory_account = ChartOfAccounts.objects.filter(
                    account_code='5100'
                ).first()

                if not loss_account:
                    print("RM-WO: account 50900 (Raw Material Loss & Spoilage) not found.")
                    return None
                if not inventory_account:
                    print("RM-WO: account 5100 (Raw Materials Inventory) not found.")
                    return None

                # ── Create journal entry ──────────────────────────────────
                journal_entry = JournalEntry.objects.create(
                    date=writeoff.date,
                    reference=f"RM-WO-{writeoff.id}",
                    description=(
                        f"Raw material write-off: {raw_material.name} "
                        f"x {writeoff.quantity} ({price_source})"
                    ),
                    entry_type='production',
                    department=Department.objects.filter(code='PROD').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now(),
                )

                # DR 50900 Raw Material Loss & Spoilage
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=loss_account,
                    entry_type='debit',
                    amount=total_loss,
                    description=(
                        f"Loss: {writeoff.quantity} {raw_material.unit_measurement} "
                        f"of {raw_material.name} @ {unit_cost} each"
                    ),
                )

                # CR 5100 Raw Materials Inventory
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=inventory_account,
                    entry_type='credit',
                    amount=total_loss,
                    description=f"Inventory reduction: {raw_material.name} written off",
                )

                print(
                    f"Created RM write-off JE {journal_entry.entry_number} — "
                    f"{raw_material.name} x {writeoff.quantity} = {total_loss} "
                    f"(source: {price_source})"
                )
                return journal_entry

        except Exception as e:
            print(f"Error creating raw material write-off journal entry: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        
    @staticmethod
    def create_store_writeoff_journal_entry(writeoff, user):
        """
        Create journal entry for a StoreWriteOff (finished product shrinkage).
        Only fires when writeoff.approved is True.

        Valuation: LivaraMainStore.unit_cost * quantity written off.

        DR  5030   Store Shrinkage      (expense / COGS)
        CR  1210   Store Inventory      (asset)
        """
        from decimal import Decimal

        try:
            with transaction.atomic():

                # ── Guard: only post approved write-offs ──────────────────
                if not writeoff.approved:
                    print(f"StoreWO-{writeoff.id}: not approved yet, skipping.")
                    return None

                # ── Guard: already posted? ────────────────────────────────
                if JournalEntry.objects.filter(
                    reference=f"StoreWO-{writeoff.id}"
                ).exists():
                    print(f"StoreWO-{writeoff.id}: journal entry already exists, skipping.")
                    return JournalEntry.objects.get(reference=f"StoreWO-{writeoff.id}")

                # ── Resolve unit cost from LivaraMainStore ────────────────
                store_product = writeoff.main_store_product  # LivaraMainStore instance
                unit_cost = store_product.unit_cost or Decimal('0.00')

                if unit_cost <= 0:
                    # Fallback: try to get cost from ManufacturedProductInventory
                    mpi = store_product.product  # ManufacturedProductInventory
                    if mpi and mpi.unit_cost and mpi.unit_cost > 0:
                        unit_cost = mpi.unit_cost
                    else:
                        print(
                            f"StoreWO-{writeoff.id}: no unit cost found for "
                            f"batch {writeoff.batch_number} — skipping journal entry."
                        )
                        return None

                total_loss = unit_cost * Decimal(str(writeoff.quantity))

                if total_loss <= 0:
                    print(f"StoreWO-{writeoff.id}: total_loss is 0, skipping.")
                    return None

                # ── Resolve accounts ──────────────────────────────────────
                shrinkage_account = ChartOfAccounts.objects.filter(
                    account_code='5030'
                ).first()

                inventory_account = ChartOfAccounts.objects.filter(
                    account_code='1210'
                ).first()

                if not shrinkage_account:
                    print("StoreWO: account 5030 (Store Shrinkage) not found.")
                    return None
                if not inventory_account:
                    print("StoreWO: account 1210 (Store Inventory) not found.")
                    return None

                product_name = (
                    store_product.product.product.product_name
                    if store_product.product and store_product.product.product
                    else writeoff.batch_number
                )

                # ── Create journal entry ──────────────────────────────────
                journal_entry = JournalEntry.objects.create(
                    date=writeoff.approved_date.date() if writeoff.approved_date else timezone.now().date(),
                    reference=f"StoreWO-{writeoff.id}",
                    description=(
                        f"Store write-off: {product_name} "
                        f"x {writeoff.quantity} units — "
                        f"{writeoff.get_reason_display()}"
                    ),
                    entry_type='production',
                    department=Department.objects.filter(code='PROD').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now(),
                )

                # DR 5030 Store Shrinkage
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=shrinkage_account,
                    entry_type='debit',
                    amount=total_loss,
                    description=(
                        f"Shrinkage: {writeoff.quantity} units of {product_name} "
                        f"@ {unit_cost} each — {writeoff.get_reason_display()}"
                    ),
                )

                # CR 1210 Store Inventory
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=inventory_account,
                    entry_type='credit',
                    amount=total_loss,
                    description=(
                        f"Inventory reduction: {product_name} "
                        f"written off (batch {writeoff.batch_number})"
                    ),
                )

                print(
                    f"Created store write-off JE {journal_entry.entry_number} — "
                    f"{product_name} x {writeoff.quantity} = {total_loss}"
                )
                return journal_entry

        except Exception as e:
            print(f"Error creating store write-off journal entry: {e}")
            import traceback
            traceback.print_exc()
            return None


    @staticmethod
    def create_accessory_requisition_journal_entry(accessory_req, user):
        """Create journal entry when main-store accessory requisition is delivered.

        Mirrors the raw-material requisition JE, but posts into
        'Accessory Inventory - Main Store' instead of 'Raw Materials Inventory'.
        """
        try:
            with transaction.atomic():
                # Create journal entry
                journal_entry = JournalEntry.objects.create(
                    date=accessory_req.request_date.date(),
                    reference=f"AccReq-{accessory_req.accessory_req_number}",
                    description=f"Accessory requisition {accessory_req.accessory_req_number}",
                    entry_type='production',
                    department=Department.objects.filter(code='PROD').first(),  # Production dept
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now(),
                )

                # 1) Accessory Inventory - Main Store (Asset)
                # Prefer lookup by explicit account_code so it maps cleanly to
                # 31000 Accessory Inventory - Main Store in the CoA.
                accessory_inventory_account = ChartOfAccounts.objects.filter(
                    account_code='31000',
                ).first()

                # 2) Tax Receivable (Asset) for input VAT
                tax_receivable_account = ChartOfAccounts.objects.filter(
                    account_name='Tax Receivable',
                    account_type='asset',
                    account_category='tax_receivable',
                ).first()

                # 3) Accounts Payable (Liability)
                payable_account = ChartOfAccounts.objects.filter(
                    account_name='Accounts Payable',
                    account_type='liability',
                    account_category='current_liability',
                ).first()

                if not accessory_inventory_account or not payable_account:
                    print(
                        "Accessory requisition JE skipped: required accounts missing. "
                        "Ensure 'Accessory Inventory - Main Store' (asset/current_asset) and "
                        "'Accounts Payable' (liability/current_liability) exist."
                    )
                    return None

                # Compute totals from items: assume price_per_unit & tax_code on each item
                from decimal import Decimal

                items = accessory_req.items.all()
                subtotal_before_tax = Decimal('0.00')
                total_tax_amount = Decimal('0.00')  # MainStoreAccessoryRequisitionItem currently has no tax fields

                for item in items:
                    qty = item.quantity_requested or Decimal('0.00')
                    unit_price = item.price or Decimal('0.00')
                    line_subtotal = qty * unit_price
                    subtotal_before_tax += line_subtotal

                # For now, we assume accessory requisition prices are tax-exclusive
                # and that any VAT is handled separately at payment level, so
                # total_tax_amount remains 0. You can extend MainStoreAccessoryRequisitionItem
                # with tax_code if you later need per-line tax here.

                grand_total = subtotal_before_tax + total_tax_amount

                # Debit Accessory Inventory - Main Store (net of tax)
                if subtotal_before_tax > 0:
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=accessory_inventory_account,
                        entry_type='debit',
                        amount=subtotal_before_tax,
                        description=f"Accessories for requisition {accessory_req.accessory_req_number}",
                    )

                # Debit Tax Receivable if applicable
                if total_tax_amount > 0 and tax_receivable_account:
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=tax_receivable_account,
                        entry_type='debit',
                        amount=total_tax_amount,
                        description=f"Input VAT on accessories for requisition {accessory_req.accessory_req_number}",
                    )

                # Credit Accounts Payable with total including tax
                if grand_total > 0:
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=payable_account,
                        entry_type='credit',
                        amount=grand_total,
                        description=f"Payable for accessories {accessory_req.accessory_req_number}",
                    )

                return journal_entry

        except Exception as e:
            print(f"Error creating accessory requisition journal entry: {e}")
            return None

    @staticmethod
    def create_internal_accessory_transfer_journal_entry(accessory_request, user):
        """Create journal entry when accessories are transferred from main store to a salon store.

        DR Accessory Inventory - [Store]
        CR Accessory Inventory - Main Store

        Valued at accessory.purchase_price (unit cost) per line. Assumes a
        ChartOfAccounts row named 'Accessory Inventory - Main Store' and,
        for each store, 'Accessory Inventory {store.name}'.
        """
        from decimal import Decimal

        try:
            with transaction.atomic():
                store = accessory_request.store

                # Determine accounts
                # Main store accessories: 31000 Accessory Inventory - Main Store
                main_inventory_account = ChartOfAccounts.objects.filter(
                    account_code='31000',
                ).first()

                # Per-store accessory inventory accounts are expected to be
                # named "Accessory Inventory {store.name}", e.g.:
                #   Bugolobi → 31200 Accessory Inventory Bugolobi
                #   Ntinda  → 31201 Accessory Inventory Ntinda
                #   Kyanja  → 31202 Accessory Inventory Kyanja
                # and configured as asset/current_asset in the CoA.
                store_account_name = f"Accessory Inventory {store.name}"
                store_inventory_account = ChartOfAccounts.objects.filter(
                    account_name=store_account_name,
                    account_type='asset',
                    account_category='current_asset',
                ).first()

                if not main_inventory_account or not store_inventory_account:
                    print(
                        "Internal accessory transfer JE skipped: required inventory accounts missing. "
                        "Ensure 'Accessory Inventory - Main Store' and per-store accounts like "
                        f"'{store_account_name}' exist."
                    )
                    return None

                # Compute total transfer value from request items
                items = accessory_request.items.all()
                total_value = Decimal('0.00')

                for item in items:
                    accessory = item.accessory
                    qty = item.quantity_requested or Decimal('0.00')
                    unit_cost = accessory.purchase_price or Decimal('0.00')
                    if unit_cost <= 0 or qty <= 0:
                        continue
                    total_value += qty * unit_cost

                if total_value <= 0:
                    print(
                        f"Skipping internal accessory transfer JE for request {accessory_request.id}: "
                        f"total_value is {total_value}"
                    )
                    return None

                # Create journal entry
                journal_entry = JournalEntry.objects.create(
                    date=accessory_request.request_date,
                    reference=f"AccInt-{accessory_request.id}",
                    description=(
                        f"Internal accessory transfer to {store.name} "
                        f"(request {accessory_request.id})"
                    ),
                    entry_type='production',
                    department=Department.objects.filter(code='PROD').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now(),
                )

                # DR Accessory Inventory - [Store]
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=store_inventory_account,
                    entry_type='debit',
                    amount=total_value,
                    description=f"Accessories transferred to {store.name}",
                )

                # CR Accessory Inventory - Main Store
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=main_inventory_account,
                    entry_type='credit',
                    amount=total_value,
                    description="Accessories transferred from main store",
                )

                return journal_entry

        except Exception as e:
            print(f"Error creating internal accessory transfer journal entry: {e}")
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
                    account_code='1100'  # Accounts Receivable
                ).first()

                # Get revenue account (Store Sales Revenue - 4110)
                revenue_account = ChartOfAccounts.objects.filter(
                    account_code='4110',  # Sale Revenue for main store products
                    account_type='revenue',
                    account_category='operating_revenue',
                ).first()

                # Create 4110 automatically if missing (name matches your CoA)
                if not revenue_account:
                    revenue_account = ChartOfAccounts.objects.create(
                        account_code='4110',
                        account_name='Sale Revenue',
                        account_type='revenue',
                        account_category='operating_revenue',
                        is_active=True,
                    )

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
                
                # Get accounts payable account (prefer supplier-specific AP if configured)
                supplier = requisition.supplier
                payable_account = getattr(supplier, 'payables_account', None)
                if payable_account is None:
                    payable_account = ChartOfAccounts.objects.filter(
                        account_code='2000',  # Accounts Payable - Suppliers (control)
                        account_type='liability',
                        account_category='current_liability',
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

        IMPORTANT: This now relies **only** on the `total_production_cost` field
        that is calculated on the manufacturing cost sheet. We *do not* attempt
        to recompute cost from raw‑material usage, to avoid unit/price
        mismatches that previously produced wildly inflated values.

        Flow:
        - Read `manufacture_product.total_production_cost`.
        - If it is missing or not > 0, skip creating a JE.
        - DR 1210 (Finished Goods / Store Inventory) with total_production_cost.
        - CR 5100 (Raw Materials Inventory) with total_production_cost.
        - Link the JE to ManufacturedProductInventory via ManufacturingRecord
          when possible.
        """
        try:
            with transaction.atomic():
                from production.models import ManufacturedProductInventory

                # 1) Use only the explicit total_production_cost recorded on the batch
                total_cost = manufacture_product.total_production_cost or Decimal("0.00")

                # If total_cost is not set or zero/negative, do not create a JE
                if total_cost <= 0:
                    print(
                        "Skipping manufacturing JE for batch "
                        f"{manufacture_product.batch_number}: total_production_cost "
                        f"is {total_cost}. Ensure the manufacturing cost sheet "
                        "has been saved before posting to the ledger."
                    )
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
                    posted_at=timezone.now(),
                )

                # Get inventory account (Finished Goods) and raw materials account
                inventory_account = ChartOfAccounts.objects.filter(
                    account_code="1210"  # Finished Goods / Store Inventory
                ).first()

                raw_materials_account = ChartOfAccounts.objects.filter(
                    account_code="5100"  # Raw Materials
                ).first()

                if inventory_account and raw_materials_account:
                    # Debit Finished Goods Inventory
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=inventory_account,
                        entry_type="debit",
                        amount=total_cost,
                        description=(
                            "Finished goods inventory - "
                            f"{manufacture_product.product.product_name}"
                        ),
                    )

                    # Credit Raw Materials (transfer from raw materials to finished goods)
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=raw_materials_account,
                        entry_type="credit",
                        amount=total_cost,
                        description=(
                            f"Raw materials consumed for {manufacture_product.batch_number}"
                        ),
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
                            defaults={"amount": total_cost},
                        )
                        # Keep amount in sync if record already existed
                        if not created and mr.amount != total_cost:
                            mr.amount = total_cost
                            mr.save(update_fields=["amount"])
                    else:
                        # Create a placeholder record that will be linked to
                        # ManufacturedProductInventory when it is created.
                        mr, created = ManufacturingRecord.objects.get_or_create(
                            manufacture_product=None,
                            journal_entry=journal_entry,
                            defaults={"amount": total_cost},
                        )
                        if not created and mr.amount != total_cost:
                            mr.amount = total_cost
                            mr.save(update_fields=["amount"])

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
                
                # Get accounts payable account (prefer supplier-specific AP if configured)
                supplier = payment_voucher.lpo.requisition.supplier
                payable_account = getattr(supplier, 'payables_account', None)
                if payable_account is None:
                    payable_account = ChartOfAccounts.objects.filter(
                        account_code='2000',  # Accounts Payable - Suppliers (control)
                        account_type='liability',
                        account_category='current_liability',
                    ).first()
                
                # Get cash account
                payment_account = payment_voucher.payment_account
                
                # Validate payment account exists
                if not payment_account:
                    journal_entry.delete()
                    error_msg = (
                        f"Payment account not specified for voucher {payment_voucher.voucher_number}. "
                        f"Please ensure payment_account is set when creating PaymentVoucher."
                    )
                    print(error_msg)
                    return None
                
                # Validate payable account exists
                if not payable_account:
                    journal_entry.delete()
                    error_msg = (
                        f"Accounts Payable account not found for payment voucher {payment_voucher.voucher_number}. "
                        f"Supplier: {supplier.name}"
                    )
                    print(error_msg)
                    return None
                
                # Create journal entry lines
                # Debit: Supplier's Accounts Payable (reduces what we owe them)
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=payable_account,
                    entry_type='debit',
                    amount=payment_voucher.amount_paid,
                    description=f"Payment to {supplier.name} for LPO {payment_voucher.lpo.lpo_number}"
                )
                
                # Credit: The actual payment account used (Cash/Bank/Mobile Money)
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=payment_account,
                    entry_type='credit',
                    amount=payment_voucher.amount_paid,
                    description=f"Payment via {payment_account.account_name} for LPO {payment_voucher.lpo.lpo_number}"
                )
                
                return journal_entry
                    
        except Exception as e:
            print(f"Error creating payment journal entry: {e}")
            import traceback
            traceback.print_exc()
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
                
                # Get default parent revenue account (Store Service Revenue 4120)
                parent_revenue_account = ChartOfAccounts.objects.filter(
                    account_code='4120'  # Store Service Revenue (parent for service categories)
                ).first()
                
                if not parent_revenue_account:
                    # Create parent Store Service Revenue account if it doesn't exist
                    parent_revenue_account = ChartOfAccounts.objects.create(
                        account_code='4120',
                        account_name='Store Service Revenue',
                        account_type='revenue',
                        account_category='operating_revenue',
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
                
                if parent_revenue_account and ar_account:
                    from decimal import Decimal
                    from collections import defaultdict
                    from production.models import ServiceSaleItem

                    # --- Debit Accounts Receivable for full amount ---
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=ar_account,
                        entry_type='debit',
                        amount=service_sale.total_amount,
                        description=(
                            f"Service sale receivable from "
                            f"{service_sale.customer.first_name} {service_sale.customer.last_name}"
                        ),
                    )

                    # --- Build revenue by service category ---
                    revenue_by_account = defaultdict(Decimal)
                    services_total = Decimal('0.00')

                    service_items = service_sale.service_sale_items.select_related(
                        'service__service__service_category__revenue_account'
                    )

                    for item in service_items:
                        line_amount = item.total_price or Decimal('0.00')
                        if line_amount <= 0:
                            continue
                        services_total += line_amount

                        # Resolve category-specific account; fall back to parent 4120
                        category = getattr(item.service.service, 'service_category', None)
                        category_account = getattr(category, 'revenue_account', None) if category else None
                        account = category_account or parent_revenue_account
                        revenue_by_account[account] += line_amount

                    # Any remaining part of total_amount (e.g., products/refreshments on the ticket)
                    # is posted to the parent service revenue account so the JE balances.
                    remainder = (service_sale.total_amount or Decimal('0.00')) - services_total
                    if remainder > 0:
                        revenue_by_account[parent_revenue_account] += remainder

                    # --- Credit revenue per account ---
                    for account, amount in revenue_by_account.items():
                        if amount <= 0:
                            continue
                        JournalEntryLine.objects.create(
                            journal_entry=journal_entry,
                            account=account,
                            entry_type='credit',
                            amount=amount,
                            description=(
                                f"Service revenue ({account.account_code}) from "
                                f"{service_sale.service_sale_number}"
                            ),
                        )

                    # Create aggregated sales revenue record for this service sale
                    SalesRevenue.objects.create(
                        service_sale=service_sale,
                        journal_entry=journal_entry,
                        amount=service_sale.total_amount,
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

                # Determine the store (for per-store cash accounts)
                store = getattr(service_sale, 'store', None)

                # Get appropriate cash/bank account based on payment method
                if payment.payment_method == 'cash':
                    # Prefer the store's configured cash account if available
                    cash_account = getattr(store, 'cash_account', None) if store else None
                    if cash_account is None:
                        cash_account = ChartOfAccounts.objects.filter(
                            account_code='1000'  # Fallback global Cash on Hand
                        ).first()
                elif payment.payment_method in ['mobile_money', 'airtel_money']:
                    # Split MTN vs Airtel mobile money into separate accounts
                    if payment.payment_method == 'mobile_money':
                        target_code = '10100'   # MTN Mobile Money
                        target_name = 'MTN Mobile Money'
                    else:  # 'airtel_money'
                        target_code = '101001'  # Airtel Mobile Money
                        target_name = 'Airtel Mobile Money'

                    cash_account = ChartOfAccounts.objects.filter(
                        account_code=target_code
                    ).first()
                    if not cash_account:
                        cash_account = ChartOfAccounts.objects.create(
                            account_code=target_code,
                            account_name=target_name,
                            account_type='asset',
                            account_category='current_asset',
                            is_active=True,
                        )
                elif payment.payment_method in ['visa', 'bank_transfer']:
                    # Prefer the store's default bank account if configured
                    cash_account = getattr(store, 'bank_account', None) if store else None
                    if cash_account is None:
                        cash_account = ChartOfAccounts.objects.filter(
                            account_code='1020'  # Fallback global Bank Account
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
                    # Default to store cash account if available, otherwise global cash
                    cash_account = getattr(store, 'cash_account', None) if store else None
                    if cash_account is None:
                        cash_account = ChartOfAccounts.objects.filter(
                            account_code='1000'  # Fallback Cash on Hand
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

                # Identify the store from the receipt
                store = None
                if store_sale_payment.receipt and store_sale_payment.receipt.store_sale:
                    store = store_sale_payment.receipt.store_sale.store

                if store_sale_payment.payment_method == 'cash':
                    # Prefer the store-specific cash account if configured
                    cash_account = getattr(store, 'cash_account', None) if store else None
                    if cash_account is None:
                        cash_account = ChartOfAccounts.objects.filter(
                            account_code='1000',
                            account_type='asset',
                            account_category='current_asset',
                        ).first()
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
    def _get_staff_payable_account(staff):
        """
        Resolve the per-staff commission payable account.
        Falls back to auto-creating it if the signal hasn't run yet.
        """
        from POSMagicApp.signals import _ensure_staff_commission_account
        
        account_code = f"2110-{staff.pk:04d}"
        account = ChartOfAccounts.objects.filter(account_code=account_code).first()
        
        if not account:
            # Auto-heal: signal may not have run for older staff
            account = _ensure_staff_commission_account(staff)
        
        return account
    
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
                
                # Get commission payable account must be staff specific
                payable_account = AccountingService._get_staff_payable_account(
                    staff=staff_commission.staff
                )
                
                if not expense_account or not payable_account:
                    print("Commission accounts not found.")
                    return None

                # Dr. Service Commission Expense (6015)
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=expense_account,
                    entry_type='debit',
                    amount=staff_commission.commission_amount,
                    description=f"Service commission expense for {staff_commission.staff.first_name}"
                )

                # Cr. Commissions Payable - [Staff Name]  (2110-XXXX)
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=payable_account,
                    entry_type='credit',
                    amount=staff_commission.commission_amount,
                    description=f"Commission payable to {staff_commission.staff.first_name}"
                )

                CommissionExpense.objects.create(
                    staff_commission=staff_commission,
                    journal_entry=journal_entry,
                    amount=staff_commission.commission_amount,
                    commission_type='service',
                    staff=staff_commission.staff  # populate new FK
                )
                    
                print(f"Created service commission journal entry: {journal_entry.entry_number}")
                return journal_entry
                    
        except Exception as e:
            print(f"Error creating service commission journal entry: {e}")
            return None
        
    @staticmethod
    def create_product_commission_journal_entry(product_commission, user):
        """Create journal entry when product commission is earned"""
        try:
            with transaction.atomic():
                # Guard: already posted?
                if CommissionExpense.objects.filter(product_commission=product_commission).exists():
                    return CommissionExpense.objects.get(
                        product_commission=product_commission
                    ).journal_entry

                journal_entry = JournalEntry.objects.create(
                    date=product_commission.created_at.date(),
                    reference=f"ProductCommission-{product_commission.id}",
                    description=(
                        f"Product commission for {product_commission.staff.first_name} "
                        f"- {product_commission.product_sale_item.product.product.product_name}"
                    ),
                    entry_type='system',
                    department=Department.objects.filter(code='SALES').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now()
                )

                expense_account = ChartOfAccounts.objects.filter(
                    account_code='6016'
                ).first()
                
                # ← THE FIX: per-staff account
                payable_account = AccountingService._get_staff_payable_account(
                    product_commission.staff
                )

                if not expense_account or not payable_account:
                    print("Commission accounts not found.")
                    return None

                # Dr. Product Commission Expense (6016)
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=expense_account,
                    entry_type='debit',
                    amount=product_commission.commission_amount,
                    description=f"Product commission expense for {product_commission.staff.first_name}"
                )

                # Cr. Commissions Payable - [Staff Name]  (2110-XXXX)
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=payable_account,
                    entry_type='credit',
                    amount=product_commission.commission_amount,
                    description=f"Commission payable to {product_commission.staff.first_name}"
                )

                CommissionExpense.objects.create(
                    product_commission=product_commission,
                    journal_entry=journal_entry,
                    amount=product_commission.commission_amount,
                    commission_type='product',
                    staff=product_commission.staff  # populate new FK
                )

                return journal_entry

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
        
    @staticmethod
    def _get_store_cash_account(store, payment_method):
        """
        Resolve the correct cash/bank ChartOfAccounts entry for a given
        store and payment method.

        Cash account codes per store (no FK on Store model, resolved by name):
            Mutaasa Kafeero  →  3004
            Bugolobi         →  3001  (adjust to your actual codes)
            Ntinda           →  3002
            Kyanja           →  3003

        Mobile money and card accounts are shared across stores.
        """
        store_name = (store.name or '').strip().lower()
        if payment_method == 'cash':
            # Per-store cash at hand accounts
            STORE_CASH_CODES = {
                'mutaasa': '3004',
                'bugolobi': '3001',   # adjust to your real codes
                'ntinda':   '3002',
                'kyanja':   '3003',
            }
            # Match by substring so "Mutaasa Kafeero" still hits 'mutaasa'
            matched_code = None
            for key, code in STORE_CASH_CODES.items():
                if key in store_name:
                    matched_code = code
                    break

            if matched_code:
                account = ChartOfAccounts.objects.filter(
                    account_code=matched_code
                ).first()
                if account:
                    return account

            # Fallback: generic cash on hand
            return ChartOfAccounts.objects.filter(account_code='1000').first()

        elif payment_method == 'mobile_money':
            return ChartOfAccounts.objects.filter(account_code='10100').first()

        elif payment_method == 'airtel_money':
            return ChartOfAccounts.objects.filter(account_code='101001').first()

        elif payment_method in ['visa', 'bank_transfer']:
            return ChartOfAccounts.objects.filter(account_code='1020').first()

        elif payment_method == 'mixed':
            # Mixed payments: use store cash as the primary account.
            # The split detail lives in the CashDrawerTransaction records —
            # we post the full amount to cash here for simplicity.
            return AccountingService._get_store_cash_account(store, 'cash')

        # Default
        return ChartOfAccounts.objects.filter(account_code='1000').first()


    @staticmethod
    def _get_store_product_revenue_account(store):
        """
        Resolve the correct Product Sales revenue account for a store.

        4100 is the Product Sales account you specified.
        If you later split by store, extend this map exactly like the cash one.
        """
        # Currently one shared Product Sales account across stores.
        # To split per-store, add a map here keyed on store name substring.
        return ChartOfAccounts.objects.filter(account_code='4100').first()


    @staticmethod
    def create_product_sale_journal_entry(product_sale, user):
        """
        Create double-entry journal for a StoreProductSale once it is paid.

        Entry:
            DR  Cash/Mobile Money/Bank  (store-specific cash account, e.g. 3004)
            CR  4100 Product Sales      (revenue)

        Guard: skips silently if a journal entry already exists for this sale
        so the signal is safe to fire more than once.
        """
        try:
            with transaction.atomic():
                # ── Guard: already posted? ────────────────────────────────────
                already_exists = JournalEntry.objects.filter(
                    reference=f"ProductSale-{product_sale.id}"
                ).exists()

                if already_exists:
                    print(
                        f"Journal entry already exists for ProductSale "
                        f"{product_sale.id} — skipping."
                    )
                    return JournalEntry.objects.filter(
                        reference=f"ProductSale-{product_sale.id}"
                    ).first()

                # ── Resolve accounts ──────────────────────────────────────────
                store = product_sale.store

                cash_account = AccountingService._get_store_cash_account(
                    store, product_sale.payment_mode
                )
                revenue_account = AccountingService._get_store_product_revenue_account(store)

                if not cash_account:
                    print(
                        f"ProductSale {product_sale.id}: cash account not found "
                        f"for store '{store.name}' / method '{product_sale.payment_mode}'. "
                        f"Skipping journal entry."
                    )
                    return None

                if not revenue_account:
                    print(
                        f"ProductSale {product_sale.id}: revenue account 4100 not found. "
                        f"Skipping journal entry."
                    )
                    return None

                # ── Create journal entry ──────────────────────────────────────
                journal_entry = JournalEntry.objects.create(
                    date=product_sale.sale_date.date(),
                    reference=f"ProductSale-{product_sale.id}",
                    description=(
                        f"Product sale {product_sale.product_sale_number} — "
                        f"{product_sale.customer.first_name} {product_sale.customer.last_name} "
                        f"at {store.name}"
                    ),
                    entry_type='sales',
                    department=Department.objects.filter(code='STORE').first(),
                    created_by=user,
                    is_posted=True,
                    posted_at=timezone.now(),
                )

                # DR Cash / Mobile Money / Bank
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=cash_account,
                    entry_type='debit',
                    amount=product_sale.total_amount,
                    description=(
                        f"Cash received via {product_sale.payment_mode} — "
                        f"{product_sale.product_sale_number}"
                    ),
                )

                # CR 4100 Product Sales Revenue
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=revenue_account,
                    entry_type='credit',
                    amount=product_sale.total_amount,
                    description=(
                        f"Product sales revenue — {product_sale.product_sale_number} "
                        f"at {store.name}"
                    ),
                )

                # Link to SalesRevenue for reporting consistency
                # StoreProductSale has no FK on SalesRevenue yet — we store
                # the reference in the journal entry itself which is enough
                # for the ledger. Add a FK to SalesRevenue if you need it
                # to appear in get_related_records().

                print(
                    f"Created product sale journal entry "
                    f"{journal_entry.entry_number} for "
                    f"{product_sale.product_sale_number} at {store.name} — "
                    f"DR {cash_account.account_code} / CR {revenue_account.account_code}"
                )
                return journal_entry

        except Exception as e:
            print(f"Error creating product sale journal entry: {e}")
            import traceback
            traceback.print_exc()
            return None
    # Balance sheet services
    @staticmethod
    def generate_balance_sheet(as_of_date, save_snapshot=False, user=None):
        """
        Generate a live balance sheet as of a given date by reading
        JournalEntryLine balances from ChartOfAccounts.

        Sub-accounts (e.g. 2110-0001) are included in their category totals
        but the parent (2110) is excluded to avoid double-counting when
        sub-accounts exist.

        Returns a dict with all sections and line items, plus optionally
        saves a BalanceSheet snapshot.
        """
        from decimal import Decimal
        from django.db.models import Sum, Q
        from accounts.models import (
            ChartOfAccounts, JournalEntryLine, BalanceSheet
        )

        def get_balance(account, as_of_date):
            """Get account balance up to and including as_of_date."""
            lines = JournalEntryLine.objects.filter(
                account=account,
                journal_entry__date__lte=as_of_date,
                journal_entry__is_posted=True,
            )
            debits = lines.filter(entry_type='debit').aggregate(
                t=Sum('amount')
            )['t'] or Decimal('0.00')
            credits = lines.filter(entry_type='credit').aggregate(
                t=Sum('amount')
            )['t'] or Decimal('0.00')

            if account.account_type in ['asset', 'expense']:
                return debits - credits
            return credits - debits

        def get_accounts(account_type, account_category):
            """
            Get active accounts for a type/category.
            Excludes parent accounts that have active sub-accounts
            to prevent double-counting.
            """
            accounts = ChartOfAccounts.objects.filter(
                account_type=account_type,
                account_category=account_category,
                is_active=True,
            ).order_by('account_code')

            result = []
            for acc in accounts:
                # Skip parent if it has active sub-accounts
                has_children = acc.sub_accounts.filter(is_active=True).exists()
                if has_children:
                    continue
                balance = get_balance(acc, as_of_date)
                if balance != Decimal('0.00'):
                    result.append({
                        'code': acc.account_code,
                        'name': acc.account_name,
                        'balance': balance,
                    })
            return result

        # ── ASSETS ───────────────────────────────────────────────────────────
        current_asset_categories = ['current_asset', 'tax_receivable']
        current_asset_lines = []
        for cat in current_asset_categories:
            current_asset_lines.extend(get_accounts('asset', cat))
        current_asset_lines.sort(key=lambda x: x['code'])

        fixed_asset_lines = get_accounts('asset', 'fixed_asset')

        total_current_assets = sum(a['balance'] for a in current_asset_lines)
        total_fixed_assets = sum(a['balance'] for a in fixed_asset_lines)
        total_assets = total_current_assets + total_fixed_assets

        # ── LIABILITIES ───────────────────────────────────────────────────────
        current_liability_lines = get_accounts('liability', 'current_liability')
        # Include tax payable under current liabilities
        tax_liability_lines = []
        for cat in ['tax_payable']:
            tax_liability_lines.extend(get_accounts('liability', cat))
        current_liability_lines = sorted(
            current_liability_lines + tax_liability_lines,
            key=lambda x: x['code']
        )

        long_term_liability_lines = get_accounts('liability', 'long_term_liability')

        total_current_liabilities = sum(a['balance'] for a in current_liability_lines)
        total_long_term_liabilities = sum(a['balance'] for a in long_term_liability_lines)
        total_liabilities = total_current_liabilities + total_long_term_liabilities

        # ── EQUITY ────────────────────────────────────────────────────────────
        owner_equity_lines = get_accounts('equity', 'owner_equity')
        retained_earnings_lines = get_accounts('equity', 'retained_earnings')
        equity_lines = owner_equity_lines + retained_earnings_lines

        total_owner_equity = sum(a['balance'] for a in owner_equity_lines)
        total_retained_earnings = sum(a['balance'] for a in retained_earnings_lines)
        total_equity = total_owner_equity + total_retained_earnings

        total_liabilities_and_equity = total_liabilities + total_equity
        is_balanced = abs(total_assets - total_liabilities_and_equity) < Decimal('0.01')

        data = {
            'as_of_date': as_of_date,
            'is_balanced': is_balanced,
            'difference': total_assets - total_liabilities_and_equity,

            # Assets
            'current_asset_lines': current_asset_lines,
            'fixed_asset_lines': fixed_asset_lines,
            'total_current_assets': total_current_assets,
            'total_fixed_assets': total_fixed_assets,
            'total_assets': total_assets,

            # Liabilities
            'current_liability_lines': current_liability_lines,
            'long_term_liability_lines': long_term_liability_lines,
            'total_current_liabilities': total_current_liabilities,
            'total_long_term_liabilities': total_long_term_liabilities,
            'total_liabilities': total_liabilities,

            # Equity
            'owner_equity_lines': owner_equity_lines,
            'retained_earnings_lines': retained_earnings_lines,
            'total_owner_equity': total_owner_equity,
            'total_retained_earnings': total_retained_earnings,
            'total_equity': total_equity,

            'total_liabilities_and_equity': total_liabilities_and_equity,
        }

        # ── Optional snapshot save ────────────────────────────────────────────
        if save_snapshot:
            snapshot, _ = BalanceSheet.objects.update_or_create(
                as_of_date=as_of_date,
                defaults={
                    'current_assets': total_current_assets,
                    'fixed_assets': total_fixed_assets,
                    'total_assets': total_assets,
                    'current_liabilities': total_current_liabilities,
                    'long_term_liabilities': total_long_term_liabilities,
                    'total_liabilities': total_liabilities,
                    'owner_equity': total_owner_equity,
                    'retained_earnings': total_retained_earnings,
                    'total_equity': total_equity,
                }
            )
            data['snapshot'] = snapshot

        return data

    #cashflow statement service 
    @staticmethod
    def generate_cash_flow_statement(start_date, end_date):
        """
        Generate a direct-method Cash Flow Statement for a given date range.

        Sections:
          A) Operating Activities
             Inflows  — all revenue accounts (credit balances in period)
             Outflows — all expense accounts (debit balances in period)

          B) Investing Activities
             Fixed asset purchases (debit movements on fixed_asset accounts)
             Fixed asset disposals (credit movements on fixed_asset accounts)

          C) Financing Activities
             Owner Capital contributions (credit movements on 3000)
             Owner Drawings (debit movements on 3100)
             Loan proceeds (credit movements on 2500)
             Loan repayments (debit movements on 2500)

          D) Opening & Closing Cash
             All cash/bank accounts (1000, 1010, 10100, 101001, 1020,
             3001–3004, 4005)
        """
        from decimal import Decimal
        from django.db.models import Sum

        CASH_ACCOUNT_CODES = [
            '1000', '1010', '10100', '101001', '1020',
            '3001', '3002', '3003', '3004', '4005',
        ]

        # Codes to exclude from operating inflows (contra-revenue)
        CONTRA_REVENUE_CODES = ['844555']

        def period_debit(account):
            """Net debit movement on an account within the period."""
            lines = JournalEntryLine.objects.filter(
                account=account,
                journal_entry__date__gte=start_date,
                journal_entry__date__lte=end_date,
                journal_entry__is_posted=True,
            )
            debits = lines.filter(entry_type='debit').aggregate(
                t=Sum('amount'))['t'] or Decimal('0.00')
            credits = lines.filter(entry_type='credit').aggregate(
                t=Sum('amount'))['t'] or Decimal('0.00')
            return debits - credits

        def period_credit(account):
            """Net credit movement on an account within the period."""
            return -period_debit(account)

        def balance_at(account, as_of_date):
            """Full balance on an account up to and including as_of_date."""
            lines = JournalEntryLine.objects.filter(
                account=account,
                journal_entry__date__lte=as_of_date,
                journal_entry__is_posted=True,
            )
            debits = lines.filter(entry_type='debit').aggregate(
                t=Sum('amount'))['t'] or Decimal('0.00')
            credits = lines.filter(entry_type='credit').aggregate(
                t=Sum('amount'))['t'] or Decimal('0.00')
            if account.account_type in ['asset', 'expense']:
                return debits - credits
            return credits - debits

        # ── A. OPERATING ACTIVITIES ───────────────────────────────────────────

        # Inflows: revenue accounts (credit side = cash received)
        revenue_accounts = ChartOfAccounts.objects.filter(
            account_type='revenue',
            is_active=True,
        ).exclude(
            account_code__in=CONTRA_REVENUE_CODES
        ).order_by('account_code')

        operating_inflow_lines = []
        for acc in revenue_accounts:
            amount = period_credit(acc)
            if amount > 0:
                operating_inflow_lines.append({
                    'code': acc.account_code,
                    'name': acc.account_name,
                    'amount': amount,
                })

        # Sales returns reduce inflows
        sales_returns_acc = ChartOfAccounts.objects.filter(
            account_code='844555'
        ).first()
        sales_returns_amount = Decimal('0.00')
        if sales_returns_acc:
            sales_returns_amount = period_debit(sales_returns_acc)
            if sales_returns_amount > 0:
                operating_inflow_lines.append({
                    'code': '844555',
                    'name': 'Less: Sales Returns',
                    'amount': -sales_returns_amount,
                })

        total_operating_inflows = sum(
            l['amount'] for l in operating_inflow_lines
        )

        # Outflows: expense accounts (debit side = cash paid out)
        expense_accounts = ChartOfAccounts.objects.filter(
            account_type='expense',
            is_active=True,
        ).order_by('account_code')

        operating_outflow_lines = []
        for acc in expense_accounts:
            amount = period_debit(acc)
            if amount > 0:
                operating_outflow_lines.append({
                    'code': acc.account_code,
                    'name': acc.account_name,
                    'amount': amount,
                })

        total_operating_outflows = sum(
            l['amount'] for l in operating_outflow_lines
        )
        net_operating = total_operating_inflows - total_operating_outflows

        # ── B. INVESTING ACTIVITIES ───────────────────────────────────────────
        fixed_asset_accounts = ChartOfAccounts.objects.filter(
            account_type='asset',
            account_category='fixed_asset',
            is_active=True,
        ).order_by('account_code')

        investing_inflow_lines = []   # disposals / sales of assets
        investing_outflow_lines = []  # purchases of assets

        for acc in fixed_asset_accounts:
            net = period_debit(acc)  # positive = purchased, negative = disposed
            if net > 0:
                investing_outflow_lines.append({
                    'code': acc.account_code,
                    'name': f"Purchase of {acc.account_name}",
                    'amount': net,
                })
            elif net < 0:
                investing_inflow_lines.append({
                    'code': acc.account_code,
                    'name': f"Proceeds from {acc.account_name}",
                    'amount': abs(net),
                })

        total_investing_inflows = sum(
            l['amount'] for l in investing_inflow_lines
        )
        total_investing_outflows = sum(
            l['amount'] for l in investing_outflow_lines
        )
        net_investing = total_investing_inflows - total_investing_outflows

        # ── C. FINANCING ACTIVITIES ───────────────────────────────────────────
        financing_inflow_lines = []
        financing_outflow_lines = []

        # Owner Capital — credit movement = new capital introduced
        owner_capital = ChartOfAccounts.objects.filter(
            account_code='3000'
        ).first()
        if owner_capital:
            amount = period_credit(owner_capital)
            if amount > 0:
                financing_inflow_lines.append({
                    'code': '3000',
                    'name': 'Owner Capital Introduced',
                    'amount': amount,
                })

        # Owner Drawings — debit movement = cash withdrawn
        owner_drawings = ChartOfAccounts.objects.filter(
            account_code='3100'
        ).first()
        if owner_drawings:
            amount = period_debit(owner_drawings)
            if amount > 0:
                financing_outflow_lines.append({
                    'code': '3100',
                    'name': 'Owner Drawings',
                    'amount': amount,
                })

        # Long-term Loans — credit = borrowed, debit = repaid
        loans = ChartOfAccounts.objects.filter(
            account_code='2500'
        ).first()
        if loans:
            net = period_credit(loans)  # positive = net borrowing
            if net > 0:
                financing_inflow_lines.append({
                    'code': '2500',
                    'name': 'Loan Proceeds',
                    'amount': net,
                })
            elif net < 0:
                financing_outflow_lines.append({
                    'code': '2500',
                    'name': 'Loan Repayments',
                    'amount': abs(net),
                })

        total_financing_inflows = sum(
            l['amount'] for l in financing_inflow_lines
        )
        total_financing_outflows = sum(
            l['amount'] for l in financing_outflow_lines
        )
        net_financing = total_financing_inflows - total_financing_outflows

        # ── D. OPENING & CLOSING CASH ─────────────────────────────────────────
        cash_accounts = ChartOfAccounts.objects.filter(
            account_code__in=CASH_ACCOUNT_CODES,
            is_active=True,
        ).order_by('account_code')

        # Opening cash: balance the day before start_date
        from datetime import timedelta
        day_before = start_date - timedelta(days=1)

        opening_cash_lines = []
        closing_cash_lines = []

        for acc in cash_accounts:
            opening_bal = balance_at(acc, day_before)
            closing_bal = balance_at(acc, end_date)
            if opening_bal != Decimal('0.00'):
                opening_cash_lines.append({
                    'code': acc.account_code,
                    'name': acc.account_name,
                    'amount': opening_bal,
                })
            if closing_bal != Decimal('0.00'):
                closing_cash_lines.append({
                    'code': acc.account_code,
                    'name': acc.account_name,
                    'amount': closing_bal,
                })

        opening_cash = sum(l['amount'] for l in opening_cash_lines)
        closing_cash = sum(l['amount'] for l in closing_cash_lines)

        # Net change should reconcile
        net_change = net_operating + net_investing + net_financing
        reconciled = abs((opening_cash + net_change) - closing_cash) < Decimal('0.01')

        return {
            'start_date': start_date,
            'end_date': end_date,

            # Operating
            'operating_inflow_lines': operating_inflow_lines,
            'operating_outflow_lines': operating_outflow_lines,
            'total_operating_inflows': total_operating_inflows,
            'total_operating_outflows': total_operating_outflows,
            'net_operating': net_operating,

            # Investing
            'investing_inflow_lines': investing_inflow_lines,
            'investing_outflow_lines': investing_outflow_lines,
            'total_investing_inflows': total_investing_inflows,
            'total_investing_outflows': total_investing_outflows,
            'net_investing': net_investing,

            # Financing
            'financing_inflow_lines': financing_inflow_lines,
            'financing_outflow_lines': financing_outflow_lines,
            'total_financing_inflows': total_financing_inflows,
            'total_financing_outflows': total_financing_outflows,
            'net_financing': net_financing,

            # Cash positions
            'opening_cash_lines': opening_cash_lines,
            'closing_cash_lines': closing_cash_lines,
            'opening_cash': opening_cash,
            'closing_cash': closing_cash,
            'net_change': net_change,
            'reconciled': reconciled,
        }
