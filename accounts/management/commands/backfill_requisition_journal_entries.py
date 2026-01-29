from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import ProductionExpense
from accounts.services import AccountingService
from accounts.signals import get_admin_user
from production.models import Requisition


class Command(BaseCommand):
    help = "Backfill missing accounting journal entries for production Requisitions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            type=str,
            default=None,
            help=(
                "Optional ISO date (YYYY-MM-DD). Only backfill requisitions "
                "created on or after this date."
            ),
        )
        parser.add_argument(
            "--status",
            type=str,
            nargs="*",
            default=["approved", "checking", "delivered"],
            help=(
                "Requisition statuses to include. Default: approved, checking, delivered. "
                "Use values from Requisition.STATUS_CHOICES."
            ),
        )

    def handle(self, *args, **options):
        from datetime import datetime

        since = options.get("since")
        statuses = options.get("status") or ["approved", "checking", "delivered"]

        qs = Requisition.objects.filter(status__in=statuses)

        if since:
            try:
                since_date = datetime.strptime(since, "%Y-%m-%d").date()
                qs = qs.filter(created_at__date__gte=since_date)
            except ValueError:
                self.stderr.write(
                    self.style.ERROR(
                        f"Invalid --since date format: {since}. Expected YYYY-MM-DD."
                    )
                )
                return

        admin_user = get_admin_user()
        if not admin_user:
            self.stderr.write(
                self.style.ERROR(
                    "No admin (superuser) found. Cannot create journal entries."
                )
            )
            return

        total = qs.count()
        created_count = 0

        self.stdout.write(
            self.style.NOTICE(
                f"Found {total} requisitions with status in {statuses} to inspect."
            )
        )

        with transaction.atomic():
            for req in qs.select_related("supplier"):
                # Skip if a ProductionExpense (and thus JE link) already exists
                if ProductionExpense.objects.filter(requisition=req).exists():
                    continue

                je = AccountingService.create_requisition_expense_journal_entry(
                    req, admin_user
                )
                if je is not None:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            "Created requisition JE {je_id} for Requisition {req_no} (ID: {req_id})".format(
                                je_id=je.id,
                                req_no=req.requisition_no,
                                req_id=req.id,
                            )
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                "Backfill complete. Created {created} new requisition journal entries "
                "out of {total} matching requisitions.".format(
                    created=created_count,
                    total=total,
                )
            )
        )
