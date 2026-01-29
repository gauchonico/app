import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from accounts.services import AccountingService
from accounts.models import JournalEntry, ProductionExpense, SalesRevenue, StoreTransfer as StoreTransferLink, ManufacturingRecord, PaymentRecord
from production.models import (
    StoreSale,
    Requisition,
    StoreTransfer,
    ManufactureProduct,
    PaymentVoucher,
    ServiceSale,
    ManufacturedProductInventory,
    IncidentWriteOff,
    MainStoreAccessoryRequisition,
    InternalAccessoryRequest,
)

# Set up logging
logger = logging.getLogger(__name__)

def get_admin_user():
    """Get admin user with fallback"""
    try:
        return User.objects.filter(is_superuser=True).first()
    except Exception as e:
        logger.error(f"Error getting admin user: {str(e)}")
        return None

def check_existing_entry(instance, entry_type):
    """Check if accounting entry already exists to prevent duplicates"""
    try:
        if isinstance(instance, StoreSale):
            return SalesRevenue.objects.filter(store_sale=instance).exists()
        elif isinstance(instance, Requisition):
            return ProductionExpense.objects.filter(requisition=instance).exists()
        elif isinstance(instance, ManufactureProduct):
            # Manufacturing is keyed off the MFG-{batch_number} journal reference
            return JournalEntry.objects.filter(reference=f"MFG-{instance.batch_number}").exists()
        elif isinstance(instance, StoreTransfer):
            return StoreTransferLink.objects.filter(transfer=instance).exists()
        elif isinstance(instance, PaymentVoucher):
            return PaymentRecord.objects.filter(payment_voucher=instance).exists()
        elif isinstance(instance, ServiceSale):
            return SalesRevenue.objects.filter(service_sale=instance).exists()
        return False
    except Exception as e:
        logger.error(f"Error checking existing entry: {str(e)}")
        return False

@receiver(post_save, sender=StoreSale)
def create_sales_journal_entry_auto(sender, instance, created, **kwargs):
    """Automatically create journal entry when a store sale is invoiced.

    We wait until the sale is fully priced (status='invoiced') so that
    subtotal, VAT, and withholding tax are final before posting to the
    ledger.
    """
    try:
        # Only create when the sale is invoiced and has a non-zero total
        if instance.status == 'invoiced' and instance.total_amount and instance.total_amount > 0:
            # Check for existing entry to prevent duplicates
            if check_existing_entry(instance, 'sales'):
                logger.info(f"Sales journal entry already exists for sale ID: {instance.id}")
                return
            
            admin_user = get_admin_user()
            if admin_user:
                with transaction.atomic():
                    AccountingService.create_sales_journal_entry(instance, admin_user)
                    logger.info(f"Sales journal entry created for sale ID: {instance.id}")
            else:
                logger.error(f"No admin user found for sale ID: {instance.id}")
    except Exception as e:
        logger.error(f"Error creating sales journal entry for sale ID {instance.id}: {str(e)}")
        # Don't raise the exception to prevent blocking the sale creation

@receiver(post_save, sender=Requisition)
def create_requisition_journal_entry_auto(sender, instance, created, **kwargs):
    """Automatically create journal entry when a requisition is approved"""
    try:
        if instance.status in ['approved', 'checking', 'delivered'] and instance.total_cost and instance.total_cost > 0:
            # Check for existing entry to prevent duplicates
            if check_existing_entry(instance, 'requisition'):
                logger.info(f"Requisition journal entry already exists for requisition ID: {instance.id}")
                return
            
            admin_user = get_admin_user()
            if admin_user:
                with transaction.atomic():
                    AccountingService.create_requisition_expense_journal_entry(instance, admin_user)
                    logger.info(f"Requisition journal entry created for requisition ID: {instance.id}")
            else:
                logger.error(f"No admin user found for requisition ID: {instance.id}")
    except Exception as e:
        logger.error(f"Error creating requisition journal entry for requisition ID {instance.id}: {str(e)}")

@receiver(post_save, sender=MainStoreAccessoryRequisition)
def create_accessory_requisition_journal_entry_auto(sender, instance, **kwargs):
    """Automatically create JE when a main-store accessory requisition is delivered.

    Uses AccountingService.create_accessory_requisition_journal_entry to
    debit Accessory Inventory - Main Store and credit Accounts Payable.
    """
    try:
        # Only when delivered; ignore pending/approved/rejected
        if instance.status != 'delivered':
            return

        # Prevent duplicates based on reference
        ref = f"AccReq-{instance.accessory_req_number}"
        if JournalEntry.objects.filter(reference=ref).exists():
            logger.info(
                f"Accessory requisition journal entry already exists for req ID: {instance.id}"
            )
            return

        admin_user = get_admin_user()
        if admin_user:
            with transaction.atomic():
                je = AccountingService.create_accessory_requisition_journal_entry(instance, admin_user)
                if je:
                    logger.info(
                        f"Accessory requisition journal entry created for req ID: {instance.id} "
                        f"- Entry: {je.entry_number or je.id}"
                    )
                else:
                    logger.error(
                        f"Failed to create accessory requisition journal entry for req ID: {instance.id}"
                    )
        else:
            logger.error(
                f"No admin user found for accessory requisition ID: {instance.id}"
            )
    except Exception as e:
        logger.error(
            f"Error creating accessory requisition journal entry for req ID {instance.id}: {str(e)}"
        )


@receiver(post_save, sender=ManufactureProduct)
def create_manufacturing_journal_entry_auto(sender, instance, created, **kwargs):
    """Automatically create journal entry when a product is manufactured"""
    try:
        if created:
            # Check for existing entry to prevent duplicates
            if check_existing_entry(instance, 'manufacturing'):
                logger.info(f"Manufacturing journal entry already exists for product ID: {instance.id}")
                return
            
            admin_user = get_admin_user()
            if admin_user:
                with transaction.atomic():
                    AccountingService.create_manufacturing_journal_entry(instance, admin_user)
                    logger.info(f"Manufacturing journal entry created for product ID: {instance.id}")
            else:
                logger.error(f"No admin user found for product ID: {instance.id}")
    except Exception as e:
        logger.error(f"Error creating manufacturing journal entry for product ID {instance.id}: {str(e)}")

@receiver(post_save, sender=StoreTransfer)
def create_store_transfer_journal_entry_auto(sender, instance, created, **kwargs):
    """Automatically create journal entry when a store transfer is completed"""
    try:
        if instance.status == 'Completed':
            # Check for existing entry to prevent duplicates
            if check_existing_entry(instance, 'store_transfer'):
                logger.info(f"Store transfer journal entry already exists for transfer ID: {instance.id}")
                return
            
            admin_user = get_admin_user()
            if admin_user:
                with transaction.atomic():
                    AccountingService.create_store_transfer_journal_entry(instance, admin_user)
                    logger.info(f"Store transfer journal entry created for transfer ID: {instance.id}")
            else:
                logger.error(f"No admin user found for transfer ID: {instance.id}")
    except Exception as e:
        logger.error(f"Error creating store transfer journal entry for transfer ID {instance.id}: {str(e)}")

@receiver(post_save, sender=PaymentVoucher)
def create_payment_journal_entry_auto(sender, instance, created, **kwargs):
    """Automatically create journal entry when a payment voucher is created"""
    try:
        if created:
            # Check for existing entry to prevent duplicates
            if check_existing_entry(instance, 'payment'):
                logger.info(f"Payment journal entry already exists for voucher ID: {instance.id}")
                return
            
            admin_user = get_admin_user()
            if admin_user:
                with transaction.atomic():
                    # Add a small delay to avoid race conditions with entry number generation
                    import time
                    time.sleep(0.1)
                    
                    journal_entry = AccountingService.create_payment_journal_entry(instance, admin_user)
                    if journal_entry:
                        logger.info(f"Payment journal entry created for voucher ID: {instance.id} - Entry: {journal_entry.entry_number}")
                    else:
                        logger.error(f"Failed to create payment journal entry for voucher ID: {instance.id}")
            else:
                logger.error(f"No admin user found for voucher ID: {instance.id}")
    except Exception as e:
        logger.error(f"Error creating payment journal entry for voucher ID {instance.id}: {str(e)}")
        # Log the full traceback for debugging
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

@receiver(post_save, sender=ServiceSale)
def create_service_sale_journal_entry_auto(sender, instance, **kwargs):
    """Automatically create journal entries for service sales.

    - When invoice_status == 'invoiced', create the revenue/AR JE.
    - When the sale becomes fully paid (paid_status == 'paid'), create
      accessory consumption JEs (DR 31222 / CR 3120x) for any associated
      AccessorySaleItem rows.
    """
    try:
        # Step 1: create revenue / AR entry when invoiced
        if instance.invoice_status == 'invoiced' and instance.total_amount and instance.total_amount > 0:
            # Check for existing entry to prevent duplicates
            if check_existing_entry(instance, 'service_sale'):
                logger.info(f"Service sale journal entry already exists for sale ID: {instance.id}")
                return
            
            admin_user = get_admin_user()
            if admin_user:
                with transaction.atomic():
                    # Add a small delay to avoid race conditions with entry number generation
                    import time
                    time.sleep(0.1)

                    journal_entry = AccountingService.create_service_sale_journal_entry(instance, admin_user)
                    if journal_entry:
                        logger.info(
                            f"Service sale journal entry created for sale ID: {instance.id} - "
                            f"Entry: {journal_entry.entry_number}"
                        )
                    else:
                        logger.error(
                            f"Failed to create service sale journal entry for sale ID: {instance.id}"
                        )
            else:
                logger.error(f"No admin user found for service sale ID: {instance.id}")

        # Step 2: when sale is fully paid, record accessory consumption
        if getattr(instance, 'paid_status', None) == 'paid':
            admin_user = get_admin_user()
            if admin_user:
                with transaction.atomic():
                    je = AccountingService.create_accessory_consumption_journal_entry(instance, admin_user)
                    if je:
                        logger.info(
                            "Accessory consumption journal entry created for service sale ID: "
                            f"{instance.id} - Entry: {je.entry_number or je.id}"
                        )
            else:
                logger.error(
                    f"No admin user found for accessory consumption on service sale ID: {instance.id}"
                )
    except Exception as e:
        logger.error(
            f"Error creating service sale/accessory consumption journal entries for sale ID {instance.id}: {str(e)}"
        )
        # Log the full traceback for debugging
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")


@receiver(post_save, sender=IncidentWriteOff)
def create_raw_material_writeoff_journal_entry_auto(sender, instance, **kwargs):
    """Automatically create JE when an incident write-off is approved.

    Creates a raw-material loss/spoilage entry at the latest requisition
    (or market) price, using AccountingService.create_raw_material_writeoff_journal_entry.
    """
    try:
        if instance.status != 'approved':
            return

        # Prevent duplicates using our RM-WO-{id} reference
        ref = f"RM-WO-{instance.id}"
        if JournalEntry.objects.filter(reference=ref).exists():
            logger.info(
                f"Raw material write-off journal entry already exists for incident ID: {instance.id}"
            )
            return

        admin_user = get_admin_user()
        if admin_user:
            with transaction.atomic():
                je = AccountingService.create_raw_material_writeoff_journal_entry(instance, admin_user)
                if je:
                    logger.info(
                        f"Raw material write-off journal entry created for incident ID: {instance.id} "
                        f"- Entry: {je.entry_number or je.id}"
                    )
                else:
                    logger.error(
                        f"Failed to create raw material write-off journal entry for incident ID: {instance.id}"
                    )
        else:
            logger.error(
                f"No admin user found for raw material write-off incident ID: {instance.id}"
            )
    except Exception as e:
        logger.error(
            f"Error creating raw material write-off journal entry for incident ID {instance.id}: {str(e)}"
        )


@receiver(post_save, sender=InternalAccessoryRequest)
def create_internal_accessory_transfer_journal_entry_auto(sender, instance, **kwargs):
    """Create JE when an internal accessory request is delivered to a salon store.

    DR Accessory Inventory {store.name}
    CR Accessory Inventory - Main Store
    """
    try:
        if instance.status != 'delivered':
            return

        ref = f"AccInt-{instance.id}"
        if JournalEntry.objects.filter(reference=ref).exists():
            logger.info(
                f"Internal accessory transfer journal entry already exists for request ID: {instance.id}"
            )
            return

        admin_user = get_admin_user()
        if admin_user:
            with transaction.atomic():
                je = AccountingService.create_internal_accessory_transfer_journal_entry(instance, admin_user)
                if je:
                    logger.info(
                        f"Internal accessory transfer journal entry created for request ID: {instance.id} "
                        f"- Entry: {je.entry_number or je.id}"
                    )
                else:
                    logger.error(
                        f"Failed to create internal accessory transfer journal entry for request ID: {instance.id}"
                    )
        else:
            logger.error(
                f"No admin user found for internal accessory request ID: {instance.id}"
            )
    except Exception as e:
        logger.error(
            f"Error creating internal accessory transfer journal entry for request ID {instance.id}: {str(e)}"
        )


@receiver(post_save, sender=ManufacturedProductInventory)
def link_manufacturing_record_to_inventory(sender, instance, created, **kwargs):
    """Ensure ManufacturingRecord rows are tied to production-store inventory.

    ManufacturedProductInventory represents inventory in the production store.
    When it is created, we try to link or create a ManufacturingRecord using
    the manufacturing journal entry with reference "MFG-{batch_number}".
    """
    try:
        if not instance.batch_number:
            return

        # Find the manufacturing JournalEntry for this batch
        je = JournalEntry.objects.filter(reference=f"MFG-{instance.batch_number}").first()
        if not je:
            return

        # First, try to attach any placeholder record that has this journal_entry
        mr = ManufacturingRecord.objects.filter(
            journal_entry=je,
            manufacture_product__isnull=True,
        ).first()

        if mr:
            mr.manufacture_product = instance
            mr.save(update_fields=['manufacture_product'])
        else:
            # If no placeholder exists, create a new ManufacturingRecord.
            from decimal import Decimal
            from django.db.models import Sum

            # Derive amount from the journal entry lines (sum of debits)
            total_amount = je.entries.filter(entry_type='debit').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')

            ManufacturingRecord.objects.get_or_create(
                manufacture_product=instance,
                journal_entry=je,
                defaults={'amount': total_amount},
            )
    except Exception as e:
        logger.error(f"Error linking ManufacturingRecord to inventory {instance.id}: {str(e)}")
