from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from production.models import StoreSale, Requisition, StoreTransfer, ManufactureProduct, PaymentVoucher
from accounts.models import JournalEntry, ProductionExpense, SalesRevenue, StoreTransfer as StoreTransferLink, ManufacturingRecord, PaymentRecord
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check accounting sync status and report any missing entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed breakdown of missing entries',
        )

    def handle(self, *args, **options):
        detailed = options['detailed']
        
        self.stdout.write(self.style.SUCCESS('=== Accounting Sync Status Report ==='))
        
        # Check Sales
        total_sales = StoreSale.objects.filter(total_amount__gt=0).count()
        sales_with_entries = SalesRevenue.objects.filter(
            store_sale__isnull=False
        ).values('store_sale').distinct().count()
        missing_sales = total_sales - sales_with_entries
        
        self.stdout.write(f"\n📊 Sales:")
        self.stdout.write(f"   Total Sales: {total_sales}")
        self.stdout.write(f"   With Accounting Entries: {sales_with_entries}")
        self.stdout.write(f"   Missing Entries: {missing_sales}")
        
        if detailed and missing_sales > 0:
            sales_with_entries_ids = set(SalesRevenue.objects.filter(
                store_sale__isnull=False
            ).values_list('store_sale_id', flat=True))
            missing_sales_list = StoreSale.objects.filter(
                total_amount__gt=0
            ).exclude(id__in=sales_with_entries_ids)[:10]
            for sale in missing_sales_list:
                self.stdout.write(f"     - Sale ID: {sale.id}, Amount: {sale.total_amount}, Date: {sale.sale_date}")
        
        # Check Requisitions
        total_requisitions = Requisition.objects.filter(
            status__in=['approved', 'checking', 'delivered'],
            total_cost__gt=0
        ).count()
        requisitions_with_entries = ProductionExpense.objects.values('requisition').distinct().count()
        missing_requisitions = total_requisitions - requisitions_with_entries
        
        self.stdout.write(f"\n📋 Requisitions:")
        self.stdout.write(f"   Total Approved Requisitions: {total_requisitions}")
        self.stdout.write(f"   With Accounting Entries: {requisitions_with_entries}")
        self.stdout.write(f"   Missing Entries: {missing_requisitions}")
        
        if detailed and missing_requisitions > 0:
            requisitions_with_entries_ids = set(ProductionExpense.objects.values_list('requisition_id', flat=True))
            missing_requisitions_list = Requisition.objects.filter(
                status__in=['approved', 'checking', 'delivered'],
                total_cost__gt=0
            ).exclude(id__in=requisitions_with_entries_ids)[:10]
            for req in missing_requisitions_list:
                self.stdout.write(f"     - Requisition ID: {req.id}, Cost: {req.total_cost}, Status: {req.status}")
        
        # Check Manufacturing
        total_manufacturing = ManufactureProduct.objects.count()
        manufacturing_with_entries = ManufacturingRecord.objects.values('manufacture_product').distinct().count()
        missing_manufacturing = total_manufacturing - manufacturing_with_entries
        
        self.stdout.write(f"\n🏭 Manufacturing:")
        self.stdout.write(f"   Total Manufacturing Records: {total_manufacturing}")
        self.stdout.write(f"   With Accounting Entries: {manufacturing_with_entries}")
        self.stdout.write(f"   Missing Entries: {missing_manufacturing}")
        
        # Check Payments
        total_payments = PaymentVoucher.objects.count()
        payments_with_entries = PaymentRecord.objects.values('payment_voucher').distinct().count()
        missing_payments = total_payments - payments_with_entries
        
        self.stdout.write(f"\n💳 Payments:")
        self.stdout.write(f"   Total Payment Vouchers: {total_payments}")
        self.stdout.write(f"   With Accounting Entries: {payments_with_entries}")
        self.stdout.write(f"   Missing Entries: {missing_payments}")
        
        # Summary
        total_missing = missing_sales + missing_requisitions + missing_manufacturing + missing_payments
        
        self.stdout.write(f"\n{'='*50}")
        self.stdout.write(f"📈 SUMMARY:")
        self.stdout.write(f"   Total Missing Accounting Entries: {total_missing}")
        
        if total_missing == 0:
            self.stdout.write(self.style.SUCCESS("✅ All accounting entries are synced!"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️  {total_missing} accounting entries are missing"))
            self.stdout.write(self.style.SUCCESS("Run 'python manage.py simple_sync_accounting' to fix missing entries"))
        
        # Log for monitoring
        if total_missing > 0:
            logger.warning(f"Accounting sync check found {total_missing} missing entries")
        else:
            logger.info("Accounting sync check passed - all entries are synced") 