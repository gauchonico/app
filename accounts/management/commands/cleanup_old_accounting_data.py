from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from accounts.models import JournalEntry, ProductionExpense, SalesRevenue, StoreTransfer, ManufacturingRecord, PaymentRecord
from production.models import Requisition, StoreSale, ServiceSale
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up old accounting data from deleted sales orders and production records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation',
        )
        parser.add_argument(
            '--entry-type',
            type=str,
            choices=['production', 'sales', 'all'],
            default='all',
            help='Type of entries to clean up',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        entry_type = options['entry_type']
        
        self.stdout.write(
            self.style.SUCCESS('🔍 Analyzing old accounting data...')
        )
        
        # Get current valid records
        valid_requisitions = set(Requisition.objects.values_list('id', flat=True))
        valid_store_sales = set(StoreSale.objects.values_list('id', flat=True))
        valid_service_sales = set(ServiceSale.objects.values_list('id', flat=True))
        
        self.stdout.write(f'📊 Current valid records:')
        self.stdout.write(f'   - Requisitions: {len(valid_requisitions)}')
        self.stdout.write(f'   - Store Sales: {len(valid_store_sales)}')
        self.stdout.write(f'   - Service Sales: {len(valid_service_sales)}')
        
        # Analyze orphaned accounting records
        orphaned_records = self.analyze_orphaned_records(
            valid_requisitions, valid_store_sales, valid_service_sales, entry_type
        )
        
        if not orphaned_records['total']:
            self.stdout.write(
                self.style.SUCCESS('✅ No orphaned accounting records found!')
            )
            return
        
        # Display analysis
        self.display_analysis(orphaned_records)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 DRY RUN - No records will be deleted')
            )
            return
        
        # Confirm deletion
        if not force:
            confirm = input('\n❓ Do you want to delete these orphaned records? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('❌ Operation cancelled.')
                return
        
        # Perform cleanup
        self.perform_cleanup(orphaned_records)
        
        self.stdout.write(
            self.style.SUCCESS('✅ Cleanup completed successfully!')
        )

    def analyze_orphaned_records(self, valid_requisitions, valid_store_sales, valid_service_sales, entry_type):
        """Analyze orphaned accounting records"""
        orphaned = {
            'production_expenses': [],
            'sales_revenues': [],
            'store_transfers': [],
            'manufacturing_records': [],
            'payment_records': [],
            'journal_entries': set(),
            'total': 0
        }
        
        # Check Production Expenses
        if entry_type in ['production', 'all']:
            for expense in ProductionExpense.objects.all():
                if expense.requisition_id not in valid_requisitions:
                    orphaned['production_expenses'].append(expense)
                    orphaned['journal_entries'].add(expense.journal_entry_id)
        
        # Check Sales Revenues
        if entry_type in ['sales', 'all']:
            for revenue in SalesRevenue.objects.all():
                is_orphaned = False
                
                if revenue.service_sale and revenue.service_sale_id not in valid_service_sales:
                    is_orphaned = True
                elif revenue.store_sale and revenue.store_sale_id not in valid_store_sales:
                    is_orphaned = True
                
                if is_orphaned:
                    orphaned['sales_revenues'].append(revenue)
                    orphaned['journal_entries'].add(revenue.journal_entry_id)
        
        # Check Store Transfers
        if entry_type in ['all']:
            for transfer in StoreTransfer.objects.all():
                if transfer.transfer_id and not transfer.transfer:
                    orphaned['store_transfers'].append(transfer)
                    orphaned['journal_entries'].add(transfer.journal_entry_id)
        
        # Check Manufacturing Records
        if entry_type in ['production', 'all']:
            for manufacturing in ManufacturingRecord.objects.all():
                if manufacturing.manufacture_product_id and not manufacturing.manufacture_product:
                    orphaned['manufacturing_records'].append(manufacturing)
                    orphaned['journal_entries'].add(manufacturing.journal_entry_id)
        
        # Check Payment Records
        if entry_type in ['all']:
            for payment in PaymentRecord.objects.all():
                if payment.payment_voucher_id and not payment.payment_voucher:
                    orphaned['payment_records'].append(payment)
                    orphaned['journal_entries'].add(payment.journal_entry_id)
        
        # Count total orphaned records
        orphaned['total'] = (
            len(orphaned['production_expenses']) +
            len(orphaned['sales_revenues']) +
            len(orphaned['store_transfers']) +
            len(orphaned['manufacturing_records']) +
            len(orphaned['payment_records'])
        )
        
        return orphaned

    def display_analysis(self, orphaned_records):
        """Display analysis of orphaned records"""
        self.stdout.write('\n📋 ORPHANED ACCOUNTING RECORDS ANALYSIS:')
        self.stdout.write('=' * 50)
        
        if orphaned_records['production_expenses']:
            self.stdout.write(f'🔴 Production Expenses: {len(orphaned_records["production_expenses"])}')
            for expense in orphaned_records['production_expenses'][:5]:  # Show first 5
                self.stdout.write(f'   - Requisition ID {expense.requisition_id} (JE: {expense.journal_entry.entry_number})')
            if len(orphaned_records['production_expenses']) > 5:
                self.stdout.write(f'   ... and {len(orphaned_records["production_expenses"]) - 5} more')
        
        if orphaned_records['sales_revenues']:
            self.stdout.write(f'🔴 Sales Revenues: {len(orphaned_records["sales_revenues"])}')
            for revenue in orphaned_records['sales_revenues'][:5]:  # Show first 5
                sale_ref = revenue.service_sale_id if revenue.service_sale_id else revenue.store_sale_id
                self.stdout.write(f'   - Sale ID {sale_ref} (JE: {revenue.journal_entry.entry_number})')
            if len(orphaned_records['sales_revenues']) > 5:
                self.stdout.write(f'   ... and {len(orphaned_records["sales_revenues"]) - 5} more')
        
        if orphaned_records['store_transfers']:
            self.stdout.write(f'🔴 Store Transfers: {len(orphaned_records["store_transfers"])}')
        
        if orphaned_records['manufacturing_records']:
            self.stdout.write(f'🔴 Manufacturing Records: {len(orphaned_records["manufacturing_records"])}')
        
        if orphaned_records['payment_records']:
            self.stdout.write(f'🔴 Payment Records: {len(orphaned_records["payment_records"])}')
        
        self.stdout.write(f'\n📊 SUMMARY:')
        self.stdout.write(f'   - Total orphaned records: {orphaned_records["total"]}')
        self.stdout.write(f'   - Affected Journal Entries: {len(orphaned_records["journal_entries"])}')

    @transaction.atomic
    def perform_cleanup(self, orphaned_records):
        """Perform the actual cleanup"""
        self.stdout.write('\n🧹 Starting cleanup...')
        
        deleted_counts = {
            'production_expenses': 0,
            'sales_revenues': 0,
            'store_transfers': 0,
            'manufacturing_records': 0,
            'payment_records': 0,
            'journal_entries': 0
        }
        
        # Delete orphaned production expenses
        if orphaned_records['production_expenses']:
            deleted_counts['production_expenses'] = len(orphaned_records['production_expenses'])
            for expense in orphaned_records['production_expenses']:
                expense.delete()
            self.stdout.write(f'✅ Deleted {deleted_counts["production_expenses"]} orphaned production expenses')
        
        # Delete orphaned sales revenues
        if orphaned_records['sales_revenues']:
            deleted_counts['sales_revenues'] = len(orphaned_records['sales_revenues'])
            for revenue in orphaned_records['sales_revenues']:
                revenue.delete()
            self.stdout.write(f'✅ Deleted {deleted_counts["sales_revenues"]} orphaned sales revenues')
        
        # Delete orphaned store transfers
        if orphaned_records['store_transfers']:
            deleted_counts['store_transfers'] = len(orphaned_records['store_transfers'])
            for transfer in orphaned_records['store_transfers']:
                transfer.delete()
            self.stdout.write(f'✅ Deleted {deleted_counts["store_transfers"]} orphaned store transfers')
        
        # Delete orphaned manufacturing records
        if orphaned_records['manufacturing_records']:
            deleted_counts['manufacturing_records'] = len(orphaned_records['manufacturing_records'])
            for manufacturing in orphaned_records['manufacturing_records']:
                manufacturing.delete()
            self.stdout.write(f'✅ Deleted {deleted_counts["manufacturing_records"]} orphaned manufacturing records')
        
        # Delete orphaned payment records
        if orphaned_records['payment_records']:
            deleted_counts['payment_records'] = len(orphaned_records['payment_records'])
            for payment in orphaned_records['payment_records']:
                payment.delete()
            self.stdout.write(f'✅ Deleted {deleted_counts["payment_records"]} orphaned payment records')
        
        # Delete orphaned journal entries (those with no related records)
        orphaned_journal_entries = JournalEntry.objects.filter(
            id__in=orphaned_records['journal_entries']
        ).filter(
            ~models.Q(production_expenses__isnull=False) &
            ~models.Q(sales_revenues__isnull=False) &
            ~models.Q(store_transfers__isnull=False) &
            ~models.Q(manufacturing_records__isnull=False) &
            ~models.Q(payment_records__isnull=False)
        )
        
        deleted_counts['journal_entries'] = orphaned_journal_entries.count()
        orphaned_journal_entries.delete()
        
        if deleted_counts['journal_entries']:
            self.stdout.write(f'✅ Deleted {deleted_counts["journal_entries"]} orphaned journal entries')
        
        # Summary
        total_deleted = sum(deleted_counts.values())
        self.stdout.write(f'\n📊 CLEANUP SUMMARY:')
        self.stdout.write(f'   - Total records deleted: {total_deleted}')
        for record_type, count in deleted_counts.items():
            if count > 0:
                self.stdout.write(f'   - {record_type.replace("_", " ").title()}: {count}')
