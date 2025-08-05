from django.core.management.base import BaseCommand
from accounts.services import AccountingService

class Command(BaseCommand):
    help = 'Process pending sales and create journal entries for paid service sales and store sales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually creating journal entries',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No journal entries will be created'))
        
        try:
            from production.models import ServiceSale, StoreSale
            
            # Count pending sales
            pending_service_sales = ServiceSale.objects.filter(
                paid_status='paid'
            ).exclude(
                accounting_entries__isnull=False
            ).count()
            
            pending_store_sales = StoreSale.objects.filter(
                payment_status='paid'
            ).exclude(
                accounting_entries__isnull=False
            ).count()
            
            self.stdout.write(f"Found {pending_service_sales} pending service sales")
            self.stdout.write(f"Found {pending_store_sales} pending store sales")
            
            if dry_run:
                self.stdout.write(self.style.SUCCESS('Dry run completed. Use without --dry-run to process sales.'))
                return
            
            # Process pending sales
            result = AccountingService.process_pending_sales()
            
            if result:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully processed {result['service_sales_processed']} service sales and "
                        f"{result['store_sales_processed']} store sales"
                    )
                )
            else:
                self.stdout.write(self.style.ERROR('Error processing pending sales'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}')) 