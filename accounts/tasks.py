import logging
from celery import shared_task
from django.db import transaction
from django.contrib.auth.models import User
from accounts.services import AccountingService
from production.models import StoreSale, Requisition, StoreTransfer, ManufactureProduct, PaymentVoucher

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def create_sales_journal_entry_task(self, sale_id):
    """Background task to create sales journal entry"""
    try:
        with transaction.atomic():
            sale = StoreSale.objects.get(id=sale_id)
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user and sale.total_amount:
                AccountingService.create_sales_journal_entry(sale, admin_user)
                logger.info(f"Sales journal entry created for sale ID: {sale_id}")
                return True
    except StoreSale.DoesNotExist:
        logger.error(f"Sale with ID {sale_id} not found")
        return False
    except Exception as exc:
        logger.error(f"Error creating sales journal entry for sale ID {sale_id}: {str(exc)}")
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def create_requisition_journal_entry_task(self, requisition_id):
    """Background task to create requisition journal entry"""
    try:
        with transaction.atomic():
            requisition = Requisition.objects.get(id=requisition_id)
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user and requisition.total_cost:
                AccountingService.create_requisition_expense_journal_entry(requisition, admin_user)
                logger.info(f"Requisition journal entry created for requisition ID: {requisition_id}")
                return True
    except Requisition.DoesNotExist:
        logger.error(f"Requisition with ID {requisition_id} not found")
        return False
    except Exception as exc:
        logger.error(f"Error creating requisition journal entry for requisition ID {requisition_id}: {str(exc)}")
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def create_manufacturing_journal_entry_task(self, product_id):
    """Background task to create manufacturing journal entry"""
    try:
        with transaction.atomic():
            product = ManufactureProduct.objects.get(id=product_id)
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                AccountingService.create_manufacturing_journal_entry(product, admin_user)
                logger.info(f"Manufacturing journal entry created for product ID: {product_id}")
                return True
    except ManufactureProduct.DoesNotExist:
        logger.error(f"ManufactureProduct with ID {product_id} not found")
        return False
    except Exception as exc:
        logger.error(f"Error creating manufacturing journal entry for product ID {product_id}: {str(exc)}")
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def create_payment_journal_entry_task(self, voucher_id):
    """Background task to create payment journal entry"""
    try:
        with transaction.atomic():
            voucher = PaymentVoucher.objects.get(id=voucher_id)
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                AccountingService.create_payment_journal_entry(voucher, admin_user)
                logger.info(f"Payment journal entry created for voucher ID: {voucher_id}")
                return True
    except PaymentVoucher.DoesNotExist:
        logger.error(f"PaymentVoucher with ID {voucher_id} not found")
        return False
    except Exception as exc:
        logger.error(f"Error creating payment journal entry for voucher ID {voucher_id}: {str(exc)}")
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_missing_accounting_entries_task(self):
    """Background task to sync any missing accounting entries"""
    try:
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            logger.error("No admin user found for accounting sync")
            return False
        
        synced_count = 0
        
        # Sync missing sales entries
        sales_without_entries = StoreSale.objects.filter(
            total_amount__gt=0
        ).exclude(
            accounting_entries__isnull=False
        )
        for sale in sales_without_entries:
            try:
                with transaction.atomic():
                    AccountingService.create_sales_journal_entry(sale, admin_user)
                    synced_count += 1
            except Exception as e:
                logger.error(f"Error syncing sale {sale.id}: {str(e)}")
        
        # Sync missing requisition entries
        requisitions_without_entries = Requisition.objects.filter(
            status__in=['approved', 'checking', 'delivered'],
            total_cost__gt=0
        ).exclude(
            accounting_entries__isnull=False
        )
        for requisition in requisitions_without_entries:
            try:
                with transaction.atomic():
                    AccountingService.create_requisition_expense_journal_entry(requisition, admin_user)
                    synced_count += 1
            except Exception as e:
                logger.error(f"Error syncing requisition {requisition.id}: {str(e)}")
        
        logger.info(f"Sync completed. {synced_count} entries synced.")
        return synced_count
        
    except Exception as exc:
        logger.error(f"Error in sync_missing_accounting_entries_task: {str(exc)}")
        raise self.retry(exc=exc) 