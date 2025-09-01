from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.business_integration import LivaraBusinessIntegration
from production.models import Requisition, PaymentVoucher, StoreSale, ServiceSale, ManufactureProduct
from accounts.models import JournalEntry

class Command(BaseCommand):
    help = 'Sync all existing LIVARA business data to accounting system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without actually creating entries',
        )
        parser.add_argument(
            '--module',
            type=str,
            help='Sync specific module: requisitions, payments, store_sales, service_sales, manufacturing, all',
            default='all'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        module = options['module']
        
        # Get admin user
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            self.stdout.write(
                self.style.ERROR('No superuser found. Please create a superuser first.')
            )
            return
        
        self.stdout.write(f'Using user: {user.username}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('=== DRY RUN MODE - No data will be modified ===')
            )
        
        self.stdout.write('=== LIVARA BUSINESS DATA SYNC ===')
        
        # Show current state
        self.show_current_state()
        
        if module == 'all' or module == 'requisitions':
            self.sync_requisitions(user, dry_run)
        
        if module == 'all' or module == 'payments':
            self.sync_payments(user, dry_run)
        
        if module == 'all' or module == 'store_sales':
            self.sync_store_sales(user, dry_run)
        
        if module == 'all' or module == 'service_sales':
            self.sync_service_sales(user, dry_run)
        
        if module == 'all' or module == 'manufacturing':
            self.sync_manufacturing(user, dry_run)
        
        self.stdout.write('\\n=== SYNC COMPLETE ===')
        self.show_final_state()
    
    def show_current_state(self):
        self.stdout.write('\\n--- Current State ---')
        self.stdout.write(f'Journal Entries: {JournalEntry.objects.count()}')
        self.stdout.write(f'Delivered Requisitions: {Requisition.objects.filter(status="delivered").count()}')
        self.stdout.write(f'Payment Vouchers: {PaymentVoucher.objects.count()}')
        self.stdout.write(f'Confirmed Store Sales: {StoreSale.objects.filter(status__in=["confirmed", "invoiced"]).count()}')
        self.stdout.write(f'Invoiced Service Sales: {ServiceSale.objects.filter(invoice_status="invoiced").count()}')
        self.stdout.write(f'Manufacturing Records: {ManufactureProduct.objects.count()}')
    
    def sync_requisitions(self, user, dry_run):
        self.stdout.write('\\n--- Syncing Requisitions ---')
        requisitions = Requisition.objects.filter(status='delivered')
        
        synced = 0
        for req in requisitions:
            existing = JournalEntry.objects.filter(reference=f"REQ-{req.requisition_no}").exists()
            
            if not existing:
                if not dry_run:
                    if LivaraBusinessIntegration.sync_requisition_to_accounting(req, user):
                        synced += 1
                        self.stdout.write(f'✓ Synced requisition: {req.requisition_no}')
                    else:
                        self.stdout.write(f'✗ Failed to sync: {req.requisition_no}')
                else:
                    self.stdout.write(f'[DRY RUN] Would sync: {req.requisition_no} - {req.total_cost}')
                    synced += 1
            else:
                self.stdout.write(f'⚪ Already synced: {req.requisition_no}')
        
        self.stdout.write(f'Requisitions synced: {synced}/{requisitions.count()}')
    
    def sync_payments(self, user, dry_run):
        self.stdout.write('\\n--- Syncing Payment Vouchers ---')
        payments = PaymentVoucher.objects.all()
        
        synced = 0
        for pv in payments:
            existing = JournalEntry.objects.filter(reference=f"PV-{pv.voucher_number}").exists()
            
            if not existing:
                if not dry_run:
                    if LivaraBusinessIntegration.sync_payment_voucher_to_accounting(pv, user):
                        synced += 1
                        self.stdout.write(f'✓ Synced payment: {pv.voucher_number}')
                    else:
                        self.stdout.write(f'✗ Failed to sync: {pv.voucher_number}')
                else:
                    self.stdout.write(f'[DRY RUN] Would sync: {pv.voucher_number} - {pv.amount_paid}')
                    synced += 1
            else:
                self.stdout.write(f'⚪ Already synced: {pv.voucher_number}')
        
        self.stdout.write(f'Payment vouchers synced: {synced}/{payments.count()}')
    
    def sync_store_sales(self, user, dry_run):
        self.stdout.write('\\n--- Syncing Store Sales ---')
        sales = StoreSale.objects.filter(status__in=['confirmed', 'invoiced'])
        
        synced = 0
        for sale in sales:
            existing = JournalEntry.objects.filter(reference=f"StoreSale-{sale.id}").exists()
            
            if not existing:
                if not dry_run:
                    if LivaraBusinessIntegration.sync_store_sale_to_accounting(sale, user):
                        synced += 1
                        self.stdout.write(f'✓ Synced store sale: {sale.order_number or sale.id}')
                    else:
                        self.stdout.write(f'✗ Failed to sync: {sale.order_number or sale.id}')
                else:
                    self.stdout.write(f'[DRY RUN] Would sync: {sale.order_number or sale.id} - {sale.total_amount}')
                    synced += 1
            else:
                self.stdout.write(f'⚪ Already synced: {sale.order_number or sale.id}')
        
        self.stdout.write(f'Store sales synced: {synced}/{sales.count()}')
    
    def sync_service_sales(self, user, dry_run):
        self.stdout.write('\\n--- Syncing Service Sales ---')
        sales = ServiceSale.objects.filter(invoice_status='invoiced')
        
        synced = 0
        for sale in sales:
            existing = JournalEntry.objects.filter(reference=f"ServiceSale-{sale.id}").exists()
            
            if not existing:
                if not dry_run:
                    from accounts.services import AccountingService
                    if AccountingService.create_service_sale_journal_entry(sale, user):
                        synced += 1
                        self.stdout.write(f'✓ Synced service sale: {sale.service_sale_number or sale.id}')
                    else:
                        self.stdout.write(f'✗ Failed to sync: {sale.service_sale_number or sale.id}')
                else:
                    self.stdout.write(f'[DRY RUN] Would sync: {sale.service_sale_number or sale.id} - {sale.total_amount}')
                    synced += 1
            else:
                self.stdout.write(f'⚪ Already synced: {sale.service_sale_number or sale.id}')
        
        self.stdout.write(f'Service sales synced: {synced}/{sales.count()}')
    
    def sync_manufacturing(self, user, dry_run):
        self.stdout.write('\\n--- Syncing Manufacturing ---')
        manufacturing = ManufactureProduct.objects.all()
        
        synced = 0
        for mfg in manufacturing:
            existing = JournalEntry.objects.filter(reference=f"MFG-{mfg.id}").exists()
            
            if not existing:
                if not dry_run:
                    if LivaraBusinessIntegration.sync_manufacturing_to_accounting(mfg, user):
                        synced += 1
                        self.stdout.write(f'✓ Synced manufacturing: {mfg.product.product_name}')
                    else:
                        self.stdout.write(f'✗ Failed to sync: {mfg.product.product_name}')
                else:
                    self.stdout.write(f'[DRY RUN] Would sync: {mfg.product.product_name}')
                    synced += 1
            else:
                self.stdout.write(f'⚪ Already synced: {mfg.product.product_name}')
        
        self.stdout.write(f'Manufacturing records synced: {synced}/{manufacturing.count()}')
    
    def show_final_state(self):
        self.stdout.write('\\n--- Final State ---')
        self.stdout.write(f'Total Journal Entries: {JournalEntry.objects.count()}')
        
        # Show journal entries by type
        req_entries = JournalEntry.objects.filter(reference__startswith='REQ-').count()
        pv_entries = JournalEntry.objects.filter(reference__startswith='PV-').count()
        store_entries = JournalEntry.objects.filter(reference__startswith='StoreSale-').count()
        service_entries = JournalEntry.objects.filter(reference__startswith='ServiceSale-').count()
        mfg_entries = JournalEntry.objects.filter(reference__startswith='MFG-').count()
        commission_entries = JournalEntry.objects.filter(reference__icontains='Commission').count()
        
        self.stdout.write(f'- Requisition entries: {req_entries}')
        self.stdout.write(f'- Payment entries: {pv_entries}')
        self.stdout.write(f'- Store sale entries: {store_entries}')
        self.stdout.write(f'- Service sale entries: {service_entries}')
        self.stdout.write(f'- Manufacturing entries: {mfg_entries}')
        self.stdout.write(f'- Commission entries: {commission_entries}')
