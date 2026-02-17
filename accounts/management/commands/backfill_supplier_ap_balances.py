from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone

from accounts.models import (
    ChartOfAccounts,
    JournalEntry,
    JournalEntryLine,
    ProductionExpense,
    PaymentRecord,
)
from accounts.signals import get_admin_user
from production.models import Supplier


class Command(BaseCommand):
    help = (
        "Backfill supplier-specific Accounts Payable balances by reclassifying "
        "legacy amounts from the 2000 control account into each supplier's "
        "payables sub-account."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--as-of",
            type=str,
            default=None,
            help=(
                "Optional ISO date (YYYY-MM-DD). Only journal entry lines on or "
                "before this date will be considered. Defaults to today."
            ),
        )
        parser.add_argument(
            "--journal-date",
            type=str,
            default=None,
            help=(
                "Optional ISO date (YYYY-MM-DD) for the reclassification journal "
                "entry. Defaults to the --as-of date (or today)."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show computed per-supplier balances without creating any journal entries.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Apply changes without interactive confirmation. "
                "Ignored when --dry-run is set."
            ),
        )

    def handle(self, *args, **options):
        as_of_str = options.get("as_of")
        journal_date_str = options.get("journal_date")
        dry_run = options.get("dry_run")
        force = options.get("force")

        # Resolve dates
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

        try:
            if journal_date_str:
                journal_date = datetime.strptime(journal_date_str, "%Y-%m-%d").date()
            else:
                journal_date = as_of_date
        except ValueError:
            self.stderr.write(
                self.style.ERROR(
                    f"Invalid --journal-date format: {journal_date_str}. Expected YYYY-MM-DD."
                )
            )
            return

        self.stdout.write(self.style.MIGRATE_HEADING("Backfilling supplier AP balances from 2000"))
        self.stdout.write(f"As-of date: {as_of_date}")
        self.stdout.write(f"Journal date: {journal_date}\n")

        # Ensure control account 2000 exists
        control_account, _ = ChartOfAccounts.objects.get_or_create(
            account_code="2000",
            defaults={
                "account_name": "Accounts Payable - Suppliers",
                "account_type": "liability",
                "account_category": "current_liability",
                "is_active": True,
            },
        )

        # Fetch all posted JE lines hitting 2000 on or before as_of_date
        lines_qs = (
            JournalEntryLine.objects.filter(
                account=control_account,
                journal_entry__is_posted=True,
                journal_entry__date__lte=as_of_date,
            )
            .select_related("journal_entry")
            .order_by("journal_entry__date", "journal_entry_id")
        )

        if not lines_qs.exists():
            self.stdout.write(self.style.WARNING("No journal entry lines found on 2000 up to the as-of date."))
            return

        # Aggregate total 2000 balance as-of date
        totals = lines_qs.aggregate(
            debit=Sum("amount", filter=Q(entry_type="debit")),
            credit=Sum("amount", filter=Q(entry_type="credit")),
        )
        total_debit = totals["debit"] or Decimal("0.00")
        total_credit = totals["credit"] or Decimal("0.00")
        control_balance = total_credit - total_debit  # Liability: credit minus debit

        self.stdout.write("Current 2000 balance (as-of filter applied):")
        self.stdout.write(f"  Total debits : {total_debit}")
        self.stdout.write(f"  Total credits: {total_credit}")
        self.stdout.write(self.style.NOTICE(f"  Net (credit - debit): {control_balance}\n"))

        # Build mapping from journal entry -> supplier using integration models
        je_to_supplier_id = {}

        # 1) Requisition expense JEs (accrual side)
        for row in (
            ProductionExpense.objects.select_related("requisition__supplier")
            .values("journal_entry_id", "requisition__supplier_id")
        ):
            je_id = row["journal_entry_id"]
            supplier_id = row["requisition__supplier_id"]
            if je_id and supplier_id and je_id not in je_to_supplier_id:
                je_to_supplier_id[je_id] = supplier_id

        # 2) Payment voucher JEs (settlement side)
        for row in (
            PaymentRecord.objects.filter(payment_voucher__isnull=False)
            .select_related("payment_voucher__lpo__requisition__supplier")
            .values("journal_entry_id", "payment_voucher__lpo__requisition__supplier_id")
        ):
            je_id = row["journal_entry_id"]
            supplier_id = row["payment_voucher__lpo__requisition__supplier_id"]
            if je_id and supplier_id and je_id not in je_to_supplier_id:
                je_to_supplier_id[je_id] = supplier_id

        from collections import defaultdict

        supplier_movements = defaultdict(lambda: {"debit": Decimal("0.00"), "credit": Decimal("0.00")})
        unmapped_lines = []

        for line in lines_qs:
            supplier_id = je_to_supplier_id.get(line.journal_entry_id)
            if not supplier_id:
                unmapped_lines.append(line)
                continue

            if line.entry_type == "debit":
                supplier_movements[supplier_id]["debit"] += line.amount
            elif line.entry_type == "credit":
                supplier_movements[supplier_id]["credit"] += line.amount

        if not supplier_movements:
            self.stdout.write(
                self.style.WARNING(
                    "No 2000 movements could be mapped to suppliers via ProductionExpense/PaymentRecord."
                )
            )
            if unmapped_lines:
                self.stdout.write(
                    self.style.WARNING(
                        f"Unmapped 2000 lines: {len(unmapped_lines)} (these remain on the control account)."
                    )
                )
            return

        # Load suppliers in bulk for reporting and account lookup
        suppliers = Supplier.objects.in_bulk(supplier_movements.keys())

        self.stdout.write("Per-supplier 2000 movements (credit - debit gives net AP balance):")
        self.stdout.write("=" * 72)

        mapped_total_debit = Decimal("0.00")
        mapped_total_credit = Decimal("0.00")
        supplier_balances = {}

        for supplier_id, mov in sorted(
            supplier_movements.items(),
            key=lambda kv: suppliers.get(kv[0]).name if suppliers.get(kv[0]) else "",
        ):
            supplier = suppliers.get(supplier_id)
            if not supplier:
                continue

            debit = mov["debit"]
            credit = mov["credit"]
            balance = credit - debit  # liability-style

            mapped_total_debit += debit
            mapped_total_credit += credit
            supplier_balances[supplier_id] = balance

            self.stdout.write(
                f"- {supplier.name}: debit={debit} credit={credit} net(credit-debit)={balance}"
            )

        mapped_net = mapped_total_credit - mapped_total_debit

        self.stdout.write("\nSUMMARY OF MAPPED 2000 MOVEMENTS:")
        self.stdout.write(f"  Mapped debits : {mapped_total_debit}")
        self.stdout.write(f"  Mapped credits: {mapped_total_credit}")
        self.stdout.write(f"  Mapped net    : {mapped_net}")

        diff = control_balance - mapped_net
        self.stdout.write(
            self.style.NOTICE(
                f"  Difference vs 2000 balance: {diff} (unmapped JEs, manual entries, or rounding)"
            )
        )

        if unmapped_lines:
            self.stdout.write(
                self.style.WARNING(
                    f"Unmapped 2000 lines (no supplier link found): {len(unmapped_lines)}. "
                    "These will remain on 2000 and are NOT reclassified by this command."
                )
            )

            # Show a short preview of which journal entries are unmapped so the
            # user can inspect them in the admin or via other tools.
            self.stdout.write("  Example unmapped journal entries (first 10):")
            for line in unmapped_lines[:10]:
                je = line.journal_entry
                self.stdout.write(
                    f"    JE {je.id} ({je.entry_number}) on {je.date}: "
                    f"{je.description[:80]}... amount={line.amount} type={line.entry_type}"
                )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no journal entries were created."))
            return

        # Confirm before applying changes unless forced
        if not force:
            confirm = input(
                "\nThis will create a reclassification journal entry to move mapped "
                "balances from 2000 into supplier-specific AP accounts. Continue? (yes/no): "
            )
            if confirm.lower().strip() != "yes":
                self.stdout.write(self.style.ERROR("Operation cancelled by user."))
                return

        admin_user = get_admin_user()
        if not admin_user:
            self.stderr.write(
                self.style.ERROR("No admin (superuser) found. Cannot create journal entries.")
            )
            return

        with transaction.atomic():
            # Create a single reclassification JE
            je = JournalEntry.objects.create(
                date=journal_date,
                reference=f"AP-backfill-{journal_date.isoformat()}",
                description=(
                    "Reclassify legacy Accounts Payable (2000) balances into "
                    "supplier-specific payables accounts"
                ),
                entry_type="system",
                created_by=admin_user,
                is_posted=True,
                posted_at=timezone.now(),
            )

            total_reclass_debits = Decimal("0.00")
            total_reclass_credits = Decimal("0.00")

            # For each supplier with a non-zero mapped balance, move that
            # balance off 2000 into the supplier's payables_account.
            for supplier_id, balance in supplier_balances.items():
                if balance == 0:
                    continue

                supplier = suppliers.get(supplier_id)
                if not supplier:
                    continue

                ap_account = supplier.payables_account
                if not ap_account:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping supplier {supplier.name}: no payables_account configured."
                        )
                    )
                    continue

                amount = abs(balance)

                if balance > 0:
                    # We owe the supplier (credit balance). Move from 2000 -> supplier AP:
                    #   DR 2000
                    #   CR supplier.payables_account
                    JournalEntryLine.objects.create(
                        journal_entry=je,
                        account=control_account,
                        entry_type="debit",
                        amount=amount,
                        description=f"Reclass AP balance for {supplier.name}",
                    )
                    JournalEntryLine.objects.create(
                        journal_entry=je,
                        account=ap_account,
                        entry_type="credit",
                        amount=amount,
                        description=f"Reclass AP balance for {supplier.name}",
                    )
                    total_reclass_debits += amount
                    total_reclass_credits += amount
                else:
                    # Net debit balance on 2000 for this supplier (e.g. overpayment).
                    # Move from supplier AP -> 2000:
                    #   DR supplier.payables_account
                    #   CR 2000
                    JournalEntryLine.objects.create(
                        journal_entry=je,
                        account=ap_account,
                        entry_type="debit",
                        amount=amount,
                        description=f"Reclass AP (debit) balance for {supplier.name}",
                    )
                    JournalEntryLine.objects.create(
                        journal_entry=je,
                        account=control_account,
                        entry_type="credit",
                        amount=amount,
                        description=f"Reclass AP (debit) balance for {supplier.name}",
                    )
                    total_reclass_debits += amount
                    total_reclass_credits += amount

            # Basic sanity check that JE is balanced
            if total_reclass_debits != total_reclass_credits:
                raise ValueError(
                    "Reclassification journal entry is not balanced: "
                    f"debits={total_reclass_debits}, credits={total_reclass_credits}"
                )

            self.stdout.write("\nCreated reclassification journal entry:")
            self.stdout.write(
                self.style.SUCCESS(
                    f"  JE ID: {je.id}, number: {je.entry_number}, "
                    f"debits={total_reclass_debits}, credits={total_reclass_credits}"
                )
            )
            self.stdout.write(
                "Note: Any unmapped 2000 lines remain on the 2000 control account "
                "and can be reviewed separately."
            )
