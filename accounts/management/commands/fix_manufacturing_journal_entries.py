from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal

from accounts.models import JournalEntry, JournalEntryLine, ManufacturingRecord, ChartOfAccounts, Department
from accounts.signals import get_admin_user
from production.models import ManufactureProduct, ManufacturedProductInventory


class Command(BaseCommand):
    help = (
        "Reverse and correct mis-valued manufacturing journal entries based on "
        "ManufactureProduct.total_production_cost."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            type=str,
            default=None,
            help=(
                "Optional ISO date (YYYY-MM-DD). Only inspect manufactured batches "
                "on or after this date."
            ),
        )
        parser.add_argument(
            "--batch",
            type=str,
            nargs="*",
            default=None,
            help=(
                "Optional specific batch_number values to restrict fixing to. "
                "If omitted, all batches are considered."
            ),
        )
        parser.add_argument(
            "--tolerance",
            type=str,
            default="0.01",
            help=(
                "Amount difference tolerance (in UGX) within which an existing JE is "
                "considered correct. Default: 0.01."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without creating any new journal entries.",
        )

    def handle(self, *args, **options):
        from datetime import datetime

        since = options.get("since")
        batches = options.get("batch")
        tolerance = Decimal(options.get("tolerance") or "0.01")
        dry_run = options.get("dry_run", False)

        # Base queryset: include all batches; we will later check
        # total_production_cost per batch and skip those that are not
        # populated, emitting a helpful warning instead of silently
        # ignoring them.
        qs = ManufactureProduct.objects.all()

        # If specific batches are provided, normalise them so you can pass either
        # raw batch_numbers (e.g. "FD0-0825-27-5058") or full JE refs
        # (e.g. "MFG-FD0-0825-27-5058"). We always filter on the underlying
        # ManufactureProduct.batch_number field, which does NOT include the
        # "MFG-" prefix.
        if batches:
            normalised_batches = []
            for b in batches:
                b = (b or "").strip()
                if not b:
                    continue
                if b.upper().startswith("MFG-"):
                    b = b[4:]
                normalised_batches.append(b)

            if not normalised_batches:
                self.stdout.write(
                    self.style.WARNING(
                        "No usable batch identifiers were provided after normalisation; "
                        "nothing to do."
                    )
                )
                return

            qs = qs.filter(batch_number__in=normalised_batches)

        if since:
            try:
                since_date = datetime.strptime(since, "%Y-%m-%d").date()
                qs = qs.filter(manufactured_at__date__gte=since_date)
            except ValueError:
                self.stderr.write(
                    self.style.ERROR(
                        f"Invalid --since date format: {since}. Expected YYYY-MM-DD."
                    )
                )
                return

        if batches:
            qs = qs.filter(batch_number__in=batches)

        total_batches = qs.count()
        if total_batches == 0:
            self.stdout.write(self.style.WARNING("No ManufactureProduct records matched the criteria."))
            return

        admin_user = get_admin_user()
        if not admin_user:
            self.stderr.write(
                self.style.ERROR(
                    "No admin (superuser) found. Cannot create journal entries."
                )
            )
            return

        fixed_count = 0
        created_new_count = 0

        self.stdout.write(
            self.style.NOTICE(
                f"Inspecting {total_batches} manufactured batches for mis-valued JEs."
            )
        )

        # Pre-fetch commonly used accounts/dept
        inventory_account = ChartOfAccounts.objects.filter(account_code="1210").first()
        raw_materials_account = ChartOfAccounts.objects.filter(account_code="5100").first()
        prod_dept = Department.objects.filter(code="PROD").first()

        if not inventory_account or not raw_materials_account:
            self.stderr.write(
                self.style.ERROR(
                    "Required accounts 1210 (Finished Goods) and 5100 (Raw Materials) "
                    "must exist in ChartOfAccounts before running this command."
                )
            )
            return

        with transaction.atomic():
            for mp in qs.select_related("product"):
                desired_cost = mp.total_production_cost or Decimal("0.00")
                if desired_cost <= 0:
                    # Let the user know this batch needs its total_production_cost
                    # set (via the manufacturing cost sheet) before it can be
                    # corrected.
                    msg = (
                        "Batch {batch} has no positive total_production_cost; "
                        "skipping. Update the manufacturing cost sheet for this "
                        "batch first."
                    ).format(batch=mp.batch_number)
                    if dry_run:
                        self.stdout.write(self.style.WARNING(f"[DRY-RUN] {msg}"))
                    else:
                        self.stdout.write(self.style.WARNING(msg))
                    continue

                ref = f"MFG-{mp.batch_number}"
                je = JournalEntry.objects.filter(reference=ref).first()

                if not je:
                    # No existing JE — optionally create a fresh correct one
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(
                                f"[DRY-RUN] Would create NEW manufacturing JE for batch "
                                f"{mp.batch_number} with cost {desired_cost:,.2f}."
                            )
                        )
                        created_new_count += 1
                        continue

                    new_je = self._create_correct_manufacturing_je(
                        mp,
                        desired_cost,
                        inventory_account,
                        raw_materials_account,
                        prod_dept,
                        admin_user,
                    )
                    created_new_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created new manufacturing JE {new_je.entry_number or new_je.id} "
                            f"for batch {mp.batch_number} at {desired_cost:,.2f}."
                        )
                    )
                    continue

                existing_debit = (
                    je.entries.filter(entry_type="debit").aggregate(total=Sum("amount"))["total"]
                    or Decimal("0.00")
                )

                diff = existing_debit - desired_cost
                if diff.copy_abs() <= tolerance:
                    # Within tolerance; treat as already correct
                    continue

                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[DRY-RUN] Batch {mp.batch_number}: existing JE (ref {ref}) "
                            f"debits {existing_debit:,.2f}, desired {desired_cost:,.2f}, "
                            f"difference {diff:,.2f}. Would reverse and repost."
                        )
                    )
                    fixed_count += 1
                    continue

                # 1) Post a reversing JE for the existing one
                rev_je = self._create_reversing_entry(je, admin_user, prod_dept)

                # 2) Post a new correct JE at desired cost
                corr_je = self._create_correct_manufacturing_je(
                    mp,
                    desired_cost,
                    inventory_account,
                    raw_materials_account,
                    prod_dept,
                    admin_user,
                    reference_suffix="-CORR",
                )

                fixed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        "Fixed manufacturing JE for batch {batch}: "
                        "reversed {old_ref} (JE {old_no}) and posted corrected JE {new_no}.".format(
                            batch=mp.batch_number,
                            old_ref=je.reference,
                            old_no=je.entry_number or je.id,
                            new_no=corr_je.entry_number or corr_je.id,
                        )
                    )
                )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"DRY-RUN complete. Would fix {fixed_count} mis-valued JEs and "
                    f"create {created_new_count} new JEs for batches with no entry."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Completed. Fixed {fixed_count} mis-valued JEs and created "
                    f"{created_new_count} new JEs for batches with no entry."
                )
            )

    def _create_reversing_entry(self, original_je, admin_user, prod_dept):
        """Create a full reversing entry for the given JournalEntry."""
        rev_ref = f"REV-{original_je.reference or original_je.id}"

        rev_je = JournalEntry.objects.create(
            date=original_je.date,
            reference=rev_ref,
            description=(
                f"Reversal of manufacturing JE {original_je.entry_number or original_je.id} "
                f"({original_je.reference})"
            ),
            entry_type="production",
            department=prod_dept or original_je.department,
            created_by=admin_user,
            is_posted=True,
            posted_at=original_je.posted_at,
        )

        # Reverse each line (swap debit/credit)
        for line in original_je.entries.all():
            JournalEntryLine.objects.create(
                journal_entry=rev_je,
                account=line.account,
                entry_type="credit" if line.entry_type == "debit" else "debit",
                amount=line.amount,
                description=f"Reversal of: {line.description}",
            )

        return rev_je

    def _create_correct_manufacturing_je(
        self,
        mp,
        total_cost,
        inventory_account,
        raw_materials_account,
        prod_dept,
        admin_user,
        reference_suffix="",
    ):
        """Create a new manufacturing JE at the correct total_cost for a batch."""
        ref = f"MFG-{mp.batch_number}{reference_suffix}"

        je = JournalEntry.objects.create(
            date=mp.manufactured_at.date(),
            reference=ref,
            description=(
                f"Corrected manufacturing cost for {mp.quantity} units of "
                f"{mp.product.product_name} (batch {mp.batch_number})"
            ),
            entry_type="production",
            department=prod_dept,
            created_by=admin_user,
            is_posted=True,
            posted_at=mp.manufactured_at,
        )

        # DR Finished Goods Inventory
        JournalEntryLine.objects.create(
            journal_entry=je,
            account=inventory_account,
            entry_type="debit",
            amount=total_cost,
            description=(
                "Finished goods inventory (corrected cost) - "
                f"{mp.product.product_name}"
            ),
        )

        # CR Raw Materials Inventory
        JournalEntryLine.objects.create(
            journal_entry=je,
            account=raw_materials_account,
            entry_type="credit",
            amount=total_cost,
            description=f"Raw materials consumed (corrected cost) for {mp.batch_number}",
        )

        # Optionally link to ManufacturedProductInventory via ManufacturingRecord
        inventory = ManufacturedProductInventory.objects.filter(
            product=mp.product,
            batch_number=mp.batch_number,
        ).first()

        if inventory is not None:
            ManufacturingRecord.objects.get_or_create(
                manufacture_product=inventory,
                journal_entry=je,
                defaults={"amount": total_cost},
            )

        return je
