from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import JournalEntry
from accounts.services import AccountingService
from accounts.signals import get_admin_user
from production.models import MainStoreAccessoryRequisition


class Command(BaseCommand):
    help = "Backfill missing accounting journal entries for delivered main-store accessory requisitions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            type=str,
            default=None,
            help=(
                "Optional ISO date (YYYY-MM-DD). Only backfill accessory requisitions "
                "created on or after this date."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Do not create any journal entries; just list which "
                "MainStoreAccessoryRequisitions would get JEs."
            ),
        )

    def handle(self, *args, **options):
        from datetime import datetime

        since = options.get("since")
        dry_run = options.get("dry_run", False)

        qs = MainStoreAccessoryRequisition.objects.filter(status="delivered")

        if since:
            try:
                since_date = datetime.strptime(since, "%Y-%m-%d").date()
                qs = qs.filter(request_date__date__gte=since_date)
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
                f"Found {total} delivered MainStoreAccessoryRequisitions to inspect."
            )
        )

        with transaction.atomic():
            for req in qs.select_related("requested_by"):
                ref = f"AccReq-{req.accessory_req_number}"
                if JournalEntry.objects.filter(reference=ref).exists():
                    continue

                if dry_run:
                    created_count += 1
                    self.stdout.write(
                        self.style.NOTICE(
                            "[DRY-RUN] Would create accessory requisition JE for AccReq {num} (ID: {req_id})".format(
                                num=req.accessory_req_number,
                                req_id=req.id,
                            )
                        )
                    )
                    continue

                je = AccountingService.create_accessory_requisition_journal_entry(
                    req, admin_user
                )
                if je is not None:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            "Created accessory requisition JE {je_id} for AccReq {num} (ID: {req_id})".format(
                                je_id=je.id,
                                num=req.accessory_req_number,
                                req_id=req.id,
                            )
                        )
                    )

        summary_prefix = "DRY-RUN complete." if dry_run else "Backfill complete."
        self.stdout.write(
            self.style.SUCCESS(
                summary_prefix + " Created {created} accessory requisition journal "
                "entries (or would create) out of {total} delivered requisitions.".format(
                    created=created_count,
                    total=total,
                )
            )
        )
