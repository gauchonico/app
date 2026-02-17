from decimal import Decimal
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone

from accounts.models import ChartOfAccounts, JournalEntry, JournalEntryLine
from accounts.signals import get_admin_user


class Command(BaseCommand):
    help = (
        "Reclass legacy accessory Accounts Payable from 2000 to 2001029. "
        "Designed to move the historical accessory requisition balance that "
        "currently sits on 2000 into the dedicated 'Account Payable Accessories' "
        "account. Safe to run once."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--as-of",
            type=str,
            default=None,
            help=(
                "Optional ISO date (YYYY-MM-DD). Only 2000 lines on or before this "
                "date will be considered. Defaults to today."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be reclassified without creating a journal entry.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Proceed even if the detected amount differs from the expected "
                "625,000.00. Ignored when --dry-run is set."
            ),
        )

    def handle(self, *args, **options):
        as_of_str = options.get("as_of")
        dry_run = options.get("dry_run")
        force = options.get("force")

        # Resolve as-of date
        try:
            if as_of_str:
                as_of_date = datetime.strptime(as_of_str, "%Y-%m-%d").date()
            else:
                as_of_date = timezone.now().date()
        except ValueError:
            self.stderr.write(
                self.style.ERROR(
                    f"Invalid --as-of date format: {as_of_str}. Expected YYYY-MM-DD."
                )
            )
            return

        self.stdout.write(self.style.MIGRATE_HEADING("Reclass accessory AP from 2000 to 2001029"))
        self.stdout.write(f"As-of date: {as_of_date}\n")

        # Ensure control account 2000 exists
        try:
            control_account = ChartOfAccounts.objects.get(account_code="2000")
        except ChartOfAccounts.DoesNotExist:
            self.stderr.write(self.style.ERROR("Account 2000 (Accounts Payable - Suppliers) not found."))
            return

        # Ensure accessory AP account 2001029 exists
        try:
            accessory_ap_account = ChartOfAccounts.objects.get(account_code="2001029")
        except ChartOfAccounts.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(
                    "Account 2001029 (Account Payable Accessories) not found. "
                    "Please create it first."
                )
            )
            return

        # Guard: do not run twice – check for existing reclass JE
        if JournalEntry.objects.filter(reference="AP-accessory-2001029").exists():
            self.stdout.write(
                self.style.WARNING(
                    "A journal entry with reference 'AP-accessory-2001029' already "
                    "exists. Aborting to avoid double reclassification."
                )
            )
            return

        # Find 2000 lines that appear to be from accessory requisition JEs
        # We match on description containing 'Accessory requisition' so that
        # we specifically target the main-store accessory JE(s).
        lines_qs = (
            JournalEntryLine.objects.filter(
                account=control_account,
                entry_type="credit",
                journal_entry__date__lte=as_of_date,
                journal_entry__description__icontains="Accessory requisition",
            )
            .select_related("journal_entry")
            .order_by("journal_entry__date", "journal_entry_id")
        )

        if not lines_qs.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No 2000 credit lines matching accessory requisitions were found "
                    "up to the as-of date. Nothing to reclass."
                )
            )
            return

        total_amount = (
            lines_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        )

        self.stdout.write("Accessory-related 2000 credit lines to be reclassified:")
        for line in lines_qs:
            je = line.journal_entry
            self.stdout.write(
                f"  JE {je.id} ({je.entry_number}) on {je.date}: "
                f"{je.description[:80]}... amount={line.amount}"
            )

        self.stdout.write("\nSUMMARY:")
        self.stdout.write(f"  Total 2000 accessory credit to reclass: {total_amount}")

        expected = Decimal("625000.00")
        if total_amount != expected:
            self.stdout.write(
                self.style.WARNING(
                    f"  NOTE: Detected total {total_amount} differs from expected "
                    f"{expected}."
                )
            )

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        "Dry run only – no changes applied. Review the lines above "
                        "before running without --dry-run."
                    )
                )
                return

            if not force:
                self.stdout.write(
                    self.style.ERROR(
                        "Aborting because detected amount does not equal 625,000.00 "
                        "and --force was not provided."
                    )
                )
                return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no journal entry will be created."))
            return

        admin_user = get_admin_user()
        if not admin_user:
            self.stderr.write(
                self.style.ERROR(
                    "No admin (superuser) found. Cannot create reclassification journal entry."
                )
            )
            return

        # Confirm with user before making changes (unless running non-interactively)
        confirm = input(
            "\nThis will create a journal entry to move the accessory AP balance "
            "from 2000 to 2001029. Continue? (yes/no): "
        )
        if confirm.lower().strip() != "yes":
            self.stdout.write(self.style.ERROR("Operation cancelled by user."))
            return

        with transaction.atomic():
            je = JournalEntry.objects.create(
                date=as_of_date,
                reference="AP-accessory-2001029",
                description=(
                    "Reclass legacy accessory Accounts Payable from 2000 control "
                    "account to 2001029 Account Payable Accessories"
                ),
                entry_type="system",
                created_by=admin_user,
                is_posted=True,
                posted_at=timezone.now(),
            )

            # DR 2000
            JournalEntryLine.objects.create(
                journal_entry=je,
                account=control_account,
                entry_type="debit",
                amount=total_amount,
                description="Reclass accessory AP from 2000 to 2001029",
            )

            # CR 2001029
            JournalEntryLine.objects.create(
                journal_entry=je,
                account=accessory_ap_account,
                entry_type="credit",
                amount=total_amount,
                description="Reclass accessory AP from 2000 to 2001029",
            )

            self.stdout.write("\nCreated reclassification journal entry:")
            self.stdout.write(
                self.style.SUCCESS(
                    f"  JE ID: {je.id}, number: {je.entry_number}, "
                    f"amount moved: {total_amount}"
                )
            )
            self.stdout.write(
                "You can now rerun 'backfill_supplier_ap_balances --dry-run' to "
                "confirm that the remaining 2000 balance matches mapped supplier "
                "AP amounts."
            )
