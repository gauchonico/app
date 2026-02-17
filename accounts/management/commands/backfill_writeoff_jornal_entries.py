from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import JournalEntry
from accounts.services import AccountingService
from production.models import IncidentWriteOff, StoreWriteOff


class Command(BaseCommand):
    help = (
        'Backfill journal entries for approved IncidentWriteOff '
        'and StoreWriteOff records that are missing accounting entries.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be posted without writing anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be saved\n'))

        system_user = User.objects.filter(is_superuser=True).first()

        # ── IncidentWriteOff — Raw Materials ──────────────────────────────────
        self.stdout.write('── Raw Material Write-offs (IncidentWriteOff) ──')

        missing_rm = [
            w for w in IncidentWriteOff.objects.filter(
                status='approved'           # only approved write-offs
            ).select_related(
                'raw_material',
                'written_off_by',           # correct field name
            ).all()
            if not JournalEntry.objects.filter(
                reference=f"RM-WO-{w.id}"
            ).exists()
        ]

        self.stdout.write(f"Found {len(missing_rm)} missing journal entries\n")

        rm_success = 0
        rm_errors = 0

        for w in missing_rm:
            user = w.written_off_by or system_user  # correct field name
            self.stdout.write(
                f"  → RM-WO-{w.id} | {w.raw_material.name} | "
                f"qty: {w.quantity} | date: {w.date}"
            )
            if not dry_run:
                result = AccountingService.create_raw_material_writeoff_journal_entry(
                    w, user
                )
                if result:
                    self.stdout.write(
                        self.style.SUCCESS(f"       ✓ Posted as {result.entry_number}")
                    )
                    rm_success += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"       ✗ Failed — check unit cost / price history "
                            f"for '{w.raw_material.name}'"
                        )
                    )
                    rm_errors += 1
            else:
                self.stdout.write(self.style.SUCCESS("       ✓ Would post"))
                rm_success += 1

        # ── StoreWriteOff — Finished Products ────────────────────────────────
        self.stdout.write('\n── Store Product Write-offs (StoreWriteOff) ──')

        missing_store = [
            w for w in StoreWriteOff.objects.filter(
                approved=True               # only approved write-offs
            ).select_related(
                'main_store_product__product__product',
                'approved_by',
            ).all()
            if not JournalEntry.objects.filter(
                reference=f"StoreWO-{w.id}"
            ).exists()
        ]

        self.stdout.write(f"Found {len(missing_store)} missing journal entries\n")

        store_success = 0
        store_errors = 0

        for w in missing_store:
            user = w.approved_by or system_user
            unit_cost = w.main_store_product.unit_cost or 0
            total = unit_cost * w.quantity

            self.stdout.write(
                f"  → StoreWO-{w.id} | batch: {w.batch_number} | "
                f"qty: {w.quantity} | unit_cost: {unit_cost} | "
                f"total: {total} | reason: {w.get_reason_display()}"
            )
            if not dry_run:
                result = AccountingService.create_store_writeoff_journal_entry(
                    w, user
                )
                if result:
                    self.stdout.write(
                        self.style.SUCCESS(f"       ✓ Posted as {result.entry_number}")
                    )
                    store_success += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"       ✗ Failed — check unit_cost for "
                            f"batch {w.batch_number}"
                        )
                    )
                    store_errors += 1
            else:
                self.stdout.write(self.style.SUCCESS("       ✓ Would post"))
                store_success += 1

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write('\n' + '─' * 50)
        action = 'Would post' if dry_run else 'Posted'
        self.stdout.write(self.style.SUCCESS(
            f"Done.\n"
            f"  Raw material write-offs  — {action}: {rm_success}  "
            f"Errors: {rm_errors}\n"
            f"  Store product write-offs — {action}: {store_success}  "
            f"Errors: {store_errors}"
        ))
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '\nDRY RUN — re-run without --dry-run to apply.'
                )
            )