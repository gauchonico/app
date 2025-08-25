from django.core.management.base import BaseCommand
from accounts.models import JournalEntry, ProductionExpense, SalesRevenue, ManufacturingRecord
from production.models import Requisition, StoreSale, ManufacturedProductInventory

class Command(BaseCommand):
    help = 'Show current accounting system status'

    def handle(self, *args, **options):
        self.stdout.write('📊 ACCOUNTING SYSTEM STATUS')
        self.stdout.write('=' * 50)
        
        # Production data counts
        requisitions = Requisition.objects.count()
        store_sales = StoreSale.objects.count()
        manufacturing = ManufacturedProductInventory.objects.count()
        
        # Accounting data counts
        journal_entries = JournalEntry.objects.count()
        production_expenses = ProductionExpense.objects.count()
        sales_revenues = SalesRevenue.objects.count()
        manufacturing_records = ManufacturingRecord.objects.count()
        
        self.stdout.write('\n📦 PRODUCTION DATA:')
        self.stdout.write(f'   - Requisitions: {requisitions}')
        self.stdout.write(f'   - Store Sales: {store_sales}')
        self.stdout.write(f'   - Manufacturing: {manufacturing}')
        
        self.stdout.write('\n💰 ACCOUNTING DATA:')
        self.stdout.write(f'   - Journal Entries: {journal_entries}')
        self.stdout.write(f'   - Production Expenses: {production_expenses}')
        self.stdout.write(f'   - Sales Revenues: {sales_revenues}')
        self.stdout.write(f'   - Manufacturing Records: {manufacturing_records}')
        
        # Check sync status
        self.stdout.write('\n🔄 SYNC STATUS:')
        
        # Check requisitions
        requisitions_with_entries = Requisition.objects.filter(
            status__in=['approved', 'checking', 'delivered'],
            total_cost__gt=0
        ).filter(accounting_entries__isnull=False).count()
        
        self.stdout.write(f'   - Requisitions with accounting entries: {requisitions_with_entries}/{requisitions}')
        
        # Check store sales
        sales_with_entries = StoreSale.objects.filter(
            total_amount__gt=0
        ).filter(accounting_entries__isnull=False).count()
        
        self.stdout.write(f'   - Store sales with accounting entries: {sales_with_entries}/{store_sales}')
        
        # Check manufacturing
        manufacturing_with_entries = ManufacturedProductInventory.objects.filter(
            accounting_entries__isnull=False
        ).count()
        
        self.stdout.write(f'   - Manufacturing with accounting entries: {manufacturing_with_entries}/{manufacturing}')
        
        # Show recent journal entries
        if journal_entries > 0:
            self.stdout.write('\n📝 RECENT JOURNAL ENTRIES:')
            for je in JournalEntry.objects.all()[:5]:
                self.stdout.write(f'   {je.entry_number}: {je.description[:50]}... ({je.entry_type})')
        
        # Summary
        self.stdout.write('\n✅ SUMMARY:')
        if journal_entries == 0:
            self.stdout.write('   🟡 No journal entries found - system is clean but empty')
        elif journal_entries > 0:
            self.stdout.write('   🟢 Accounting system has entries and appears to be synced')
        
        self.stdout.write('   🎯 Your accounting system is now clean and ready for new transactions!')
