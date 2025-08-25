from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import JournalEntry

class Command(BaseCommand):
    help = 'Clean up orphaned journal entries that reference deleted production records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation',
        )
        parser.add_argument(
            '--keep-manual',
            action='store_true',
            help='Keep manual entries (like wages) even if orphaned',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        keep_manual = options['keep_manual']
        
        self.stdout.write('🧹 CLEANING UP ORPHANED JOURNAL ENTRIES')
        self.stdout.write('=' * 50)
        
        # Find orphaned entries
        orphaned_entries = []
        for je in JournalEntry.objects.all():
            if not je.has_related_records():
                if keep_manual and je.entry_type == 'manual':
                    continue
                orphaned_entries.append(je)
        
        if not orphaned_entries:
            self.stdout.write('✅ No orphaned journal entries found!')
            return
        
        # Group by entry type
        by_type = {}
        for je in orphaned_entries:
            entry_type = je.entry_type
            if entry_type not in by_type:
                by_type[entry_type] = []
            by_type[entry_type].append(je)
        
        self.stdout.write(f'\n🔴 Found {len(orphaned_entries)} orphaned journal entries:')
        for entry_type, entries in by_type.items():
            self.stdout.write(f'   - {entry_type}: {len(entries)} entries')
        
        # Show sample entries
        self.stdout.write('\n📝 SAMPLE ORPHANED ENTRIES:')
        for je in orphaned_entries[:10]:
            self.stdout.write(f'   {je.entry_number}: {je.description[:60]}... ({je.entry_type})')
        
        if len(orphaned_entries) > 10:
            self.stdout.write(f'   ... and {len(orphaned_entries) - 10} more')
        
        if dry_run:
            self.stdout.write('\n🔍 DRY RUN - No entries will be deleted')
            return
        
        if not force:
            self.stdout.write('\n⚠️  WARNING: This will permanently delete these journal entries!')
            self.stdout.write('   These entries reference production records that no longer exist.')
            confirm = input('\n❓ Do you want to delete these orphaned entries? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('❌ Operation cancelled.')
                return
        
        # Delete orphaned entries
        with transaction.atomic():
            deleted_count = 0
            for entry_type, entries in by_type.items():
                for je in entries:
                    je.delete()
                    deleted_count += 1
                    self.stdout.write(f'🗑️  Deleted {je.entry_number} ({entry_type})')
            
            self.stdout.write(f'\n✅ Successfully deleted {deleted_count} orphaned journal entries')
            
            # Show remaining entries
            remaining = JournalEntry.objects.count()
            self.stdout.write(f'📊 Remaining journal entries: {remaining}')
