from django.core.management.base import BaseCommand
from django.db.models import Count
from accounts.models import JournalEntry

class Command(BaseCommand):
    help = 'Analyze existing journal entries'

    def handle(self, *args, **options):
        self.stdout.write('📊 JOURNAL ENTRIES ANALYSIS')
        self.stdout.write('=' * 50)
        
        # Count by entry type
        self.stdout.write('\n📋 BY ENTRY TYPE:')
        for entry_type, count in JournalEntry.objects.values('entry_type').annotate(count=Count('id')).order_by('-count'):
            self.stdout.write(f'   {entry_type}: {count}')
        
        # Show sample entries
        self.stdout.write('\n📝 SAMPLE ENTRIES:')
        for je in JournalEntry.objects.all()[:10]:
            self.stdout.write(f'   {je.entry_number}: {je.description[:60]}... ({je.entry_type})')
        
        # Check for related records
        self.stdout.write('\n🔗 RELATED RECORDS:')
        total_with_relations = 0
        for je in JournalEntry.objects.all():
            if je.has_related_records():
                total_with_relations += 1
        
        self.stdout.write(f'   Journal entries with related records: {total_with_relations}')
        self.stdout.write(f'   Journal entries without related records: {JournalEntry.objects.count() - total_with_relations}')
        
        # Show entries without related records
        self.stdout.write('\n🔴 ENTRIES WITHOUT RELATED RECORDS:')
        for je in JournalEntry.objects.all():
            if not je.has_related_records():
                self.stdout.write(f'   {je.entry_number}: {je.description[:60]}... ({je.entry_type})')
