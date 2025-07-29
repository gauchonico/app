import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from accounts.services import AccountingService
from accounts.models import JournalEntry, ProductionExpense, SalesRevenue, StoreTransfer as StoreTransferLink, ManufacturingRecord, PaymentRecord
from production.models import StoreSale, Requisition, StoreTransfer, ManufactureProduct, PaymentVoucher

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
            return ManufacturingRecord.objects.filter(manufacture_product=instance).exists()
        elif isinstance(instance, StoreTransfer):
            return StoreTransferLink.objects.filter(transfer=instance).exists()
        elif isinstance(instance, PaymentVoucher):
            return PaymentRecord.objects.filter(payment_voucher=instance).exists()
        return False
    except Exception as e:
        logger.error(f"Error checking existing entry: {str(e)}")
        return False

@receiver(post_save, sender=StoreSale)
def create_sales_journal_entry_auto(sender, instance, created, **kwargs):
    """Automatically create journal entry when a store sale is created"""
    try:
        if created and instance.total_amount and instance.total_amount > 0:
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
                    AccountingService.create_payment_journal_entry(instance, admin_user)
                    logger.info(f"Payment journal entry created for voucher ID: {instance.id}")
            else:
                logger.error(f"No admin user found for voucher ID: {instance.id}")
    except Exception as e:
        logger.error(f"Error creating payment journal entry for voucher ID {instance.id}: {str(e)}") 