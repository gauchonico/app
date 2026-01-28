from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import JournalEntry


class Command(BaseCommand):
    help = "Delete sales-related JournalEntries that have no JournalEntryLine rows (empty 0/0 entries)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show which entries would be deleted, without deleting them.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Sales-related JEs with no lines
        empty_sales_journal_entries = JournalEntry.objects.filter(
            entry_type="sales",
            entries__isnull=True,
        ).distinct()

        count = empty_sales_journal_entries.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No empty sales journal entries found."))
            return

        self.stdout.write(self.style.WARNING(f"Found {count} empty sales journal entries."))

        for je in empty_sales_journal_entries:
            self.stdout.write(
                f" - {je.entry_number or je.id}: date={je.date}, reference={je.reference!r}, description={je.description[:60]!r}"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run mode: no entries were deleted."))
            return

        with transaction.atomic():
            deleted_count, _ = empty_sales_journal_entries.delete()

        self.stdout.write(
            self.style.SUCCESS(f"Deleted {deleted_count} empty sales JournalEntry records (including dependents, if any).")
        )
