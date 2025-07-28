from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.services import AccountingService
from production.models import ManufacturedProductInventory, StoreSale, Requisition, StoreTransfer, ManufactureProduct, PaymentVoucher, Store
from datetime import date, timedelta

class Command(BaseCommand):
    help = 'Sync existing production data with accounting system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for syncing (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for syncing (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--sync-sales',
            action='store_true',
            help='Sync store sales',
        )
        parser.add_argument(
            '--sync-requisitions',
            action='store_true',
            help='Sync production requisitions',
        )
        parser.add_argument(
            '--sync-manufacturing',
            action='store_true',
            help='Sync manufacturing records',
        )
        parser.add_argument(
            '--sync-transfers',
            action='store_true',
            help='Sync store transfers',
        )
        parser.add_argument(
            '--sync-payments',
            action='store_true',
            help='Sync payment vouchers',
        )
        parser.add_argument(
            '--sync-all',
            action='store_true',
            help='Sync all data types',
        )

    def handle(self, *args, **options):
        # Get admin user for creating entries
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.ERROR('No admin user found. Please create a superuser first.'))
            return
        
        # Set date range
        if options['start_date'] and options['end_date']:
            start_date = date.fromisoformat(options['start_date'])
            end_date = date.fromisoformat(options['end_date'])
        else:
            # Default to last 30 days
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
        
        self.stdout.write(f'Syncing data from {start_date} to {end_date}')
        
        # Sync store sales
        if options['sync_sales'] or options['sync_all']:
            self.stdout.write('Syncing store sales...')
            store_sales = StoreSale.objects.filter(
                sale_date__date__range=[start_date, end_date]
            )
            
            synced_count = 0
            for sale in store_sales:
                # Check if already synced
                if not hasattr(sale, 'accounting_entries') or not sale.accounting_entries.exists():
                    journal_entry = AccountingService.create_sales_journal_entry(sale, admin_user)
                    if journal_entry:
                        synced_count += 1
                        self.stdout.write(f'  Synced sale {sale.id}')
            
            self.stdout.write(f'Synced {synced_count} store sales')
        
        # Sync production requisitions
        if options['sync_requisitions'] or options['sync_all']:
            self.stdout.write('Syncing production requisitions...')
            requisitions = Requisition.objects.filter(
                created_at__date__range=[start_date, end_date],
                status__in=['approved', 'checking', 'delivered']  # Only synced approved requisitions
            )
            
            synced_count = 0
            for req in requisitions:
                # Check if already synced
                if not hasattr(req, 'accounting_entries') or not req.accounting_entries.exists():
                    journal_entry = AccountingService.create_requisition_expense_journal_entry(req, admin_user)
                    if journal_entry:
                        synced_count += 1
                        self.stdout.write(f'  Synced requisition {req.requisition_no}')
            
            self.stdout.write(f'Synced {synced_count} production requisitions')
        
        # Sync manufacturing records
        if options['sync_manufacturing'] or options['sync_all']:
            self.stdout.write('Syncing manufacturing records...')
            manufactured_products = ManufactureProduct.objects.filter(
                manufactured_at__date__range=[start_date, end_date]
            )
            
            synced_count = 0
            for mfg in manufactured_products:
                # Check if already synced (you might need to add a field to track this)
                journal_entry = AccountingService.create_manufacturing_journal_entry(mfg, admin_user)
                if journal_entry:
                    synced_count += 1
                    self.stdout.write(f'  Synced manufacturing {mfg.batch_number}')
            
            self.stdout.write(f'Synced {synced_count} manufacturing records')
        
        # Sync store transfers
        if options['sync_transfers'] or options['sync_all']:
            self.stdout.write('Syncing store transfers...')
            transfers = StoreTransfer.objects.filter(
                date__date__range=[start_date, end_date],
                status='Completed'  # Only synced completed transfers
            )
            
            synced_count = 0
            for transfer in transfers:
                # Check if already synced
                if not hasattr(transfer, 'accounting_entries') or not transfer.accounting_entries.exists():
                    journal_entry = AccountingService.create_store_transfer_journal_entry(transfer, admin_user)
                    if journal_entry:
                        synced_count += 1
                        self.stdout.write(f'  Synced transfer {transfer.liv_main_transfer_number}')
            
            self.stdout.write(f'Synced {synced_count} store transfers')
        
        # Sync payment vouchers
        if options['sync_payments'] or options['sync_all']:
            self.stdout.write('Syncing payment vouchers...')
            payments = PaymentVoucher.objects.filter(
                payment_date__date__range=[start_date, end_date]
            )
            
            synced_count = 0
            for payment in payments:
                # Check if already synced
                journal_entry = AccountingService.create_payment_journal_entry(payment, admin_user)
                if journal_entry:
                    synced_count += 1
                    self.stdout.write(f'  Synced payment {payment.voucher_number}')
            
            self.stdout.write(f'Synced {synced_count} payment vouchers')
        
        # Generate store financial summaries
        if options['sync_all']:
            self.stdout.write('Generating store financial summaries...')
            stores = Store.objects.all()
            
            for store in stores:
                summary = AccountingService.generate_store_financial_summary(store, start_date, end_date)
                if summary:
                    self.stdout.write(f'  Generated summary for {store.name}')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully synced production data with accounting system!')
        ) 