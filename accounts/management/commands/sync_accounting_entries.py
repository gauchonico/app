from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User
from accounts.services import AccountingService
from production.models import StoreSale, Requisition, StoreTransfer, ManufactureProduct, PaymentVoucher
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync missing accounting entries for all production transactions'

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

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        sync_type = options['type']
        
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(
                self.style.ERROR('No admin user found. Please create a superuser first.')
            )
            return
        
        synced_count = 0
        
        if sync_type in ['sales', 'all']:
            synced_count += self._sync_sales(admin_user, dry_run)
        
        if sync_type in ['requisitions', 'all']:
            synced_count += self._sync_requisitions(admin_user, dry_run)
        
        if sync_type in ['manufacturing', 'all']:
            synced_count += self._sync_manufacturing(admin_user, dry_run)
        
        if sync_type in ['payments', 'all']:
            synced_count += self._sync_payments(admin_user, dry_run)
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'DRY RUN: Would sync {synced_count} accounting entries')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully synced {synced_count} accounting entries')
            )

    def _sync_sales(self, admin_user, dry_run):
        """Sync missing sales journal entries"""
        sales_without_entries = StoreSale.objects.filter(
            total_amount__gt=0
        ).exclude(
            accounting_entries__isnull=False
        )
        
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

    def _sync_requisitions(self, admin_user, dry_run):
        """Sync missing requisition journal entries"""
        requisitions_without_entries = Requisition.objects.filter(
            status__in=['approved', 'checking', 'delivered'],
            total_cost__gt=0
        ).exclude(
            accounting_entries__isnull=False
        )
        
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

    def _sync_manufacturing(self, admin_user, dry_run):
        """Sync missing manufacturing journal entries"""
        products_without_entries = ManufactureProduct.objects.exclude(
            accounting_entries__isnull=False
        )
        
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

    def _sync_payments(self, admin_user, dry_run):
        """Sync missing payment journal entries"""
        payments_without_entries = PaymentVoucher.objects.exclude(
            accounting_entries__isnull=False
        )
        
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