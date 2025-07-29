from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User
from accounts.services import AccountingService
from accounts.models import ProductionExpense, SalesRevenue, StoreTransfer as StoreTransferLink, ManufacturingRecord, PaymentRecord
from production.models import StoreSale, Requisition, StoreTransfer, ManufactureProduct, PaymentVoucher
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Simple sync of missing accounting entries (no Celery required)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes',
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['sales', 'requisitions', 'manufacturing', 'payments', 'all'],
            default='all',
            help='Type of entries to sync',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of entries to sync in one run',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        sync_type = options['type']
        limit = options['limit']
        
        self.stdout.write(f"Starting simple accounting sync at {datetime.now()}")
        
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(
                self.style.ERROR('No admin user found. Please create a superuser first.')
            )
            return
        
        synced_count = 0
        
        if sync_type in ['sales', 'all']:
            synced_count += self._sync_sales(admin_user, dry_run, limit)
        
        if sync_type in ['requisitions', 'all']:
            synced_count += self._sync_requisitions(admin_user, dry_run, limit)
        
        if sync_type in ['manufacturing', 'all']:
            synced_count += self._sync_manufacturing(admin_user, dry_run, limit)
        
        if sync_type in ['payments', 'all']:
            synced_count += self._sync_payments(admin_user, dry_run, limit)
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'DRY RUN: Would sync {synced_count} accounting entries')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully synced {synced_count} accounting entries')
            )
        
        logger.info(f"Simple sync completed: {synced_count} entries synced")

    def _sync_sales(self, admin_user, dry_run, limit):
        """Sync missing sales journal entries"""
        # Get sales that don't have accounting entries
        sales_with_entries_ids = set(SalesRevenue.objects.filter(
            store_sale__isnull=False
        ).values_list('store_sale_id', flat=True))
        
        sales_without_entries = StoreSale.objects.filter(
            total_amount__gt=0
        ).exclude(id__in=sales_with_entries_ids)[:limit]
        
        count = 0
        for sale in sales_without_entries:
            try:
                if not dry_run:
                    with transaction.atomic():
                        AccountingService.create_sales_journal_entry(sale, admin_user)
                count += 1
                self.stdout.write(f"{'[DRY RUN] ' if dry_run else ''}Synced sale ID: {sale.id}")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error syncing sale {sale.id}: {str(e)}")
                )
        
        return count

    def _sync_requisitions(self, admin_user, dry_run, limit):
        """Sync missing requisition journal entries"""
        # Get requisitions that don't have accounting entries
        requisitions_with_entries_ids = set(ProductionExpense.objects.values_list('requisition_id', flat=True))
        
        requisitions_without_entries = Requisition.objects.filter(
            status__in=['approved', 'checking', 'delivered'],
            total_cost__gt=0
        ).exclude(id__in=requisitions_with_entries_ids)[:limit]
        
        count = 0
        for requisition in requisitions_without_entries:
            try:
                if not dry_run:
                    with transaction.atomic():
                        AccountingService.create_requisition_expense_journal_entry(requisition, admin_user)
                count += 1
                self.stdout.write(f"{'[DRY RUN] ' if dry_run else ''}Synced requisition ID: {requisition.id}")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error syncing requisition {requisition.id}: {str(e)}")
                )
        
        return count

    def _sync_manufacturing(self, admin_user, dry_run, limit):
        """Sync missing manufacturing journal entries"""
        # Get manufacturing products that don't have accounting entries
        manufacturing_with_entries_ids = set(ManufacturingRecord.objects.values_list('manufacture_product_id', flat=True))
        
        products_without_entries = ManufactureProduct.objects.exclude(
            id__in=manufacturing_with_entries_ids
        )[:limit]
        
        count = 0
        for product in products_without_entries:
            try:
                if not dry_run:
                    with transaction.atomic():
                        AccountingService.create_manufacturing_journal_entry(product, admin_user)
                count += 1
                self.stdout.write(f"{'[DRY RUN] ' if dry_run else ''}Synced manufacturing product ID: {product.id}")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error syncing manufacturing product {product.id}: {str(e)}")
                )
        
        return count

    def _sync_payments(self, admin_user, dry_run, limit):
        """Sync missing payment journal entries"""
        # Get payment vouchers that don't have accounting entries
        payments_with_entries_ids = set(PaymentRecord.objects.values_list('payment_voucher_id', flat=True))
        
        payments_without_entries = PaymentVoucher.objects.exclude(
            id__in=payments_with_entries_ids
        )[:limit]
        
        count = 0
        for payment in payments_without_entries:
            try:
                if not dry_run:
                    with transaction.atomic():
                        AccountingService.create_payment_journal_entry(payment, admin_user)
                count += 1
                self.stdout.write(f"{'[DRY RUN] ' if dry_run else ''}Synced payment voucher ID: {payment.id}")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error syncing payment voucher {payment.id}: {str(e)}")
                )
        
        return count 