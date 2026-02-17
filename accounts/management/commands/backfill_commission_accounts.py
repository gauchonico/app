from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User
from accounts.models import CommissionExpense, ChartOfAccounts, JournalEntryLine
from POSMagicApp.signals import _ensure_staff_commission_account


class Command(BaseCommand):
    help = (
        'Backfill per-staff commission payable accounts and re-point existing '
        'CommissionExpense journal entry credit lines from 2110 to 2110-XXXX'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without writing to the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be saved\n'))

        parent_account = ChartOfAccounts.objects.filter(account_code='2110').first()
        if not parent_account:
            self.stdout.write(self.style.ERROR('Account 2110 (Commission Payable) not found. Aborting.'))
            return

        # ── Phase 1: ensure every staff member has a sub-account ──────────────
        self.stdout.write('Phase 1: Creating missing per-staff commission accounts...')
        from POSMagicApp.models import Staff

        # Build a set of account codes that will exist after phase 1.
        # In a real run these are written to the DB.
        # In a dry run we track them in memory so phase 2 can simulate correctly.
        will_exist_codes = set(
            ChartOfAccounts.objects.filter(
                account_code__startswith='2110-'
            ).values_list('account_code', flat=True)
        )

        created_count = 0
        staff_account_map = {}  # staff.pk → account_code, used by phase 2

        for staff in Staff.objects.all():
            account_code = f"2110-{staff.pk:04d}"
            staff_account_map[staff.pk] = account_code

            if account_code not in will_exist_codes:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ {'Would create' if dry_run else 'Creating'} "
                        f"{account_code} for {staff.first_name} {staff.last_name}"
                    )
                )
                if not dry_run:
                    _ensure_staff_commission_account(staff)
                else:
                    # Track it as "will exist" so phase 2 doesn't false-fail
                    will_exist_codes.add(account_code)
                created_count += 1
            else:
                self.stdout.write(
                    f"  · {account_code} already exists "
                    f"for {staff.first_name} {staff.last_name}"
                )

        self.stdout.write(
            f"\n  {created_count} accounts "
            f"{'would be ' if dry_run else ''}created.\n"
        )

        # ── Phase 2: re-point credit lines on existing CommissionExpense ───────
        self.stdout.write('Phase 2: Re-pointing journal entry credit lines to per-staff accounts...')

        updated_lines = 0
        skipped = 0
        errors = 0

        for expense in CommissionExpense.objects.select_related(
            'staff_commission__staff',
            'product_commission__staff',
            'journal_entry',
        ).all():
            # Resolve the staff member
            if expense.staff_commission:
                staff = expense.staff_commission.staff
            elif expense.product_commission:
                staff = expense.product_commission.staff
            else:
                # Monthly commission payment — different flow, skip
                skipped += 1
                continue

            staff_account_code = staff_account_map.get(staff.pk, f"2110-{staff.pk:04d}")

            # In dry run: check our in-memory set; in real run: check the DB
            if dry_run:
                account_exists = staff_account_code in will_exist_codes
                staff_account = None  # not needed for dry run reporting
            else:
                try:
                    staff_account = ChartOfAccounts.objects.get(
                        account_code=staff_account_code
                    )
                    account_exists = True
                except ChartOfAccounts.DoesNotExist:
                    account_exists = False
                    staff_account = None

            if not account_exists:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Account {staff_account_code} missing for "
                        f"{staff.first_name} — run phase 1 first"
                    )
                )
                errors += 1
                continue

            # Find the credit line still pointing to the shared 2110 account
            credit_line = JournalEntryLine.objects.filter(
                journal_entry=expense.journal_entry,
                account=parent_account,
                entry_type='credit'
            ).first()

            if not credit_line:
                # Already re-pointed or never was on 2110
                skipped += 1
                continue

            self.stdout.write(
                f"  → JE {expense.journal_entry.entry_number}: "
                f"2110 → {staff_account_code} "
                f"({staff.first_name} {staff.last_name}) "
                f"amount={credit_line.amount}"
            )

            if not dry_run:
                with transaction.atomic():
                    credit_line.account = staff_account
                    credit_line.description = (
                        f"Commission payable to "
                        f"{staff.first_name} {staff.last_name}"
                    )
                    credit_line.save(update_fields=['account', 'description'])

                    # Populate the staff FK on CommissionExpense
                    expense.staff = staff
                    expense.save(update_fields=['staff'])

            updated_lines += 1

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write('\n' + '─' * 50)
        action = 'Would be re-pointed' if dry_run else 'Re-pointed'
        self.stdout.write(self.style.SUCCESS(
            f"Done.\n"
            f"  {action}              : {updated_lines} credit lines\n"
            f"  Skipped (already correct or monthly) : {skipped}\n"
            f"  Errors                               : {errors}"
        ))
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '\nDRY RUN — re-run without --dry-run to apply.'
                )
            )