from django.core.management.base import BaseCommand
from django.db import transaction, models
from django.contrib.auth.models import User
from django.utils import timezone
from accounts.services import AccountingService
from accounts.models import (
    JournalEntry, ProductionExpense, SalesRevenue, StoreTransfer, 
    ManufacturingRecord, PaymentRecord
)
from production.models import StoreSale, Requisition, StoreTransfer as ProdStoreTransfer, ManufacturedProductInventory, PaymentVoucher
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up old accounting data and sync with current production data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--cleanup-only',
            action='store_true',
            help='Only clean up old data, do not sync new entries',
        )
        parser.add_argument(
            '--sync-only',
            action='store_true',
            help='Only sync new entries, do not clean up old data',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force operations without confirmation',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        cleanup_only = options['cleanup_only']
        sync_only = options['sync_only']
        force = options['force']
        
        self.stdout.write(
            self.style.SUCCESS('🔄 Starting Accounting Data Sync and Cleanup...')
        )
        
        # Get admin user
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(
                self.style.ERROR('❌ No admin user found. Please create a superuser first.')
            )
            return
        
        # Step 1: Analyze current data
        self.analyze_current_data()
        
        # Step 2: Clean up old data (unless sync-only)
        if not sync_only:
            self.cleanup_old_data(dry_run, force)
        
        # Step 3: Sync current data (unless cleanup-only)
        if not cleanup_only:
            self.sync_current_data(admin_user, dry_run)
        
        self.stdout.write(
            self.style.SUCCESS('✅ Sync and cleanup completed!')
        )

    def analyze_current_data(self):
        """Analyze current production and accounting data"""
        self.stdout.write('\n📊 CURRENT DATA ANALYSIS:')
        self.stdout.write('=' * 40)
        
        # Production data
        requisitions = Requisition.objects.count()
        store_sales = StoreSale.objects.count()
        store_transfers = ProdStoreTransfer.objects.count()
        manufacturing = ManufacturedProductInventory.objects.count()
        payments = PaymentVoucher.objects.count()
        
        # Accounting data
        journal_entries = JournalEntry.objects.count()
        production_expenses = ProductionExpense.objects.count()
        sales_revenues = SalesRevenue.objects.count()
        accounting_transfers = StoreTransfer.objects.count()
        manufacturing_records = ManufacturingRecord.objects.count()
        payment_records = PaymentRecord.objects.count()
        
        self.stdout.write(f'📦 Production Data:')
        self.stdout.write(f'   - Requisitions: {requisitions}')
        self.stdout.write(f'   - Store Sales: {store_sales}')
        self.stdout.write(f'   - Store Transfers: {store_transfers}')
        self.stdout.write(f'   - Manufacturing: {manufacturing}')
        self.stdout.write(f'   - Payments: {payments}')
        
        self.stdout.write(f'\n💰 Accounting Data:')
        self.stdout.write(f'   - Journal Entries: {journal_entries}')
        self.stdout.write(f'   - Production Expenses: {production_expenses}')
        self.stdout.write(f'   - Sales Revenues: {sales_revenues}')
        self.stdout.write(f'   - Store Transfers: {accounting_transfers}')
        self.stdout.write(f'   - Manufacturing Records: {manufacturing_records}')
        self.stdout.write(f'   - Payment Records: {payment_records}')

    def cleanup_old_data(self, dry_run, force):
        """Clean up orphaned accounting records"""
        self.stdout.write('\n🧹 CLEANING UP OLD DATA:')
        self.stdout.write('=' * 40)
        
        # Get current valid record IDs
        valid_requisitions = set(Requisition.objects.values_list('id', flat=True))
        valid_store_sales = set(StoreSale.objects.values_list('id', flat=True))
        valid_store_transfers = set(ProdStoreTransfer.objects.values_list('id', flat=True))
        valid_manufacturing = set(ManufacturedProductInventory.objects.values_list('id', flat=True))
        valid_payments = set(PaymentVoucher.objects.values_list('id', flat=True))
        
        # Find orphaned records
        orphaned_expenses = ProductionExpense.objects.exclude(requisition_id__in=valid_requisitions)
        orphaned_sales = SalesRevenue.objects.exclude(
            models.Q(service_sale__isnull=True) & models.Q(store_sale_id__in=valid_store_sales)
        )
        orphaned_transfers = StoreTransfer.objects.exclude(transfer_id__in=valid_store_transfers)
        orphaned_manufacturing = ManufacturingRecord.objects.exclude(manufacture_product_id__in=valid_manufacturing)
        orphaned_payments = PaymentRecord.objects.exclude(payment_voucher_id__in=valid_payments)
        
        total_orphaned = (
            orphaned_expenses.count() + 
            orphaned_sales.count() + 
            orphaned_transfers.count() + 
            orphaned_manufacturing.count() + 
            orphaned_payments.count()
        )
        
        if total_orphaned == 0:
            self.stdout.write('✅ No orphaned records found!')
            return
        
        self.stdout.write(f'🔴 Found {total_orphaned} orphaned records:')
        self.stdout.write(f'   - Production Expenses: {orphaned_expenses.count()}')
        self.stdout.write(f'   - Sales Revenues: {orphaned_sales.count()}')
        self.stdout.write(f'   - Store Transfers: {orphaned_transfers.count()}')
        self.stdout.write(f'   - Manufacturing Records: {orphaned_manufacturing.count()}')
        self.stdout.write(f'   - Payment Records: {orphaned_payments.count()}')
        
        if dry_run:
            self.stdout.write('🔍 DRY RUN - No records will be deleted')
            return
        
        if not force:
            confirm = input('\n❓ Do you want to delete these orphaned records? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('❌ Cleanup cancelled.')
                return
        
        # Delete orphaned records
        with transaction.atomic():
            orphaned_expenses.delete()
            orphaned_sales.delete()
            orphaned_transfers.delete()
            orphaned_manufacturing.delete()
            orphaned_payments.delete()
            
            # Delete orphaned journal entries
            # IMPORTANT: exclude any journal entries that are linked to CashDrawerBanking,
            # because that FK is PROTECT and those entries are not truly orphaned.
            orphaned_journal_entries = JournalEntry.objects.filter(
                ~models.Q(production_expenses__isnull=False) &
                ~models.Q(sales_revenues__isnull=False) &
                ~models.Q(store_transfers__isnull=False) &
                ~models.Q(manufacturing_records__isnull=False) &
                ~models.Q(payment_records__isnull=False) &
                ~models.Q(cash_drawer_banking__isnull=False)
            )
            orphaned_count = orphaned_journal_entries.count()
            orphaned_journal_entries.delete()
            total_orphaned += orphaned_count
            
            self.stdout.write(f'✅ Deleted {total_orphaned} orphaned records')

    def sync_current_data(self, admin_user, dry_run):
        """Sync current production data to accounting"""
        self.stdout.write('\n🔄 SYNCING CURRENT DATA:')
        self.stdout.write('=' * 40)
        
        synced_count = 0
        
        # Sync requisitions
        synced_count += self._sync_requisitions(admin_user, dry_run)
        
        # Sync store sales
        synced_count += self._sync_store_sales(admin_user, dry_run)
        
        # Sync store transfers
        synced_count += self._sync_store_transfers(admin_user, dry_run)
        
        # Sync manufacturing
        synced_count += self._sync_manufacturing(admin_user, dry_run)
        
        # Sync payments
        synced_count += self._sync_payments(admin_user, dry_run)
        
        if dry_run:
            self.stdout.write(f'🔍 DRY RUN: Would sync {synced_count} entries')
        else:
            self.stdout.write(f'✅ Synced {synced_count} entries')

    def _sync_requisitions(self, admin_user, dry_run):
        """Sync requisitions without accounting entries"""
        requisitions_to_sync = Requisition.objects.filter(
            status__in=['approved', 'checking', 'delivered'],
            total_cost__gt=0
        ).exclude(
            accounting_entries__isnull=False
        )
        
        count = 0
        for requisition in requisitions_to_sync:
            try:
                if not dry_run:
                    with transaction.atomic():
                        AccountingService.create_requisition_expense_journal_entry(requisition, admin_user)
                count += 1
                self.stdout.write(f"{'[DRY RUN] ' if dry_run else ''}✅ Synced requisition: {requisition.requisition_no}")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error syncing requisition {requisition.requisition_no}: {str(e)}")
                )
        
        if count > 0:
            self.stdout.write(f"📊 Synced {count} requisitions")
        
        return count

    def _sync_store_sales(self, admin_user, dry_run):
        """Sync store sales without accounting entries.

        We treat a StoreSale as "already synced" if it has at least one
        SalesRevenue record (accounts.models.SalesRevenue) pointing to it,
        via the related name `revenue_records`.
        """
        sales_to_sync = StoreSale.objects.filter(
            total_amount__gt=0
        ).exclude(
            revenue_records__isnull=False
        )
        
        count = 0
        for sale in sales_to_sync:
            try:
                if not dry_run:
                    with transaction.atomic():
                        AccountingService.create_sales_journal_entry(sale, admin_user)
                count += 1
                self.stdout.write(f"{'[DRY RUN] ' if dry_run else ''}✅ Synced store sale: {sale.id}")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error syncing store sale {sale.id}: {str(e)}")
                )
        
        if count > 0:
            self.stdout.write(f"📊 Synced {count} store sales")
        
        return count

    def _sync_store_transfers(self, admin_user, dry_run):
        """Sync store transfers without accounting entries"""
        transfers_to_sync = ProdStoreTransfer.objects.exclude(
            accounting_entries__isnull=False
        )
        
        count = 0
        for transfer in transfers_to_sync:
            try:
                if not dry_run:
                    with transaction.atomic():
                        AccountingService.create_store_transfer_journal_entry(transfer, admin_user)
                count += 1
                self.stdout.write(f"{'[DRY RUN] ' if dry_run else ''}✅ Synced store transfer: {transfer.id}")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error syncing store transfer {transfer.id}: {str(e)}")
                )
        
        if count > 0:
            self.stdout.write(f"📊 Synced {count} store transfers")
        
        return count

    def _sync_manufacturing(self, admin_user, dry_run):
        """Sync manufacturing without accounting entries.

        We treat a ManufactureProduct batch as "already synced" if there is
        already a JournalEntry with the reference pattern we use for
        manufacturing entries ("MFG-{batch_number}"). This avoids relying on
        a reverse relation that does not exist between ManufactureProduct and
        ManufacturedProductInventory.
        """
        from production.models import ManufactureProduct

        # Consider all manufacture batches that are tied to a production order
        products_to_sync = ManufactureProduct.objects.filter(
            production_order__isnull=False
        )

        count = 0
        for product in products_to_sync:
            # Skip if a manufacturing JE for this batch already exists
            from accounts.models import JournalEntry
            if JournalEntry.objects.filter(reference=f"MFG-{product.batch_number}").exists():
                continue

            try:
                if not dry_run:
                    with transaction.atomic():
                        AccountingService.create_manufacturing_journal_entry(product, admin_user)
                count += 1
                self.stdout.write(f"{'[DRY RUN] ' if dry_run else ''}✅ Synced manufacturing: {product.id}")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error syncing manufacturing {product.id}: {str(e)}")
                )
        
        if count > 0:
            self.stdout.write(f"📊 Synced {count} manufacturing records")
        
        return count

    def _sync_payments(self, admin_user, dry_run):
        """Sync payments without accounting entries"""
        payments_to_sync = PaymentVoucher.objects.exclude(
            accounting_entries__isnull=False
        )
        
        count = 0
        for payment in payments_to_sync:
            try:
                if not dry_run:
                    with transaction.atomic():
                        AccountingService.create_payment_journal_entry(payment, admin_user)
                count += 1
                self.stdout.write(f"{'[DRY RUN] ' if dry_run else ''}✅ Synced payment: {payment.voucher_number}")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error syncing payment {payment.voucher_number}: {str(e)}")
                )
        
        if count > 0:
            self.stdout.write(f"📊 Synced {count} payments")
        
        return count
