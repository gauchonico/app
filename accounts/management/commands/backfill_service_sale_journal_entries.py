from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import SalesRevenue
from accounts.services import AccountingService
from accounts.signals import get_admin_user
from production.models import ServiceSale


class Command(BaseCommand):
    help = "Backfill missing accounting journal entries for existing ServiceSales"

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            type=str,
            default=None,
            help=(
                "Optional ISO date (YYYY-MM-DD). Only backfill service sales "
                "on or after this date."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Do not create any journal entries; just list which ServiceSales "
                "would get JEs."
            ),
        )

    def handle(self, *args, **options):
        from datetime import datetime

        since = options.get("since")
        dry_run = options.get("dry_run", False)

        qs = ServiceSale.objects.filter(invoice_status="invoiced", total_amount__gt=0)

        if since:
            try:
                since_date = datetime.strptime(since, "%Y-%m-%d").date()
                qs = qs.filter(sale_date__date__gte=since_date)
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
                f"Found {total} invoiced ServiceSales to inspect."
            )
        )

        with transaction.atomic():
            for sale in qs.select_related("customer"):
                # Skip if a SalesRevenue record already exists (journal already created)
                if SalesRevenue.objects.filter(service_sale=sale).exists():
                    continue

                if dry_run:
                    created_count += 1
                    self.stdout.write(
                        self.style.NOTICE(
                            "[DRY-RUN] Would create service sale JE for ServiceSale {num} (ID: {sale_id})".format(
                                num=sale.service_sale_number,
                                sale_id=sale.id,
                            )
                        )
                    )
                    continue

                je = AccountingService.create_service_sale_journal_entry(sale, admin_user)
                if je is not None:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            "Created service sale JE {je_id} for ServiceSale {num} (ID: {sale_id})".format(
                                je_id=je.id,
                                num=sale.service_sale_number,
                                sale_id=sale.id,
                            )
                        )
                    )

        summary_prefix = "DRY-RUN complete." if dry_run else "Backfill complete."
        self.stdout.write(
            self.style.SUCCESS(
                summary_prefix + " Created {created} service sale journal entries "
                "(or would create) out of {total} invoiced ServiceSales.".format(
                    created=created_count,
                    total=total,
                )
            )
        )
